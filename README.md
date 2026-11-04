# ShopLite 电商测试项目

一个用于软件测试课程的小型电商网站，包含商品列表、购物车、结算支付、用户中心，以及配套的功能测试、UI 一致性测试、Selenium 自动化测试和安全测试报告。

## 功能范围

- 商品：列表、关键字搜索、分类/价格筛选、排序、分页、详情
- 购物车：加购、改数量、删除、清空、库存上限、游客购物车登录合并
- 结算：收货信息校验、订单确认、模拟支付（成功/失败/取消）、订单历史
- 用户：注册、登录、个人中心、资料编辑

## 技术栈

| 部分 | 技术 |
|---|---|
| Web 应用 | Python 3 + Flask + SQLite + Jinja2 |
| 功能测试 | pytest + Flask test client |
| UI 自动化 | Selenium 4 + pytest + Page Object Model（Microsoft Edge 无头模式） |
| 安全测试 | requests 手工 payload + SQLite 数据核验 |
| 测试报告 | pytest-html |

## 快速开始

```bash
python -m pip install -r requirements.txt
python run.py
```

浏览器打开 <http://127.0.0.1:5000>。首次启动会自动创建 `shop.db` 并写入种子数据（20 件商品、4 个分类、2 个测试账号）。

重置数据库：

```bash
python -m shop.db --reset
```

测试账号：

| 账号 | 密码 | 说明 |
|---|---|---|
| alice | alice123 | 主测试账号 |
| bob | bob123 | 用于越权/隔离测试 |

模拟支付测试卡：

| 卡号 | 结果 |
|---|---|
| 4242 4242 4242 4242 | 支付成功 |
| 4000 0000 0000 0002 | 支付失败 |

## 运行效果

截图见 `reports/screenshots/`（首页、商品详情、购物车、结算、支付、订单详情）。启动 `python run.py` 后可访问 <http://127.0.0.1:5000> 实际体验完整购买流程。

## 测试执行

功能测试（共 45 条自动化用例）：

```bash
mkdir reports
pytest tests/functional --html=reports/functional-report.html --self-contained-html
```

UI 自动化测试（需要安装 Microsoft Edge）：

```bash
pytest tests/ui --html=reports/ui-report.html --self-contained-html
```

脚本优先使用仓库内 `drivers/msedgedriver.exe`（与本机 Edge 156.0.4314.50 匹配）。如果该文件不存在，或与对方的 Edge 版本不匹配导致启动失败，会自动回退到 Selenium Manager 下载匹配驱动；网络受限时可手动下载对应版本驱动放入 `drivers/`。

安全测试扫描（自动启动临时环境，输出 12 项检查结果）：

```bash
python tests/security/security_scan.py
```

说明：功能测试、UI 测试和安全扫描都使用临时数据库，不会改动本地 `shop.db`；UI 测试每个用例前会重建数据库，用例之间互不依赖。

## 目录结构

```
shop/                        被测系统
  __init__.py                应用工厂
  views.py                   路由与业务逻辑
  db.py                      建表与种子数据
  templates/                 页面模板
  static/style.css           统一样式
tests/
  functional/                功能测试（pytest + test client）
    test_cart.py             购物车
    test_filtering.py        商品筛选/搜索/分页
    test_checkout.py         结算与支付
    test_auth.py             登录/注册/个人中心
  ui/                        Selenium 自动化
    pages/                   Page Object
    test_purchase_flow.py    核心购买链路 + 异常流
    test_ui_consistency.py   UI 一致性断言
  security/
    security_scan.py         安全测试扫描脚本
docs/
  test-plan.md               测试计划
  test-cases.md              测试用例与追溯矩阵
  security-report.md         安全测试报告
```

## 打包分享给别人

推荐只打包运行所需文件和最终报告，不要带缓存和个人数据库。Windows PowerShell 示例：

```powershell
Compress-Archive -Path shop,tests,docs,drivers,reports,README.md,requirements.txt,pytest.ini,run.py,.gitignore -DestinationPath ShopLite.zip
```

对方解压后执行：

```bash
python -m pip install -r requirements.txt
python run.py
```

注意事项：

- 需要 Python 3.10+；首次安装依赖需要联网（`requirements.txt` 使用 `>=`，pip 会自动选择与对方 Python 版本兼容的版本）。
- UI 自动化需要安装 Microsoft Edge。`drivers/msedgedriver.exe` 只匹配 Edge 156；对方 Edge 版本不同时，测试会自动回退到 Selenium Manager 下载匹配驱动（需要联网），也可以手动下载对应版本放入 `drivers/`。
- 不要打包 `shop.db`（首次启动会自动建库并写入种子数据）、`__pycache__`、`.pytest_cache`、`.claude/`。`reports/` 是最终测试报告与截图，可直接附带。
- macOS / Linux 上功能测试和安全扫描可以正常运行；UI 自动化需要自行安装 Edge，或把 `tests/ui/conftest.py` 改为使用 Chrome。
- 如果对方完全离线，可在相同操作系统 + 相同 Python 版本的环境执行 `pip download -r requirements.txt -d wheels`，再让对方执行 `pip install --no-index --find-links wheels -r requirements.txt`。

## 交付物

1. 可运行的被测系统（本仓库 `shop/`）
2. 测试计划（`docs/test-plan.md`）
3. 测试用例表与需求追溯矩阵（`docs/test-cases.md`）
4. Selenium 自动化工程与 HTML 报告（`tests/ui/`、`reports/`）
5. 安全测试报告（`docs/security-report.md`）
6. 安全扫描脚本（`tests/security/security_scan.py`）

## 重要说明

- 模拟支付网关不是真实支付，不会产生任何扣款。
- 该系统为课程安全测试**刻意保留了常见安全弱点**（SQL 注入、XSS、金额篡改、明文卡号等），只能在本机课程环境运行，**不要部署到公网或用于真实数据**。
- 安全测试只允许针对本仓库启动的本地实例执行。
