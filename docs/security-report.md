# ShopLite 安全测试报告

| 项目 | 内容 |
|---|---|
| 被测系统 | ShopLite 简易电商平台 v1.0 |
| 测试日期 | 2026-10-29 |
| 测试环境 | Windows 11，Python 3.15，Flask 3.1，SQLite，本地 `127.0.0.1` 随机端口 |
| 测试范围 | 登录表单、支付流程、会话管理、结算业务逻辑 |
| 测试方法 | 黑盒测试：手工构造 payload + requests 自动化脚本 + 数据库核验 |
| 执行脚本 | `tests/security/security_scan.py` |
| 风险分级 | 高 / 中 / 低（综合可利用性与业务影响） |

> 说明：被测系统是课程演示系统，为安全测试任务保留了常见实现缺陷。所有测试仅针对本地启动的实例，未涉及任何真实支付网关或第三方系统。

## 1. 结果概览

共执行 12 项检查，发现 12 个安全问题：高 4 项、中 6 项、低 2 项。

| 编号 | 安全问题 | 等级 | 状态 | 修复优先级 |
|---|---|---|---|---|
| SEC-01 | 登录表单 SQL 注入，可绕过密码 | 高 | 存在 | P0 |
| SEC-02 | 结算金额由客户端提交，可篡改 | 高 | 存在 | P0 |
| SEC-03 | 支付卡号明文存储并写入日志 | 高 | 存在 | P0 |
| SEC-12 | 用户密码明文存储 | 高 | 存在 | P0 |
| SEC-04 | 搜索结果反射型 XSS | 中 | 存在 | P1 |
| SEC-05 | 个人简介存储型 XSS | 中 | 存在 | P1 |
| SEC-06 | 注册无密码强度校验 | 中 | 存在 | P1 |
| SEC-07 | 登录接口无限速、无锁定 | 中 | 存在 | P1 |
| SEC-08 | 退出登录后旧会话仍有效 | 中 | 存在 | P1 |
| SEC-09 | 写操作缺少 CSRF Token | 中 | 存在 | P1 |
| SEC-10 | 登录错误提示可枚举用户名 | 低 | 存在 | P2 |
| SEC-11 | 会话 Cookie 缺少 Secure 标志 | 低 | 存在 | P2 |

复现脚本执行结果（节选）：

```
[高] SEC-01 登录表单 SQL 注入 —— 发现漏洞
[高] SEC-02 结算金额客户端篡改 —— 发现漏洞
[高] SEC-03 支付卡号明文存储 —— 发现漏洞
[高] SEC-12 用户密码明文存储 —— 发现漏洞
[中] SEC-04 反射型 XSS（搜索） —— 发现漏洞
[中] SEC-05 存储型 XSS（个人简介） —— 发现漏洞
[中] SEC-06 弱口令策略缺失 —— 发现漏洞
[中] SEC-07 登录无限速/锁定 —— 发现漏洞
[中] SEC-08 退出登录后会话未失效 —— 发现漏洞
[中] SEC-09 写操作缺少 CSRF 防护 —— 发现漏洞
[低] SEC-10 用户名枚举 —— 发现漏洞
[低] SEC-11 会话 Cookie 缺少 Secure 标志 —— 发现漏洞
```

## 2. 详细发现

### SEC-01 登录表单 SQL 注入（高）

- 位置：`POST /login`，`shop/views.py` 的 `login()`。
- 复现步骤：
  1. 打开登录页。
  2. 用户名输入 `' OR '1'='1' -- `，密码输入任意内容。
  3. 提交后页面显示「退出登录」，并以 alice 身份登录。
- 证据：登录查询由 f-string 拼接：

  ```python
  sql = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
  ```

  payload 使 `WHERE` 条件恒为真，密码校验被注释掉。
- 影响：攻击者无需密码即可登录任意可枚举的账号，属于最严重级别的漏洞。
- 修复建议：使用参数化查询；对输入做长度与字符校验；禁止把用户输入拼进 SQL。

  ```python
  row = db.execute(
      "SELECT * FROM users WHERE username = ? AND password = ?",
      (username, hashed_password),
  ).fetchone()
  ```

- 修复验证：再次执行 SEC-01，应无法登录，返回统一的「用户名或密码错误」。

### SEC-02 结算金额客户端篡改（高）

- 位置：`POST /checkout`，隐藏字段 `total`。
- 复现步骤：
  1. 登录后将 1 件陶瓷马克杯（¥39.00）加入购物车。
  2. 进入结算页，抓包把表单隐藏字段 `total` 从 `39.00` 改为 `0.01`。
  3. 提交后支付页显示应付 ¥0.01，订单以 0.01 元创建。
