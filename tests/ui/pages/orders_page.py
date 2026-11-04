from selenium.webdriver.common.by import By

from .base_page import BasePage


class OrdersPage(BasePage):
    def open(self):
        self.visit("/orders")
        self.wait_until(
            lambda d: d.find_elements(By.CSS_SELECTOR, '[data-testid="order-row"]')
            or d.find_elements(By.CSS_SELECTOR, '[data-testid="empty-orders"]')
        )
        return self

    def rows(self):
        return self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="order-row"]')

    def statuses(self):
        return [
            element.text
            for element in self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="order-status"]')
        ]
