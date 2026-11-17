"""页面与表单路由."""
import re
from math import ceil

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from . import get_db

bp = Blueprint("main", __name__)

PAGE_SIZE = 8
STATUS_LABELS = {"pending": "待支付", "paid": "已支付", "cancelled": "已取消"}


# ---------- 会话与购物车辅助 ----------

def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def logged_in_username():
    return session.get("username")


def _pairs_for_user(user_id):
    rows = get_db().execute(
        "SELECT product_id, quantity FROM cart_items WHERE user_id = ? ORDER BY id", (user_id,)
    ).fetchall()
    return [(row["product_id"], row["quantity"]) for row in rows]


def _pairs_for_guest():
    return [(int(pid), qty) for pid, qty in (session.get("cart") or {}).items()]


def get_cart_items():
    """购物车明细:登录用户读数据库,游客读 session."""
    db = get_db()
    user_id = session.get("user_id")
    pairs = _pairs_for_user(user_id) if user_id else _pairs_for_guest()
    items = []
    for product_id, quantity in pairs:
        product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if product is None:
            continue
        items.append(
            {
                "product_id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "stock": product["stock"],
                "emoji": product["emoji"],
                "qty": quantity,
                "subtotal": round(product["price"] * quantity, 2),
            }
        )
    return items


def get_cart_total():
    return round(sum(item["subtotal"] for item in get_cart_items()), 2)