- 证据：`client_total = request.form.get("total", type=float)` 直接写入订单总额。
- 影响：可任意压低订单金额，造成直接资金损失。
- 修复建议：服务端按商品表价格重新计算总额，完全不信任客户端金额；若前后端金额不一致则拒绝下单。

  ```python
  server_total = round(sum(item["price"] * item["qty"] for item in items), 2)
  # 忽略客户端 total，或与 server_total 比对，不一致直接拒绝
  ```

- 修复验证：篡改 total 后订单金额仍为 ¥39.00，或请求被拒绝。

### SEC-03 支付卡号明文存储（高）

- 位置：`POST /pay/<order_id>`，`orders.card_number` 字段与服务端日志。
- 复现步骤：
  1. 完成一笔订单并使用测试卡号 `4242424242424242` 支付。
  2. 查询 SQLite：`SELECT card_number FROM orders WHERE id = ?`。
  3. 返回完整 16 位卡号；服务端控制台同时打印该卡号。
- 影响：违反 PCI DSS 对敏感认证数据的保护要求，数据库或日志泄露即导致持卡人数据泄露。
- 修复建议：不存储完整卡号；只保存后四位与支付令牌；日志脱敏；真实业务应使用支付服务商的托管收银台/令牌化方案。

  ```python
  masked = "**** **** **** " + card[-4:]
  db.execute("UPDATE orders SET card_last4 = ? WHERE id = ?", (card[-4:], order_id))
  ```

- 修复验证：数据库中不再出现完整卡号，日志仅显示掩码。

### SEC-12 用户密码明文存储（高）

- 位置：`POST /register`、`users.password` 字段、`POST /login` 校验逻辑。
- 复现步骤：
  1. 注册新用户 `plain_user`，密码 `PlainText#2026`。
  2. 查询 SQLite：`SELECT password FROM users WHERE username = 'plain_user'`。
  3. 返回结果与注册密码完全一致。
- 证据：注册时直接执行 `INSERT INTO users (username, password, ...) VALUES (?, ?, ...)`，登录时用明文比较。
- 影响：数据库一旦泄露，攻击者可直接获得全部账号密码，并可能在其他站点撞库；也违反最小化敏感数据存储原则。
- 修复建议：使用 bcrypt/argon2 等慢哈希算法加盐存储，登录时用 `check_password_hash` 校验，禁止任何位置的明文密码日志。

  ```python
  from werkzeug.security import generate_password_hash, check_password_hash

  db.execute(
      "INSERT INTO users (username, password) VALUES (?, ?)",
      (username, generate_password_hash(password)),
  )
  ```

- 修复验证：数据库中密码字段为哈希值；使用原密码仍可登录，错误密码被拒绝。

### SEC-04 搜索结果反射型 XSS（中）

- 位置：`shop/templates/index.html`，`{{ q|safe }}`。
- 复现步骤：访问 `/?q=<script>alert(1)</script>`。
- 证据：响应 HTML 中包含未转义的 `<script>alert(1)</script>`，浏览器执行弹窗。
- 影响：可构造钓鱼链接在受害者浏览器执行任意脚本，窃取会话或伪造操作。
- 修复建议：移除 `|safe`，依赖 Jinja2 自动转义；如需高亮搜索词，先转义再包裹 `<mark>`；增加 CSP 响应头。

- 修复验证：payload 以纯文本显示，页面源码中为 `&lt;script&gt;`。

### SEC-05 个人简介存储型 XSS（中）

- 位置：`shop/templates/profile.html`，`{{ user['bio']|safe }}`。
- 复现步骤：
  1. 注册并登录新账号。
  2. 在个人简介中保存 `<script>alert('stored')</script>`。
  3. 刷新个人中心，脚本被执行。
- 影响：脚本持久化在服务端，任何查看该资料的用户都会中招，危害高于反射型。
- 修复建议：同 SEC-04，移除 `|safe`；若业务允许富文本，使用白名单清洗库（如 bleach）并加 CSP。

- 修复验证：简介原样显示为文本，不再执行。

### SEC-06 注册无密码强度校验（中）

- 位置：`POST /register`。
- 复现步骤：注册用户名 `weak_user`、密码 `123`，注册成功并可正常登录。
- 影响：用户可设置极易猜测的密码，显著提高撞库与暴力破解成功率。
- 修复建议：服务端校验密码长度至少 8 位、包含多类字符、拒绝常见弱口令表；前端提示仅作辅助。

- 修复验证：密码 `123` 注册被拒绝并提示规则。

