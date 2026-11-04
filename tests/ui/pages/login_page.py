from selenium.webdriver.common.by import By

from .base_page import BasePage


class LoginPage(BasePage):
    def open(self):
        self.visit("/login")
        self.wait_for('[data-testid="login-form"]')
        return self

    def login(self, username, password):
        username_input = self.wait_for('[data-testid="login-username"]')
        username_input.clear()
        username_input.send_keys(username)

        password_input = self.wait_for('[data-testid="login-password"]')
        password_input.clear()
        password_input.send_keys(password)

        self.click('[data-testid="login-submit"]')
        self.wait_until(
            lambda d: d.find_elements(By.CSS_SELECTOR, '[data-testid="nav-logout"]')
            or d.find_elements(By.CSS_SELECTOR, '[data-testid="flash"]')
        )
        return self
