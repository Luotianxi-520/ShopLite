import re


def login(client, username="alice", password="alice123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def add_to_cart(client, product_id, qty=1):
    return client.post(
        f"/cart/add/{product_id}",
        data={"qty": str(qty)},
        follow_redirects=True,
    )


def order_id_from(response):
    location = response.headers.get("Location", "")
    match = re.search(r"/pay/(\d+)", location)
    assert match, f"未从响应中解析到订单号：{location}"
    return int(match.group(1))


def product_cards(html):
    """解析商品卡片的 (id, 分类, 价格)。"""
    return re.findall(
        r'data-product-id="(\d+)" data-category="([^"]+)" data-price="([\d.]+)"',
        html,
    )
