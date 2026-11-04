"""启动 ShopLite:python run.py,访问 http://127.0.0.1:5000"""
from shop import create_app
from shop.db import DEFAULT_DB, init_db

app = create_app()

if __name__ == "__main__":
    init_db(DEFAULT_DB)
    app.run(host="127.0.0.1", port=5000, debug=False)
