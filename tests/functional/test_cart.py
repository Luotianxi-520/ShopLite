import re

from tests.functional.helpers import add_to_cart, login


def cart_product_ids(html):
    return [int(pid) for pid in re.findall(r'data-testid="cart-row" data-product-id="(\d+)"', html)]


def test_add_to_cart_as_guest(client):
    resp = add_to_cart(client, 1)
    assert "已将「无线蓝牙耳机」加入购物车" in resp.text

    page = client.get("/cart")
    assert cart_product_ids(page.text) == [1]
    assert "¥199.00" in page.text


def test_add_same_product_twice_increments_quantity(client):
    add_to_cart(client, 12)
    add_to_cart(client, 12)

    page = client.get("/cart")
    assert cart_product_ids(page.text) == [12]
    assert 'value="2"' in page.text
    assert "¥78.00" in page.text


def test_update_quantity_recalculates_subtotal(client):
    add_to_cart(client, 1)

    resp = client.post("/cart/update/1", data={"qty": "3"}, follow_redirects=True)
    assert "数量已更新" in resp.text
    assert 'value="3"' in resp.text
    assert "¥597.00" in resp.text


def test_quantity_over_stock_is_capped(client):
    add_to_cart(client, 20)  # 跳绳库存只有 2 件

    resp = client.post("/cart/update/20", data={"qty": "9"}, follow_redirects=True)
    assert "库存不足" in resp.text
    assert "最多可购买 2 件" in resp.text
    assert 'value="2"' in resp.text
    assert "¥50.00" in resp.text


def test_update_quantity_to_zero_removes_item(client):
    add_to_cart(client, 1)

    resp = client.post("/cart/update/1", data={"qty": "0"}, follow_redirects=True)
    assert "已移出购物车" in resp.text
    assert "购物车还是空的" in resp.text


def test_remove_item(client):
    add_to_cart(client, 1)
    add_to_cart(client, 12)

    resp = client.post("/cart/remove/1", follow_redirects=True)
    assert "无线蓝牙耳机" not in resp.text
    assert "陶瓷马克杯" in resp.text


def test_clear_cart(client):
    add_to_cart(client, 1)
    add_to_cart(client, 12)

    resp = client.post("/cart/clear", follow_redirects=True)
    assert "购物车已清空" in resp.text
    assert "购物车还是空的" in resp.text


def test_out_of_stock_product_cannot_be_added(client):
    resp = add_to_cart(client, 5)  # 智能手表库存为 0
    assert "暂时缺货" in resp.text
    assert "购物车还是空的" in client.get("/cart").text


def test_cart_total_sums_all_items(client):
    add_to_cart(client, 1)   # 199
    add_to_cart(client, 12)  # 39
    client.post("/cart/update/12", data={"qty": "2"})

    page = client.get("/cart")
    assert "¥277.00" in page.text


def test_guest_cart_merged_after_login(client):
    add_to_cart(client, 2)  # 游客加入机械键盘

    login(client)

    page = client.get("/cart")
    assert cart_product_ids(page.text) == [2]
    assert "机械键盘" in page.text


def test_guest_cart_quantities_merge_with_existing_cart(client):
    login(client)
    add_to_cart(client, 12)  # alice 购物车 1 件
    client.get("/logout")
    add_to_cart(client, 12)  # 游客购物车 1 件

    login(client)

    page = client.get("/cart")
    assert 'value="2"' in page.text
    assert "¥78.00" in page.text


def test_add_unknown_product_returns_404(client):
    resp = client.post("/cart/add/9999")
    assert resp.status_code == 404
