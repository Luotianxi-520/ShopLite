from selenium.webdriver.support import expected_conditions as EC

from .base_page import BasePage
from .payment_page import PaymentPage


class CheckoutPage(BasePage):
    def fill_form(self, name=None, address=None, phone=None):
        for css, value in (
            ('[data-testid="checkout-name"]', name),
            ('[data-testid="checkout-address"]', address),
            ('[data-testid="checkout-phone"]', phone),
        ):
            if value is None:
                continue
            field = self.wait_for(css)
            field.clear()
            field.send_keys(value)
        return self

    def submit(self):
        self.click('[data-testid="checkout-submit"]')
        return self

    def submit_and_pay(self):
        self.submit()
        self.wait_until(EC.presence_of_element_located(("css selector", '[data-testid="pay-form"]')))
        return PaymentPage(self.driver, self.base_url)
