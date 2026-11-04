import pytest

from shop import create_app
from shop.db import connect, init_db


@pytest.fixture()
def app(tmp_path):
    db_path = str(tmp_path / "functional.db")
    init_db(db_path)
    application = create_app(db_path)
    application.config.update(TESTING=True)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def bob_client(app):
    test_client = app.test_client()
    test_client.post("/login", data={"username": "bob", "password": "bob123"})
    return test_client


@pytest.fixture()
def query(app):
    """直接查询测试数据库，用于断言订单等持久化结果。"""

    def run(sql, params=()):
        conn = connect(app.config["DATABASE"])
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    return run