def cart_count():
    user_id = session.get("user_id")
    if user_id:
        row = get_db().execute(
            "SELECT COALESCE(SUM(quantity), 0) AS n FROM cart_items WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["n"]
    return sum((session.get("cart") or {}).values())


def _set_cart_quantity(product_id, quantity):
    user_id = session.get("user_id")
    if user_id:
        db = get_db()
        if quantity <= 0:
            db.execute(
                "DELETE FROM cart_items WHERE user_id = ? AND product_id = ?", (user_id, product_id)
            )
        else:
            db.execute(
                "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = excluded.quantity",
                (user_id, product_id, quantity),
            )
        db.commit()
    else:
        cart = session.get("cart") or {}
        if quantity <= 0:
            cart.pop(str(product_id), None)
        else:
            cart[str(product_id)] = quantity
        session["cart"] = cart


def _remove_from_cart(product_id):
    _set_cart_quantity(product_id, 0)


def _clear_cart(user_id):
    db = get_db()
    db.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
    db.commit()


def _merge_guest_cart(user_id):
    """登录时把游客购物车合并进用户购物车,数量不超过库存."""
    cart = session.get("cart") or {}
    if not cart:
        return
    db = get_db()
    for pid_str, qty in cart.items():
        product = db.execute("SELECT * FROM products WHERE id = ?", (int(pid_str),)).fetchone()
        if product is None:
            continue
        row = db.execute(
            "SELECT quantity FROM cart_items WHERE user_id = ? AND product_id = ?",
            (user_id, product["id"]),
        ).fetchone()
        merged = min((row["quantity"] if row else 0) + qty, product["stock"])
        if merged <= 0:
            continue
        db.execute(
            "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = excluded.quantity",
            (user_id, product["id"], merged),
        )
    db.commit()
    session.pop("cart", None)


def _back_url():
    """返回来源页(仅允许站内地址)."""
    referrer = request.referrer
    if referrer and referrer.startswith(request.host_url):
        return referrer
    return url_for("main.index")


# ---------- 商品 ----------

@bp.route("/")
def index():
    db = get_db()
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    min_price_raw = request.args.get("min_price", "")
    max_price_raw = request.args.get("max_price", "")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    sort = request.args.get("sort", "")
    page = request.args.get("page", 1, type=int) or 1

    where, params = [], []
    if q:
        where.append("name LIKE ?")
        params.append(f"%{q}%")
    if category:
        where.append("category = ?")
        params.append(category)
    if min_price is not None:
        where.append("price >= ?")
        params.append(min_price)
    if max_price is not None:
        where.append("price <= ?")
        params.append(max_price)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    total_count = db.execute(
        f"SELECT COUNT(*) AS n FROM products{where_sql}", params
    ).fetchone()["n"]
    total_pages = max(1, ceil(total_count / PAGE_SIZE))
    page = min(max(page, 1), total_pages)
    order_sql = {
        "price_asc": "price ASC, id ASC",
        "price_desc": "price DESC, id ASC",
        "name": "name ASC",
    }.get(sort, "id ASC")
    products = db.execute(
        f"SELECT * FROM products{where_sql} ORDER BY {order_sql} LIMIT ? OFFSET ?",
        params + [PAGE_SIZE, (page - 1) * PAGE_SIZE],
    ).fetchall()
    categories = [
        row["category"]
        for row in db.execute("SELECT DISTINCT category FROM products ORDER BY category")
    ]
    filters = {
        "q": q,
        "category": category,
        "min_price": min_price_raw,
        "max_price": max_price_raw,
        "sort": sort,
    }
    return render_template(
        "index.html",
        products=products,
        categories=categories,
        q=q,
        category=category,
        min_price=min_price_raw,
        max_price=max_price_raw,
        sort=sort,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        filters=filters,
    )


@bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = get_db().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        abort(404)
    return render_template("product.html", product=product)


# ---------- 购物车 ----------

@bp.route("/cart")
def cart_view():
    return render_template("cart.html", items=get_cart_items(), total=get_cart_total())


@bp.route("/cart/add/<int:product_id>", methods=["POST"])
def cart_add(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        abort(404)
    if product["stock"] <= 0:
        flash(f"「{product['name']}」暂时缺货", "error")
        return redirect(_back_url())

    qty = request.form.get("qty", 1, type=int) or 1
    if qty < 1:
        qty = 1
    user_id = session.get("user_id")
    if user_id:
        row = db.execute(
            "SELECT quantity FROM cart_items WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        ).fetchone()
        current = row["quantity"] if row else 0
    else:
        current = (session.get("cart") or {}).get(str(product_id), 0)

    new_qty = min(current + qty, product["stock"])
    _set_cart_quantity(product_id, new_qty)
    if new_qty < current + qty:
        flash(f"库存不足,「{product['name']}」最多可购买 {product['stock']} 件", "error")
    else:
        flash(f"已将「{product['name']}」加入购物车", "success")
    return redirect(_back_url())


@bp.route("/cart/update/<int:product_id>", methods=["POST"])
def cart_update(product_id):
    product = get_db().execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        abort(404)
    qty = request.form.get("qty", type=int)
    if qty is None:
        flash("请输入有效数量", "error")
    elif qty <= 0:
        _remove_from_cart(product_id)
        flash("已移出购物车", "info")
    elif qty > product["stock"]:
        _set_cart_quantity(product_id, product["stock"])
        flash(f"库存不足,「{product['name']}」最多可购买 {product['stock']} 件", "error")
    else:
        _set_cart_quantity(product_id, qty)
        flash("数量已更新", "success")
    return redirect(url_for("main.cart_view"))


@bp.route("/cart/remove/<int:product_id>", methods=["POST"])
def cart_remove(product_id):
    _remove_from_cart(product_id)
    flash("已移出购物车", "info")
    return redirect(url_for("main.cart_view"))


@bp.route("/cart/clear", methods=["POST"])
def cart_clear():
    if session.get("user_id"):
        _clear_cart(session["user_id"])
    else:
        session.pop("cart", None)
    flash("购物车已清空", "info")
    return redirect(url_for("main.cart_view"))


# ---------- 结算与支付 ----------

@bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    user = current_user()
    if user is None:
        return redirect(url_for("main.login", next=request.path))
    items = get_cart_items()
    if not items:
        flash("购物车是空的,先去挑选商品吧", "error")
        return redirect(url_for("main.cart_view"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        client_total = request.form.get("total", type=float)

        errors = []
        if not name:
            errors.append("请填写收货人姓名")
        if not address:
            errors.append("请填写收货地址")
        if not re.fullmatch(r"\d{6,15}", phone):
            errors.append("请填写正确的手机号")
        if client_total is None or client_total < 0:
            errors.append("订单金额无效")
        if errors:
            for message in errors:
                flash(message, "error")
            return render_template("checkout.html", items=items, total=get_cart_total(), user=user)

        db = get_db()
        cursor = db.execute(
            "INSERT INTO orders (user_id, total, name, address, phone, status) "
            "VALUES (?, ?, ?, ?, ?, 'pending')",
            (user["id"], client_total, name, address, phone),
        )
        order_id = cursor.lastrowid
        for item in items:
            db.execute(
                "INSERT INTO order_items (order_id, product_id, name, price, quantity) "
                "VALUES (?, ?, ?, ?, ?)",
                (order_id, item["product_id"], item["name"], item["price"], item["qty"]),
            )
        db.commit()
        return redirect(url_for("main.pay", order_id=order_id))

    return render_template("checkout.html", items=items, total=get_cart_total(), user=user)


@bp.route("/pay/<int:order_id>", methods=["GET", "POST"])
def pay(order_id):
    user = current_user()
    if user is None:
        return redirect(url_for("main.login", next=request.path))
    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user["id"])
    ).fetchone()
    if order is None:
        abort(404)
    if order["status"] != "pending":
        flash("该订单当前状态不可支付", "info")
        return redirect(url_for("main.order_detail", order_id=order_id))

    items = db.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()

    if request.method == "POST":
        card = request.form.get("card_number", "").replace(" ", "")
        expiry = request.form.get("expiry", "").strip()
        cvv = request.form.get("cvv", "").strip()
        if (
            not re.fullmatch(r"\d{16}", card)
            or not re.fullmatch(r"\d{2}/\d{2}", expiry)
            or not re.fullmatch(r"\d{3}", cvv)
        ):
            flash("支付信息格式不正确,请检查卡号、有效期和 CVV", "error")
            return render_template("pay.html", order=order, items=items)
        if card.endswith("0002"):
            flash("支付失败:该银行卡被拒绝,请更换支付方式", "error")
            return render_template("pay.html", order=order, items=items)

        db.execute(
            "UPDATE orders SET status = 'paid', card_number = ? WHERE id = ?", (card, order_id)
        )
        db.commit()
        _clear_cart(user["id"])
        print(f"[mock-gateway] 支付成功 order={order_id} card={card}")
        flash("支付成功,感谢您的购买!", "success")
        return redirect(url_for("main.order_detail", order_id=order_id))

    return render_template("pay.html", order=order, items=items)


@bp.route("/pay/<int:order_id>/cancel", methods=["POST"])
def pay_cancel(order_id):
    user = current_user()
    if user is None:
        return redirect(url_for("main.login", next=request.path))
    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user["id"])
    ).fetchone()
    if order is None:
        abort(404)
    if order["status"] == "pending":
        db.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
        db.commit()
        flash("订单已取消", "info")
    return redirect(url_for("main.orders_list"))


# ---------- 订单 ----------

def _mask_card(card_number):
    if not card_number:
        return ""
    return "**** **** **** " + card_number[-4:]


@bp.route("/order/<int:order_id>")
def order_detail(order_id):
    user = current_user()
    if user is None:
        return redirect(url_for("main.login", next=request.path))
    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user["id"])
    ).fetchone()
    if order is None:
        abort(404)
    items = db.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    return render_template(
        "order.html",
        order=order,
        items=items,
        status_label=STATUS_LABELS.get(order["status"], order["status"]),
        masked_card=_mask_card(order["card_number"]),
    )


