from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .base_page import BasePage
from .product_page import ProductPage


class ProductsPage(BasePage):
    def open(self):
        self.visit("/")
        self.wait_for('[data-testid="filter-panel"]')
        return self

    def _submit_filters(self):
        form = self.wait_for('[data-testid="filter-panel"]')
        self.click('[data-testid="filter-submit"]')
        WebDriverWait(self.driver, 10).until(EC.staleness_of(form))
        self.wait_for('[data-testid="filter-panel"]')

    def filter_category(self, label):
        Select(self.wait_for('[data-testid="category-select"]')).select_by_visible_text(label)
        self._submit_filters()
        return self

    def search(self, term):
        field = self.wait_for('[data-testid="search-input"]')
        field.clear()
        field.send_keys(term)
        self._submit_filters()
        return self

    def product_cards(self):
        return self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="product-card"]')

    def card_categories(self):
        return [card.get_attribute("data-category") for card in self.product_cards()]

    def product_names(self):
        return [
            element.text
            for element in self.driver.find_elements(By.CSS_SELECTOR, ".product-name")
        ]

    def open_product(self, product_id):
        self.click(f'[data-product-id="{product_id}"] [data-testid="product-link"]')
        self.wait_for('[data-testid="product-name"]')
        return ProductPage(self.driver, self.base_url)
