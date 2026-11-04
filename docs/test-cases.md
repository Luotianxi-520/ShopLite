# ShopLite 测试用例

| 项目 | 内容 |
|---|---|
| 被测版本 | ShopLite v1.0 |
| 编写日期 | 2026-10-29 |
| 编号规则 | F-功能、UI-界面、SEC-安全 |
| 优先级 | P0 核心、P1 重要、P2 一般 |

用例执行方式：功能用例全部由 pytest 自动化执行（`tests/functional/`）；UI 用例部分自动化（`tests/ui/`）、部分人工检查；安全用例由扫描脚本执行（`tests/security/security_scan.py`）并归档到安全报告。

## 1. 功能用例

### 1.1 购物车（F-001 ~ F-012）

| 编号 | 用例标题 | 前置条件 | 步骤 | 预期结果 | 优先级 | 自动化对应 |
|---|---|---|---|---|---|---|
| F-001 | 游客加入购物车 | 未登录；商品库存大于 0 | 打开商品详情，点击「加入购物车」 | 提示加购成功；购物车含该商品，金额正确 | P0 | test_add_to_cart_as_guest |
| F-002 | 重复加购累加数量 | 购物车已有 1 件陶瓷马克杯 | 再次加购同一商品 | 数量为 2，小计 ¥78.00 | P0 | test_add_same_product_twice_increments_quantity |
| F-003 | 修改数量并重算金额 | 购物车有无线蓝牙耳机 1 件 | 数量改为 3 并更新 | 数量 3，小计与合计均为 ¥597.00 | P0 | test_update_quantity_recalculates_subtotal |
| F-004 | 数量超过库存被截断 | 跳绳库存 2，购物车 1 件 | 数量改为 9 并更新 | 数量截断为 2，提示库存不足 | P1 | test_quantity_over_stock_is_capped |
| F-005 | 数量改为 0 移除商品 | 购物车有商品 | 数量改为 0 并更新 | 商品移除，提示已移出购物车 | P1 | test_update_quantity_to_zero_removes_item |
| F-006 | 删除单个商品 | 购物车有耳机和马克杯 | 删除耳机 | 仅耳机被移除，马克杯保留 | P1 | test_remove_item |
| F-007 | 清空购物车 | 购物车有商品 | 点击「清空购物车」 | 购物车为空并提示已清空 | P1 | test_clear_cart |
| F-008 | 缺货商品禁止加购 | 智能手表库存为 0 | 尝试加入购物车 | 提示暂时缺货，购物车仍为空 | P0 | test_out_of_stock_product_cannot_be_added |
| F-009 | 购物车合计金额正确 | 耳机 ¥199×1，马克杯 ¥39×2 | 打开购物车 | 合计 ¥277.00 | P0 | test_cart_total_sums_all_items |
| F-010 | 游客购物车登录后合并 | 游客已加购机械键盘 | 登录 alice 后打开购物车 | 机械键盘保留在购物车 | P0 | test_guest_cart_merged_after_login |
| F-011 | 合并时数量叠加 | alice 购物车 1 件；游客 1 件 | 游客登录 alice | 同一商品数量合并为 2 | P1 | test_guest_cart_quantities_merge_with_existing_cart |
| F-012 | 加购不存在商品 | 无 | POST /cart/add/9999 | 返回 404 | P2 | test_add_unknown_product_returns_404 |

### 1.2 商品筛选与分页（F-013 ~ F-024）

| 编号 | 用例标题 | 前置条件 | 步骤 | 预期结果 | 优先级 | 自动化对应 |
|---|---|---|---|---|---|---|
| F-013 | 按分类筛选 | 20 件商品已加载 | 选择「电子产品」并筛选 | 6 件，且分类均为电子产品 | P0 | test_filter_by_category |
| F-014 | 按价格区间筛选 | 同上 | 最低 100、最高 300 | 7 件，价格均在 [100, 300] | P0 | test_filter_by_price_range |
| F-015 | 价格边界值包含 | 同上 | 最低=最高=39 | 仅陶瓷马克杯（¥39） | P1 | test_price_boundary_is_inclusive |
| F-016 | 关键字搜索 | 同上 | 搜索「键盘」 | 仅机械键盘 | P0 | test_search_by_keyword |
| F-017 | 搜索无结果 | 同上 | 搜索不存在的商品 | 显示「未找到相关商品」空状态 | P1 | test_search_without_results_shows_empty_state |
| F-018 | 组合筛选 | 同上 | 分类=图书，最高价 100 | 3 件图书，价格均 ≤100 | P1 | test_combined_filters |
| F-019 | 价格升序排序 | 同上 | 排序=价格从低到高 | 第一页 8 件价格非递减 | P1 | test_sort_by_price_ascending |
| F-020 | 价格降序排序 | 同上 | 排序=价格从高到低 | 第一页 8 件价格非递增 | P1 | test_sort_by_price_descending |
| F-021 | 分页内容互不重复 | 同上 | 依次访问第 1/2/3 页 | 8/8/4 件，三页无重复且合计 20 | P1 | test_pagination_pages_are_disjoint |
| F-022 | 页码越界收敛 | 同上 | 访问 page=99 | 收敛到最后一页，显示 4 件 | P2 | test_page_out_of_range_is_clamped |
| F-023 | 非法价格参数忽略 | 同上 | min_price=abc | 忽略该条件，正常显示第一页 8 件 | P2 | test_invalid_price_input_is_ignored |
| F-024 | 搜索特殊字符不崩溃 | 同上 | 搜索 `' OR '1'='1` | 200，无结果，不出现 500 | P1 | test_search_special_characters_do_not_crash |