### SEC-07 登录接口无限速、无锁定（中）

- 位置：`POST /login`。
- 复现步骤：对 alice 连续提交 12 次错误密码，随后提交正确密码，仍可立即登录。
- 影响：可对账号进行在线暴力破解或撞库，且无告警。
- 修复建议：按账号 + IP 限速（如 5 次/分钟），连续失败递增锁定时间，必要时加入验证码；记录并告警异常登录。

- 修复验证：连续失败后返回 429 或要求验证码/锁定。

### SEC-08 退出登录后会话未失效（中）

- 位置：`GET /logout`。
- 复现步骤：
  1. 登录 alice，保存 Cookie 值。
  2. 调用 `/logout` 退出。
  3. 使用退出前的旧 Cookie 发起请求，仍可访问 `/profile`。
- 原因：Flask 默认使用客户端签名 Cookie 保存会话，退出只是让浏览器删除 Cookie，服务端没有会话撤销机制。
- 修复建议：启用服务端会话存储（Redis/数据库），登录时轮换会话 ID，退出时在服务端吊销；设置较短会话有效期。

- 修复验证：旧 Cookie 访问个人中心被重定向到登录页。

### SEC-09 写操作缺少 CSRF 防护（中）

- 位置：所有改变状态的接口，如 `POST /cart/clear`、`POST /checkout`。
- 复现步骤：登录后不携带任何 CSRF Token，直接 POST `/cart/clear`，购物车被清空。
- 影响：攻击者可诱导已登录用户访问恶意页面，借用户身份执行下单、清空购物车等操作。
- 修复建议：引入 Flask-WTF `CSRFProtect`，所有表单渲染并校验 token；Cookie 设置 `SameSite=Lax`。

  ```python
  from flask_wtf.csrf import CSRFProtect
  csrf = CSRFProtect(app)
  ```

- 修复验证：无 token 的 POST 请求返回 400。

### SEC-10 用户名枚举（低）

- 位置：`POST /login` 错误提示。
- 复现步骤：使用已存在用户 alice 与不存在用户分别登录，得到「密码错误」与「用户名不存在」两种提示。
- 影响：攻击者可先批量枚举有效账号，再定向爆破或钓鱼。
- 修复建议：统一提示为「用户名或密码错误」；保持响应时间一致；必要时增加登录失败延迟。

- 修复验证：两种情况的响应内容与耗时无显著差异。

### SEC-11 会话 Cookie 缺少 Secure 标志（低）

- 位置：登录响应的 `Set-Cookie`。
- 复现步骤：提交登录请求，检查响应头。
- 证据：`session=...; HttpOnly; Path=/`，缺少 `Secure`，未显式设置 `SameSite`。
- 影响：在 HTTPS 站点上，Cookie 可能通过明文 HTTP 请求泄露，增加会话劫持风险。
- 修复建议：生产环境启用 HTTPS 并设置：

  ```python
  app.config.update(
      SESSION_COOKIE_SECURE=True,
      SESSION_COOKIE_HTTPONLY=True,
      SESSION_COOKIE_SAMESITE="Lax",
  )
  ```

- 修复验证：Set-Cookie 包含 `Secure` 与 `SameSite=Lax`。

## 3. 修复优先级与回归计划

| 优先级 | 漏洞 | 建议处理时间 |
|---|---|---|
| P0 | SEC-01、SEC-02、SEC-03、SEC-12 | 演示/上线前必须修复 |
| P1 | SEC-04 ~ SEC-09 | 下一迭代修复 |
| P2 | SEC-10、SEC-11 | 随安全加固一并处理 |

回归方式：修复后重新执行 `python tests/security/security_scan.py`，预期 12 项检查全部显示「未发现」；同时执行功能测试与 UI 自动化，确认修复未破坏正常业务流程。

## 4. 测试局限

- 本次未使用商业/开源动态扫描器（如 OWASP ZAP、Burp Suite）做全站爬取，覆盖聚焦于作业要求的登录表单与支付流程；后续可补充自动扫描。
- 未测试真实的第三方支付网关，支付相关结论仅针对本地模拟网关及本系统自身的金额、卡号处理逻辑。
- 未覆盖文件上传、越权遍历全部接口、依赖组件 CVE 等方向，可作为后续扩展。

## 5. 结论

ShopLite 在登录认证、密码存储、结算金额处理与支付数据保护等关键环节存在高危缺陷，当前版本不适合部署到任何公开环境。按照第 3 节优先级修复后，需重新执行安全扫描与全量回归测试，确认漏洞关闭且业务功能正常。
