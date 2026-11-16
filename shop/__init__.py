"""ShopLite 应用工厂。"""
from pathlib import Path

from flask import Flask, g, render_template

from . import db

PRODUCT_IMAGE_EXTS = (".jpeg", ".jpg", ".png", ".webp")


def get_db():
    """每个请求复用同一个 SQLite 连接。"""
    from flask import current_app

    if "db" not in g:
        g.db = db.connect(current_app.config["DATABASE"])
    return g.db


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "shoplite-course-secret-key"
    app.config["DATABASE"] = db_path or db.DEFAULT_DB

    image_dir = Path(app.static_folder) / "images" / "products"

    def product_image(product_id):
        """按商品 ID 查找本地图片；找不到时返回 None，由模板回退到 emoji。"""
        for ext in PRODUCT_IMAGE_EXTS:
            name = f"{product_id}{ext}"
            if (image_dir / name).exists():
                return f"images/products/{name}"
        return None

    app.jinja_env.globals["product_image"] = product_image

    from .views import bp, cart_count, logged_in_username

    app.register_blueprint(bp)

    @app.teardown_appcontext
    def close_db(_exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.context_processor
    def inject_globals():
        return {
            "cart_count": cart_count(),
            "current_username": logged_in_username(),
        }

    @app.errorhandler(404)
    def not_found(_err):
        return render_template("404.html"), 404

    return app