### 1.3 结算与支付（F-025 ~ F-035）

| 编号 | 用例标题 | 前置条件 | 步骤 | 预期结果 | 优先级 | 自动化对应 |
|---|---|---|---|---|---|---|
| F-025 | 未登录结算被拦截 | 游客有购物车 | 访问 /checkout | 302 跳转登录页 | P0 | test_checkout_requires_login |
| F-026 | 结算页显示清单与金额 | alice 登录，马克杯 ×2 | 打开结算页 | 显示商品、¥78.00，隐藏 total=78.00 | P0 | test_checkout_page_shows_cart_summary |
| F-027 | 结算页预填收货信息 | alice 登录 | 打开结算页 | 收货人 alice，地址为资料地址 | P1 | test_checkout_prefills_profile |
| F-028 | 结算表单校验 | 登录且有购物车 | 空姓名、空地址、手机号 abc 提交 | 3 条错误提示，不创建订单 | P0 | test_checkout_validation_errors |
| F-029 | 提交生成待支付订单 | 同上 | 填写合法信息提交 | 订单 pending，总额 78，明细 2 件 | P0 | test_checkout_creates_pending_order |
| F-030 | 空购物车结算 | 登录，购物车为空 | 访问 /checkout | 提示购物车为空并回购物车页 | P1 | test_checkout_with_empty_cart_redirects |
| F-031 | 支付成功流程 | 有待支付订单 | 提交 4242 卡号 | 订单已支付，购物车清空，订单历史可见 | P0 | test_payment_success_flow |
| F-032 | 支付失败流程 | 有待支付订单 | 提交 0002 卡号 | 提示支付失败，订单仍待支付，购物车保留 | P0 | test_payment_declined_keeps_order_pending |
| F-033 | 支付卡号格式校验 | 有待支付订单 | 卡号填 1234 | 提示格式不正确，订单仍待支付 | P1 | test_payment_invalid_card_format |
| F-034 | 取消支付 | 有待支付订单 | 点击「取消支付」 | 订单状态变为已取消 | P1 | test_cancel_payment |
| F-035 | 订单越权访问 | alice 已创建订单 | bob 访问该订单详情和支付接口 | 均返回 404 | P0 | test_order_detail_only_visible_to_owner |

### 1.4 用户与登录（F-036 ~ F-045）

| 编号 | 用例标题 | 前置条件 | 步骤 | 预期结果 | 优先级 | 自动化对应 |
|---|---|---|---|---|---|---|
| F-036 | 注册后登录 | 用户名 carol 不存在 | 注册 carol 后登录 | 注册成功提示，登录成功 | P1 | test_register_then_login |
| F-037 | 重复用户名注册 | alice 已存在 | 注册 alice | 提示用户名已存在 | P1 | test_register_duplicate_username |
| F-038 | 注册必填校验 | 无 | 空用户名、空密码提交 | 提示用户名和密码不能为空 | P1 | test_register_requires_username_and_password |
| F-039 | 密码错误登录 | alice 存在 | 使用错误密码登录 | 提示密码错误 | P0 | test_login_with_wrong_password |
| F-040 | 不存在用户登录 | 无 | 使用不存在用户名登录 | 提示用户名不存在 | P1 | test_login_with_unknown_user |
| F-041 | 退出登录清除状态 | alice 已登录 | 点击退出登录 | 会话清除，导航出现登录/注册 | P0 | test_logout_clears_session |
| F-042 | 登录后回跳结算页 | 游客有购物车 | 带 next=/checkout 登录 | 登录成功并进入结算页 | P1 | test_login_redirects_back_to_checkout |
| F-043 | 拒绝外部 next 跳转 | 无 | next=//evil.example 登录 | 跳转站内首页，不跳外部站 | P1 | test_login_rejects_external_next_url |
| F-044 | 个人中心需登录 | 未登录 | 访问 /profile | 302 跳转登录页 | P1 | test_profile_requires_login |
| F-045 | 更新个人资料 | alice 已登录 | 修改邮箱、地址、简介并保存 | 保存成功，页面显示新值 | P1 | test_update_profile |

