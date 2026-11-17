from tests.functional.helpers import add_to_cart, login, order_id_from

CHECKOUT_DATA = {
    "name": "张三",
    "address": "北京市海淀区测试路 8 号",
    "phone": "13800138000",
    "total": "78.00",
}

PAY_SUCCESS = {"card_number": "4242 4242 4242 4242", "expiry": "12/30", "cvv": "123"}
PAY_DECLINED = {"card_number": "4000 0000 0000 0002", "expiry": "12/30", "cvv": "123"}


def prepare_order(client):
    """登录 alice，加入 2 个马克杯（78 元），提交订单并返回订单号。"""
    login(client)
    add_to_cart(client, 12, qty=2)
    resp = client.post("/checkout", data=CHECKOUT_DATA)
    return order_id_from(resp)


def test_checkout_requires_login(client):
    add_to_cart(client, 12)
    resp = client.get("/checkout")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_checkout_page_shows_cart_summary(client):
    login(client)
    add_to_cart(client, 12, qty=2)

    resp = client.get("/checkout")
    assert resp.status_code == 200
    assert "陶瓷马克杯" in resp.text
    assert "¥78.00" in resp.text
    assert 'value="78.00"' in resp.text


def test_checkout_prefills_profile(client):
    login(client)
    add_to_cart(client, 12)

    resp = client.get("/checkout")
    assert 'value="alice"' in resp.text
    assert 'value="北京市朝阳区测试路 1 号"' in resp.text


def test_checkout_validation_errors(client, query):
    login(client)
    add_to_cart(client, 12)

    resp = client.post(
        "/checkout",
        data={"name": "", "address": "", "phone": "abc", "total": "39.00"},
    )
    assert resp.status_code == 200
    assert "请填写收货人姓名" in resp.text
    assert "请填写收货地址" in resp.text
    assert "请填写正确的手机号" in resp.text
    assert query("SELECT COUNT(*) AS n FROM orders")[0]["n"] == 0


def test_checkout_creates_pending_order(client, query):
    order_id = prepare_order(client)

    order = query("SELECT * FROM orders WHERE id = ?", (order_id,))[0]
    assert order["status"] == "pending"
    assert order["total"] == 78.0
    assert order["name"] == "张三"
    assert order["phone"] == "13800138000"

    items = query("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    assert len(items) == 1
    assert items[0]["name"] == "陶瓷马克杯"
    assert items[0]["quantity"] == 2

    pay_page = client.get(f"/pay/{order_id}")
    assert "¥78.00" in pay_page.text


def test_checkout_with_empty_cart_redirects(client):
    login(client)
    resp = client.get("/checkout", follow_redirects=True)
    assert "购物车是空的" in resp.text
    assert "购物车还是空的" in resp.text


def test_payment_success_flow(client, query):
    order_id = prepare_order(client)

    resp = client.post(f"/pay/{order_id}", data=PAY_SUCCESS, follow_redirects=True)
    assert "支付成功" in resp.text
    assert "已支付" in resp.text

    status = query("SELECT status FROM orders WHERE id = ?", (order_id,))[0]["status"]
    assert status == "paid"

    assert "购物车还是空的" in client.get("/cart").text
    assert f"订单 #{order_id}" in client.get("/orders").text
    assert "已支付" in client.get("/orders").text


def test_payment_declined_keeps_order_pending(client, query):
    order_id = prepare_order(client)

    resp = client.post(f"/pay/{order_id}", data=PAY_DECLINED, follow_redirects=True)
    assert "支付失败" in resp.text

    status = query("SELECT status FROM orders WHERE id = ?", (order_id,))[0]["status"]
    assert status == "pending"
    assert "陶瓷马克杯" in client.get("/cart").text


def test_payment_invalid_card_format(client, query):
    order_id = prepare_order(client)

    resp = client.post(
        f"/pay/{order_id}",
        data={"card_number": "1234", "expiry": "12/30", "cvv": "123"},
        follow_redirects=True,
    )
    assert "支付信息格式不正确" in resp.text
    status = query("SELECT status FROM orders WHERE id = ?", (order_id,))[0]["status"]
    assert status == "pending"


def test_payment_rejects_expired_card(client, query):
    order_id = prepare_order(client)

    resp = client.post(
        f"/pay/{order_id}",
        data={"card_number": "4242 4242 4242 4242", "expiry": "01/20", "cvv": "123"},
        follow_redirects=True,
    )
    assert "银行卡已过期" in resp.text

    status = query("SELECT status FROM orders WHERE id = ?", (order_id,))[0]["status"]
    assert status == "pending"


def test_cancel_payment(client, query):
    order_id = prepare_order(client)

    resp = client.post(f"/pay/{order_id}/cancel", follow_redirects=True)
    assert "订单已取消" in resp.text

    status = query("SELECT status FROM orders WHERE id = ?", (order_id,))[0]["status"]
    assert status == "cancelled"


def test_order_detail_only_visible_to_owner(client, bob_client):
    order_id = prepare_order(client)

    resp = bob_client.get(f"/order/{order_id}")
    assert resp.status_code == 404
    assert "你访问的页面不存在" in resp.text

    resp = bob_client.post(f"/pay/{order_id}", data=PAY_SUCCESS)
    assert resp.status_code == 404
