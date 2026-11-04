"""SQLite 数据库：建表、种子数据、命令行初始化。"""
import os
import sqlite3
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.environ.get("SHOP_DB") or os.path.join(ROOT_DIR, "shop.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT DEFAULT '',
    address TEXT DEFAULT '',
    bio TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL,
    emoji TEXT DEFAULT '📦',
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    UNIQUE (user_id, product_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total REAL NOT NULL,
    name TEXT DEFAULT '',
    address TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    card_number TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL
);
"""

# (name, category, price, stock, emoji, description)
SEED_PRODUCTS = [
    ("无线蓝牙耳机", "电子产品", 199.0, 15, "🎧", "主动降噪，单次续航 30 小时，支持快充。"),
    ("机械键盘", "电子产品", 399.0, 8, "⌨️", "87 键热插拔轴体，PBT 键帽。"),
    ("27 英寸显示器", "电子产品", 1299.0, 5, "🖥️", "2K 分辨率，75Hz 刷新率，低蓝光。"),
    ("移动电源", "电子产品", 129.0, 30, "🔋", "20000mAh 大容量，双向快充。"),
    ("智能手表", "电子产品", 899.0, 0, "⌚", "血氧与心率监测，50 米防水。"),
    ("USB-C 充电器", "电子产品", 79.0, 50, "🔌", "65W 氮化镓，三口输出。"),
    ("Python 编程入门", "图书", 59.0, 20, "📘", "零基础入门，含 40 个实战案例。"),
    ("软件测试的艺术", "图书", 45.0, 12, "📗", "经典测试入门读物，第 3 版。"),
    ("算法导论", "图书", 128.0, 6, "📕", "计算机算法领域经典教材。"),
    ("深入理解计算机系统", "图书", 139.0, 3, "📙", "从程序员视角理解计算机系统。"),
    ("产品经理手册", "图书", 68.0, 0, "📓", "产品思维与方法论入门。"),
    ("陶瓷马克杯", "家居", 39.0, 40, "☕", "350ml 哑光釉面，可进微波炉。"),
    ("香薰蜡烛", "家居", 59.0, 25, "🕯️", "大豆蜡配方，雪松香型。"),
    ("记忆棉枕头", "家居", 159.0, 10, "🛏️", "慢回弹记忆棉，护颈设计。"),
    ("桌面收纳盒", "家居", 29.0, 60, "🗃️", "可叠放设计，桌面整理利器。"),
    ("便携台灯", "家居", 89.0, 18, "💡", "三档色温，USB 供电。"),
    ("瑜伽垫", "运动户外", 79.0, 22, "🧘", "加厚防滑，附收纳带。"),
    ("登山背包", "运动户外", 299.0, 7, "🎒", "40L 容量，防泼水面料。"),
    ("保温水壶", "运动户外", 119.0, 35, "🥤", "316 不锈钢，保温 12 小时。"),
    ("跳绳", "运动户外", 25.0, 2, "🪢", "可调节长度，轴承顺滑。"),
]

# (username, password, email, address)
SEED_USERS = [
    ("alice", "alice123", "alice@example.com", "北京市朝阳区测试路 1 号"),
    ("bob", "bob123", "bob@example.com", "上海市浦东新区测试路 2 号"),
]


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path, reset=False):
    """建表并写入种子数据（仅在表为空时写入）。"""
    if reset and os.path.exists(db_path):
        os.remove(db_path)
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO products (name, category, price, stock, emoji, description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                SEED_PRODUCTS,
            )
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO users (username, password, email, address) VALUES (?, ?, ?, ?)",
                SEED_USERS,
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db(DEFAULT_DB, reset="--reset" in sys.argv)
    print(f"数据库已初始化：{DEFAULT_DB}")