## 2. UI 一致性用例（UI-001 ~ UI-010）

| 编号 | 检查项 | 前置条件 | 步骤 | 预期结果 | 优先级 | 执行方式 |
|---|---|---|---|---|---|---|
| UI-001 | 公共头部与页脚 | 打开 /、/login、/register、/cart、/product/1 | 检查每页 | 均有统一 header 与 footer | P0 | Selenium 自动化 |
| UI-002 | 页面标题格式 | 同上 | 读取浏览器标题 | 均以「 · ShopLite」结尾 | P0 | Selenium 自动化 |
| UI-003 | 主导航一致性 | 同上 | 检查导航文本 | 均含首页、购物车、我的订单 | P1 | Selenium 自动化 |
| UI-004 | 主按钮视觉一致 | 上述页面及有商品的购物车页 | 读取 .btn-primary 背景色 | 所有页面颜色一致（#2563eb） | P1 | Selenium 自动化 |
| UI-005 | 品牌标识一致 | 同上 | 检查左上角品牌 | 均显示 🛒 ShopLite | P2 | Selenium 自动化 |
| UI-006 | 响应式布局 | 1440×900、768 宽、375 宽 | 截图检查 | 无横向滚动，卡片与表单不重叠 | P1 | 人工截图 |
| UI-007 | 字体与字号层级 | 主要页面 | 人工比对 | 页面标题 > 卡片标题 > 正文 > 辅助文字 | P2 | 人工检查 |
| UI-008 | 表单错误提示样式 | 登录、结算 | 触发校验错误 | 统一为页面顶部 flash 提示 | P1 | 人工 + 自动化断言 |
| UI-009 | 空状态样式 | 空购物车、无订单、无搜索结果 | 打开对应页面 | 统一为虚线卡片空状态 | P2 | 人工检查 |
| UI-010 | 页脚版权信息 | 上述五个页面 | 检查页脚 | 均含「© 2026 ShopLite」 | P1 | Selenium 自动化 |

## 3. 安全用例（SEC-01 ~ SEC-12）

| 编号 | 检查项 | 风险等级 | 攻击步骤 | 修复前现象 | 自动化 |
|---|---|---|---|---|---|
| SEC-01 | 登录表单 SQL 注入 | 高 | 用户名输入 `' OR '1'='1' -- `，密码任意 | 绕过密码直接登录成功 | check_sql_injection |
| SEC-02 | 结算金额客户端篡改 | 高 | 抓包把 hidden 字段 total 从 39.00 改为 0.01 | 订单金额变为 0.01 元 | check_price_tampering |
| SEC-03 | 支付卡号明文存储 | 高 | 完成支付后查询数据库 | 完整卡号明文保存在 orders 表 | check_card_storage |
| SEC-04 | 反射型 XSS | 中 | 搜索参数传入 `<script>alert(1)</script>` | 脚本原样输出到页面 | check_reflected_xss |
| SEC-05 | 存储型 XSS | 中 | 个人简介保存 script 标签后刷新页面 | 个人中心原样渲染脚本 | check_stored_xss |
| SEC-06 | 弱口令策略缺失 | 中 | 注册密码使用 123 | 注册成功且可登录 | check_weak_password |
| SEC-07 | 登录无限速/锁定 | 中 | 连续 12 次错误密码后使用正确密码 | 仍可立即登录，无锁定 | check_brute_force |
| SEC-08 | 退出登录后会话未失效 | 中 | 登录后保存 Cookie，退出后回放旧 Cookie | 仍可访问个人中心 | check_session_after_logout |
| SEC-09 | 写操作缺少 CSRF 防护 | 中 | 无 Token 直接 POST /cart/clear | 购物车被清空 | check_csrf |
| SEC-10 | 用户名枚举 | 低 | 对比存在用户与不存在用户的错误提示 | 提示可区分，可枚举账号 | check_user_enumeration |
| SEC-11 | 会话 Cookie 缺少 Secure | 低 | 检查登录响应 Set-Cookie | 无 Secure 标志 | check_cookie_flags |
| SEC-12 | 用户密码明文存储 | 高 | 注册新账号后查询 users 表 | password 字段为明文 | check_plaintext_password |

## 4. 执行结果汇总

| 类型 | 用例数 | 执行方式 | 结果 |
|---|---|---|---|
| 功能测试 | 45 | pytest 自动化 | 全部通过 |
| UI 自动化 | 8 | Selenium + pytest | 全部通过 |
| UI 人工检查 | 4 | 人工截图/比对 | 通过（见测试计划检查单） |
| 安全测试 | 12 | 扫描脚本 | 发现 12 项（高 4 / 中 6 / 低 2） |

详细执行结果见 `reports/functional-report.html`、`reports/ui-report.html` 与 `docs/security-report.md`。
