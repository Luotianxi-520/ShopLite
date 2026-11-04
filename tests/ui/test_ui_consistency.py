from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tests.ui.pages.products_page import ProductsPage

PAGES = ["/", "/login", "/register", "/cart", "/product/1"]


def test_header_footer_and_title_consistency(driver, base_url):
    for path in PAGES:
        driver.get(base_url + path)

        header = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="site-header"]'))
        )
        footer = driver.find_element(By.CSS_SELECTOR, '[data-testid="site-footer"]')

        assert header.is_displayed()
        assert footer.is_displayed()
        assert "ShopLite" in driver.find_element(By.CSS_SELECTOR, '[data-testid="brand"]').text
        assert driver.title.endswith("· ShopLite")
        assert "© 2026 ShopLite" in footer.text

        nav_text = driver.find_element(By.CSS_SELECTOR, '[data-testid="main-nav"]').text
        assert "首页" in nav_text
        assert "购物车" in nav_text
        assert "我的订单" in nav_text


def test_primary_button_color_is_consistent(driver, base_url):
    colors = set()
    for path in ["/", "/login", "/register", "/product/1"]:
        driver.get(base_url + path)
        button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".btn-primary"))
        )
        colors.add(button.value_of_css_property("background-color"))

    # 购物车页的“去结算”按钮
    ProductsPage(driver, base_url).open().open_product(1).add_to_cart()
    driver.get(base_url + "/cart")
    checkout_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="checkout-btn"]'))
    )
    colors.add(checkout_button.value_of_css_property("background-color"))

    assert len(colors) == 1, f"主按钮颜色不一致：{colors}"
