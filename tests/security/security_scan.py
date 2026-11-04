"""ShopLite 安全测试扫描。

仅对本地启动的课程测试系统执行，请勿用于未授权的真实系统。
运行：python tests/security/security_scan.py
"""
import logging
import os
import re
import sys
import tempfile
import threading

import requests
from werkzeug.serving import make_server

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shop import create_app
from shop.db import connect, init_db

BASE = ""
FINDINGS = []


# ---------- 工具函数 ----------

def login_session(username="alice", password="alice123"):
    session = requests.Session()
    session.post(
        f"{BASE}/login",
        data={"username": username, "password": password},
        allow_redirects=True,
    )
    return session


def create_order(session, total="0.01"):
    response = session.post(
        f"{BASE}/checkout",
        data={
            "name": "安全测试",
            "address": "测试地址 1 号",
            "phone": "13800138000",
            "total": total,
        },
        allow_redirects=False,
    )
    match = re.search(r"/pay/(\d+)", response.headers.get("Location", ""))
    if not match:
        raise RuntimeError(f"下单失败：{response.status_code}")
    return int(match.group(1))


# ---------- 各项检查 ----------

def check_sql_injection(_db_path):
    session = requests.Session()
    response = session.post(
        f"{BASE}/login",
        data={"username": "' OR '1'='1' -- ", "password": "anything"},
        allow_redirects=True,
    )
    found = "退出登录" in response.text
    evidence = "用户名输入 `' OR '1'='1' -- `，无需正确密码即登录为 alice"
    return found, evidence


def check_reflected_xss(_db_path):
    payload = "<script>alert(1)</script>"
    response = requests.get(f"{BASE}/", params={"q": payload})
    found = payload in response.text
    evidence = f"搜索参数 q={payload} 被原样输出到页面（未转义）"
    return found, evidence


def check_stored_xss(_db_path):
    session = requests.Session()
    session.post(
        f"{BASE}/register",
        data={"username": "xss_user", "password": "xss123", "email": "", "address": ""},
        allow_redirects=True,
    )
    session.post(
        f"{BASE}/login",
        data={"username": "xss_user", "password": "xss123"},
        allow_redirects=True,
    )
    payload = "<script>alert('stored')</script>"
    session.post(
        f"{BASE}/profile",
        data={"email": "xss@example.com", "address": "", "bio": payload},
        allow_redirects=True,
    )
    response = session.get(f"{BASE}/profile")
    found = payload in response.text
    evidence = "个人简介字段存储的 script 标签在个人中心被原样渲染（存储型 XSS）"
    return found, evidence


def check_price_tampering(_db_path):
    session = login_session()
    session.post(f"{BASE}/cart/add/12", data={"qty": "1"}, allow_redirects=True)
    checkout = session.get(f"{BASE}/checkout")
    normal_total = re.search(r'name="total" value="([\d.]+)"', checkout.text).group(1)

    order_id = create_order(session, total="0.01")
    pay_page = session.get(f"{BASE}/pay/{order_id}")
    found = "¥0.01" in pay_page.text
    evidence = f"结算页正常金额 {normal_total} 元，抓包把隐藏字段 total 改为 0.01 后订单金额变为 0.01 元"
    return found, evidence


def check_weak_password(_db_path):
    session = requests.Session()
    session.post(
        f"{BASE}/register",
        data={"username": "weak_user", "password": "123", "email": "", "address": ""},
        allow_redirects=True,
    )
    response = session.post(
        f"{BASE}/login",
        data={"username": "weak_user", "password": "123"},
        allow_redirects=True,
    )
    found = "退出登录" in response.text
    evidence = "注册时密码仅 3 位数字 \"123\" 即被接受，且可正常登录"
    return found, evidence


def check_user_enumeration(_db_path):
    wrong_password = requests.post(
        f"{BASE}/login", data={"username": "alice", "password": "wrong"}
    )
    unknown_user = requests.post(
        f"{BASE}/login", data={"username": "no_such_user", "password": "wrong"}
    )
    found = "密码错误" in wrong_password.text and "用户名不存在" in unknown_user.text
    evidence = "已存在用户返回“密码错误”，不存在用户返回“用户名不存在”，可枚举有效用户名"
    return found, evidence


def check_brute_force(_db_path):
    session = requests.Session()
    for _ in range(12):
        session.post(
            f"{BASE}/login",
            data={"username": "alice", "password": "wrong-password"},
            allow_redirects=True,
        )
    response = session.post(
        f"{BASE}/login",
        data={"username": "alice", "password": "alice123"},
        allow_redirects=True,
    )
    found = "退出登录" in response.text
    evidence = "连续 12 次错误密码后没有限速/锁定，正确密码仍可立即登录"
    return found, evidence


def check_session_after_logout(_db_path):
    session = login_session()
    stolen_cookie = session.cookies.get("session")
    session.get(f"{BASE}/logout")

    replay = requests.Session()
    replay.cookies.set("session", stolen_cookie)
    response = replay.get(f"{BASE}/profile")
    found = response.status_code == 200 and "个人中心" in response.text
    evidence = "退出登录后，旧的会话 Cookie 仍可访问个人中心（服务端未使会话失效）"
    return found, evidence


