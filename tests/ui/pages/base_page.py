from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class BasePage:
    """Page Object 基类：统一封装显式等待与常用查询。"""

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url

    def visit(self, path=""):
        self.driver.get(self.base_url + path)
        return self

    def wait_for(self, css, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, css))
        )

    def wait_for_present(self, css, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css))
        )

    def wait_until(self, condition, timeout=10):
        return WebDriverWait(self.driver, timeout).until(condition)

    def wait_for_url_change(self, previous_url, timeout=10):
        self.wait_until(EC.url_changes(previous_url), timeout=timeout)
        return self

    def wait_for_reload(self, previous_url, timeout=10):
        """等待表单提交触发的整页刷新完成。

        不要用 EC.staleness_of：文档切换的瞬间，EdgeDriver 的 is_enabled()
        会返回 DevTools 错误 -32000 "Node with given id does not belong to
        the document"，而不是 StaleElementReferenceException，导致用例偶发失败。
        这里改为等待新页面自身可观察的结果：URL 已变化，或页面渲染出 flash。
        """
        self.wait_until(
            lambda d: d.current_url != previous_url
            or d.find_elements(By.CSS_SELECTOR, '[data-testid="flash"]'),
            timeout=timeout,
        )
        return self

    def click(self, css):
        self.wait_for(css).click()

    def text_of(self, css):
        return self.wait_for(css).text

    def flash_messages(self):
        return [
            element.text
            for element in self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="flash"]')
        ]

    def has_flash(self, fragment, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: any(
                    fragment in element.text
                    for element in d.find_elements(By.CSS_SELECTOR, '[data-testid="flash"]')
                )
            )
            return True
        except Exception:
            return False

    def body_text(self):
        return self.driver.find_element(By.TAG_NAME, "body").text

    def cart_count(self):
        return self.driver.find_element(By.CSS_SELECTOR, '[data-testid="cart-count"]').text
