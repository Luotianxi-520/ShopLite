import pytest

from tests.functional.helpers import add_to_cart, login


def test_register_then_login(client):
    resp = client.post(
        "/register",
        data={"username": "carol", "password": "Carol123!", "email": "carol@example.com", "address": ""},
        follow_redirects=True,
    )
    assert "注册成功,请登录" in resp.text

    resp = login(client, "carol", "Carol123!")
    assert "欢迎回来,carol!" in resp.text


def test_register_duplicate_username(client):
    resp = client.post(
        "/register",
        data={"username": "alice", "password": "whatever", "email": "", "address": ""},
        follow_redirects=True,
    )
    assert "用户名已存在" in resp.text


def test_register_requires_username_and_password(client):
    resp = client.post(
        "/register",
        data={"username": "", "password": "", "email": "", "address": ""},
        follow_redirects=True,
    )
    assert "用户名和密码不能为空" in resp.text


@pytest.mark.parametrize(
    "password",
    [
        "Sh0rt!",    # 不足 8 位
        "sh0rty!#",  # 缺大写字母
        "SH0RTY!#",  # 缺小写字母
        "Shorty!!",  # 缺数字
        "Shorty12",  # 缺符号
    ],
)
def test_register_rejects_weak_password(client, query, password):
    resp = client.post(
        "/register",
        data={"username": "weak", "password": password, "email": "", "address": ""},
        follow_redirects=True,
    )
    assert "密码需至少 8 位" in resp.text
    assert query("SELECT COUNT(*) AS n FROM users WHERE username = 'weak'")[0]["n"] == 0


def test_login_with_wrong_password(client):
    resp = login(client, "alice", "wrong-password")
    assert "密码错误,请重试" in resp.text


def test_login_with_unknown_user(client):
    resp = login(client, "nobody", "whatever")
    assert "用户名不存在" in resp.text


def test_logout_clears_session(client):
    login(client)
    assert 'data-testid="nav-logout"' in client.get("/").text

    resp = client.get("/logout", follow_redirects=True)
    assert "已退出登录" in resp.text
    assert 'data-testid="nav-login"' in resp.text


def test_login_redirects_back_to_checkout(client):
    add_to_cart(client, 1)

    resp = client.post(
        "/login",
        data={"username": "alice", "password": "alice123", "next": "/checkout"},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/checkout")

    page = client.get("/checkout")
    assert page.status_code == 200
    assert "确认订单" in page.text


def test_login_rejects_external_next_url(client):
    resp = client.post(
        "/login",
        data={"username": "alice", "password": "alice123", "next": "//evil.example"},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"


def test_profile_requires_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_update_profile(client):
    login(client)

    resp = client.post(
        "/profile",
        data={"email": "new@example.com", "address": "新地址 1 号", "bio": "这是一段个人简介"},
        follow_redirects=True,
    )
    assert "个人资料已更新" in resp.text
    assert "new@example.com" in resp.text
    assert "新地址 1 号" in resp.text
    assert "这是一段个人简介" in resp.text