@bp.route("/orders")
def orders_list():
    user = current_user()
    if user is None:
        return redirect(url_for("main.login", next=request.path))
    orders = get_db().execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user["id"],)
    ).fetchall()
    return render_template("orders.html", orders=orders, status_labels=STATUS_LABELS)


# ---------- 用户 ----------

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        # 登录查询使用字符串拼接(课程安全测试的已知注入点)
        sql = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        row = get_db().execute(sql).fetchone()
        if row is None:
            exists = get_db().execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            flash("密码错误,请重试" if exists else "用户名不存在", "error")
            return render_template(
                "login.html", username=username, next_url=request.form.get("next", "")
            )

        _merge_guest_cart(row["id"])
        session["user_id"] = row["id"]
        session["username"] = row["username"]
        flash(f"欢迎回来,{row['username']}!", "success")
        next_url = request.form.get("next", "")
        if next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(url_for("main.index"))

    return render_template("login.html", username="", next_url=request.args.get("next", ""))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        db = get_db()
        if not username or not password:
            flash("用户名和密码不能为空", "error")
        elif db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            flash("用户名已存在,请更换", "error")
        else:
            # 未校验密码复杂度(课程安全测试的已知弱点)
            db.execute(
                "INSERT INTO users (username, password, email, address) VALUES (?, ?, ?, ?)",
                (username, password, email, address),
            )
            db.commit()
            flash("注册成功,请登录", "success")
            return redirect(url_for("main.login"))
        return render_template(
            "register.html", username=username, email=email, address=address
        )
    return render_template("register.html", username="", email="", address="")


@bp.route("/profile", methods=["GET", "POST"])
def profile():
    user = current_user()
    if user is None:
        return redirect(url_for("main.login", next=request.path))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        bio = request.form.get("bio", "")
        db = get_db()
        db.execute(
            "UPDATE users SET email = ?, address = ?, bio = ? WHERE id = ?",
            (email, address, bio, user["id"]),
        )
        db.commit()
        flash("个人资料已更新", "success")
        return redirect(url_for("main.profile"))
    return render_template("profile.html", user=user)


@bp.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    flash("已退出登录", "info")
    return redirect(url_for("main.index"))
