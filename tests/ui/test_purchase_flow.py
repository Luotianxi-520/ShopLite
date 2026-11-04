from tests.ui.pages.cart_page import CartPage
from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.orders_page import OrdersPage
from tests.ui.pages.products_page import ProductsPage


def login(driver, base_url, username="alice", password="alice123"):
    return LoginPage(driver, base_url).open().login(username, password)


def test_end_to_end_purchase(driver, base_url):
    login(driver, base_url)

    products = ProductsPage(driver, base_url).open()
    products.filter_category("电子产品")
    assert products.card_categories()
    assert set(products.card_categories()) == {"电子产品"}

    product = products.open_product(1)  # 无线蓝牙耳机
    product.add_to_cart()
    assert any("无线蓝牙耳机" in message for message in product.flash_messages())

    cart = CartPage(driver, base_url).open()
    assert cart.has_item("无线蓝牙耳机")
    cart.set_quantity(1, 2)
    assert cart.total_text() == "¥398.00"

    checkout = cart.go_checkout()
    checkout.fill_form(name="张三", address="北京市海淀区测试路 8 号", phone="13800138000")
    payment = checkout.submit_and_pay()
    payment.fill_and_pay("4242 4242 4242 4242", "12/30", "123")

    payment.wait_for('[data-testid="order-status"]')
    assert payment.text_of('[data-testid="order-status"]') == "已支付"
    assert "支付成功" in payment.body_text()

    orders = OrdersPage(driver, base_url).open()
    assert "已支付" in orders.body_text()

    cart = CartPage(driver, base_url).open()
    assert "购物车还是空的" in cart.body_text()


def test_guest_cart_is_merged_after_login(driver, base_url):
    ProductsPage(driver, base_url).open().open_product(2).add_to_cart()  # 机械键盘

    cart = CartPage(driver, base_url).open()
    assert cart.has_item("机械键盘")

    login(driver, base_url)
    cart = CartPage(driver, base_url).open()
    assert cart.has_item("机械键盘")
    assert cart.cart_count() == "1"


def test_filter_and_search(driver, base_url):
    products = ProductsPage(driver, base_url).open()
    products.filter_category("图书")
    assert len(products.product_cards()) == 5
    assert set(products.card_categories()) == {"图书"}

    products = ProductsPage(driver, base_url).open()
    products.search("算法")
    names = products.product_names()
    assert len(names) == 1
    assert "算法导论" in names[0]


def test_checkout_form_validation(driver, base_url):
    login(driver, base_url)
    ProductsPage(driver, base_url).open().open_product(6).add_to_cart()

    cart = CartPage(driver, base_url).open()
    checkout = cart.go_checkout()
    checkout.fill_form(name="", address="", phone="")
    checkout.submit()

    assert checkout.has_flash("请填写收货人姓名")
    assert "/checkout" in driver.current_url


def test_payment_declined_keeps_order_pending(driver, base_url):
    login(driver, base_url)
    ProductsPage(driver, base_url).open().open_product(6).add_to_cart()

    cart = CartPage(driver, base_url).open()
    checkout = cart.go_checkout()
    checkout.fill_form(name="李四", address="上海市浦东新区测试路 2 号", phone="13900139000")
    payment = checkout.submit_and_pay()

    payment.fill_and_pay("4000 0000 0000 0002")
    assert payment.has_flash("支付失败")
    assert "/pay/" in driver.current_url

    orders = OrdersPage(driver, base_url).open()
    assert "待支付" in orders.body_text()

    cart = CartPage(driver, base_url).open()
    assert cart.has_item("USB-C 充电器")


def test_out_of_stock_add_button_disabled(driver, base_url):
    product = ProductsPage(driver, base_url).open().open_product(5)  # 智能手表库存 0
    assert product.add_button_disabled()
