from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .base_page import BasePage


class PaymentPage(BasePage):
    def fill_and_pay(self, card_number, expiry="12/30", cvv="123"):
        for css, value in (
            ('[data-testid="card-number"]', card_number),
            ('[data-testid="expiry"]', expiry),
            ('[data-testid="cvv"]', cvv),
        ):
            field = self.wait_for(css)
            field.clear()
            field.send_keys(value)

        form = self.wait_for('[data-testid="pay-form"]')
        self.click('[data-testid="pay-submit"]')
        WebDriverWait(self.driver, 10).until(EC.staleness_of(form))
        return self
