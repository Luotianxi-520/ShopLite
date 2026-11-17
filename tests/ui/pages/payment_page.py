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

        self.wait_for('[data-testid="pay-form"]')
        previous_url = self.driver.current_url
        self.click('[data-testid="pay-submit"]')
        # 支付成功会跳转到订单页，卡被拒绝则留在支付页并显示 flash
        self.wait_for_reload(previous_url)
        return self