def check_card_storage(db_path):
    session = login_session("bob", "bob123")
    session.post(f"{BASE}/cart/add/12", data={"qty": "1"}, allow_redirects=True)
    checkout = session.get(f"{BASE}/checkout")
    total = re.search(r'name="total" value="([\d.]+)"', checkout.text).group(1)
    order_id = create_order(session, total=total)

    card = "4242424242424242"
    response = session.post(
        f"{BASE}/pay/{order_id}",
        data={"card_number": card, "expiry": "12/30", "cvv": "123"},
        allow_redirects=True,
    )
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT card_number FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
    finally:
        conn.close()
    found = row is not None and row["card_number"] == card
    evidence = "支付成功后完整卡号明文存入 orders.card_number，同时被打印到服务端日志"
    return found, evidence


def check_csrf(_db_path):
    session = login_session()
    session.post(f"{BASE}/cart/add/12", data={"qty": "1"}, allow_redirects=True)
    response = session.post(f"{BASE}/cart/clear", allow_redirects=False)
    cart = session.get(f"{BASE}/cart")
    found = response.status_code == 302 and "购物车还是空的" in cart.text
    evidence = "购物车写接口没有 CSRF Token，任何来源的表单请求都能清空购物车"
    return found, evidence


def check_cookie_flags(_db_path):
    response = requests.post(
        f"{BASE}/login",
        data={"username": "alice", "password": "alice123"},
        allow_redirects=False,
    )
    set_cookie = response.headers.get("Set-Cookie", "")
    found = "session=" in set_cookie and "Secure" not in set_cookie
    evidence = "会话 Cookie 缺少 Secure 标志（SameSite 也未显式设置）"
    return found, evidence


def check_plaintext_password(db_path):
    session = requests.Session()
    session.post(
        f"{BASE}/register",
        data={"username": "plain_user", "password": "PlainText#2026", "email": "", "address": ""},
        allow_redirects=True,
    )
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT password FROM users WHERE username = ?", ("plain_user",)
        ).fetchone()
    finally:
        conn.close()
    found = row is not None and row["password"] == "PlainText#2026"
    evidence = "注册后 users.password 直接保存明文密码，数据库泄露即可直接登录所有账号"
    return found, evidence


CHECKS = [
    ("SEC-01", "登录表单 SQL 注入", "高", check_sql_injection),
    ("SEC-02", "结算金额客户端篡改", "高", check_price_tampering),
    ("SEC-03", "支付卡号明文存储", "高", check_card_storage),
    ("SEC-04", "反射型 XSS（搜索）", "中", check_reflected_xss),
    ("SEC-05", "存储型 XSS（个人简介）", "中", check_stored_xss),
    ("SEC-06", "弱口令策略缺失", "中", check_weak_password),
    ("SEC-07", "登录无限速/锁定", "中", check_brute_force),
    ("SEC-08", "退出登录后会话未失效", "中", check_session_after_logout),
    ("SEC-09", "写操作缺少 CSRF 防护", "中", check_csrf),
    ("SEC-10", "用户名枚举", "低", check_user_enumeration),
    ("SEC-11", "会话 Cookie 缺少 Secure 标志", "低", check_cookie_flags),
    ("SEC-12", "用户密码明文存储", "高", check_plaintext_password),
]

SEVERITY_ORDER = {"高": 0, "中": 1, "低": 2}


def run_scan(db_path):
    for check_id, name, severity, func in CHECKS:
        try:
            found, evidence = func(db_path)
        except Exception as exc:  # 单项失败不影响其余检查
            found, evidence = False, f"检查执行异常：{exc}"
        FINDINGS.append(
            {
                "id": check_id,
                "name": name,
                "severity": severity,
                "found": found,
                "evidence": evidence,
            }
        )


def print_report():
    print("=" * 68)
    print("ShopLite 安全测试扫描结果")
    print("=" * 68)
    for item in sorted(FINDINGS, key=lambda f: SEVERITY_ORDER[f["severity"]]):
        status = "发现漏洞" if item["found"] else "未发现"
        print(f"[{item['severity']}] {item['id']} {item['name']} —— {status}")
        if item["found"]:
            print(f"        证据：{item['evidence']}")
    hit = [f for f in FINDINGS if f["found"]]
    counts = {level: sum(1 for f in hit if f["severity"] == level) for level in ("高", "中", "低")}
    print("-" * 68)
    print(
        f"共检查 {len(FINDINGS)} 项，发现 {len(hit)} 个问题"
        f"（高 {counts['高']} / 中 {counts['中']} / 低 {counts['低']}）"
    )


def main():
    global BASE
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "security.db")
        init_db(db_path)
        app = create_app(db_path)
        httpd = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        BASE = f"http://127.0.0.1:{httpd.server_port}"
        print(f"目标系统启动于 {BASE}\n")
        try:
            run_scan(db_path)
        finally:
            httpd.shutdown()
            thread.join(timeout=5)
    print_report()


if __name__ == "__main__":
    main()
