from .base_page import BasePage


class ProductPage(BasePage):
    def add_to_cart(self):
        self.click('[data-testid="add-to-cart"]')
        self.wait_for('[data-testid="flash"]')
        return self

    def add_button_disabled(self):
        button = self.wait_for('[data-testid="add-to-cart"]')
        return button.get_attribute("disabled") is not None

    def stock_text(self):
        return self.text_of('[data-testid="stock-status"]')
