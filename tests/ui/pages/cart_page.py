from selenium.webdriver.common.by import By

from .base_page import BasePage
from .checkout_page import CheckoutPage


class CartPage(BasePage):
    def open(self):
        self.visit("/cart")
        self.wait_until(
            lambda d: d.find_elements(By.CSS_SELECTOR, '[data-testid="cart-total"]')
            or d.find_elements(By.CSS_SELECTOR, '[data-testid="empty-cart"]')
        )
        return self

    def set_quantity(self, product_id, quantity):
        field = self.wait_for(f'[data-product-id="{product_id}"] [data-testid="qty-input"]')
        field.clear()
        field.send_keys(str(quantity))
        self.click(f'[data-product-id="{product_id}"] [data-testid="qty-update"]')
        # 提交后重定向回购物车，等新页面上的 flash 出现（不要用 staleness_of 判断旧元素）
        self.wait_for('[data-testid="flash"]')
        return self

    def total_text(self):
        return self.text_of('[data-testid="cart-total"]')

    def subtotal_text(self, product_id):
        return self.text_of(f'[data-product-id="{product_id}"] [data-testid="subtotal"]')

    def has_item(self, name):
        return name in self.body_text()

    def go_checkout(self):
        self.click('[data-testid="checkout-btn"]')
        self.wait_for('[data-testid="checkout-form"]')
        return CheckoutPage(self.driver, self.base_url)
