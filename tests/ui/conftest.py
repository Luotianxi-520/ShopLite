import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from shop import create_app
from shop.db import init_db

ROOT = Path(__file__).resolve().parents[2]
LOCAL_EDGEDRIVER = ROOT / "drivers" / "msedgedriver.exe"


class ServerInfo:
    def __init__(self, url, db_path):
        self.url = url
        self.db_path = db_path


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    db_path = str(tmp_path_factory.mktemp("ui_db") / "ui.db")
    init_db(db_path)
    app = create_app(db_path)
    httpd = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield ServerInfo(f"http://127.0.0.1:{httpd.server_port}", db_path)
    httpd.shutdown()
    thread.join(timeout=5)


@pytest.fixture(autouse=True)
def reset_database(server):
    """每个用例前重建数据库，保证用例互不依赖。"""
    init_db(server.db_path, reset=True)
    yield


@pytest.fixture()
def base_url(server):
    return server.url


@pytest.fixture()
def driver():
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.edge.service import Service

    options = webdriver.EdgeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=zh-CN")

    browser = None
    if LOCAL_EDGEDRIVER.exists():
        try:
            browser = webdriver.Edge(
                options=options, service=Service(str(LOCAL_EDGEDRIVER))
            )
        except WebDriverException:
            # 本地驱动与浏览器版本不匹配时，回退到 Selenium Manager 自动下载
            browser = None

    if browser is None:
        browser = webdriver.Edge(options=options)
    browser.set_page_load_timeout(20)
    yield browser
    browser.quit()
