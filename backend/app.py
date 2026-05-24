"""
Главна входна точка на backend приложението.

Това е Flask сървърът, който обработва всички HTTP заявки от frontend-а.
Стартира се с: python backend/app.py

Структура:
- app.py – инициализация и конфигурация (този файл)
- routes/ – endpoint-и, разделени по теми (Blueprint-и)
- database/ – модули за работа с базата
- config.py – конфигурация от .env
"""

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

import config
from routes.health import health_bp
from routes.auth import auth_bp
from routes.movies import movies_bp
from routes.reviews import reviews_bp


# ============================================================
# Инициализация на Flask приложението
# ============================================================
app = Flask(
    __name__,
    static_folder="../frontend",
    static_url_path="/static"
)
app.json.ensure_ascii = False  # позволява кирилица в JSON отговорите

# Валидираме конфигурацията при стартиране
config.validate_config()

# CORS позволява на frontend (на различен порт) да прави заявки към backend
CORS(app)

# ============================================================
# Конфигурация на JWT (JSON Web Tokens)
# ============================================================
# JWT_SECRET_KEY се ползва за подписване на токените – без него
# никой не може да създава или верифицира токени
app.config["JWT_SECRET_KEY"] = config.JWT_SECRET_KEY

# Срок на валидност на access токените (от config.py, по подразбиране 24 часа)
from datetime import timedelta
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=config.JWT_ACCESS_TOKEN_EXPIRES_HOURS)

# Инициализираме JWT manager-а – закачваме го към приложението
jwt = JWTManager(app)

# ============================================================
# Регистриране на Blueprint-и
# ============================================================
# Всеки Blueprint съдържа група от свързани endpoint-и.
# Тук ги "закачаме" към главното приложение.
app.register_blueprint(health_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(movies_bp)
app.register_blueprint(reviews_bp)


# ============================================================
# Стартиране на dev сървъра
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Стартиране на Movie Reviews Backend")
    print("=" * 60)
    print(f"   Host:  {config.FLASK_HOST}")
    print(f"   Port:  {config.FLASK_PORT}")
    print(f"   Debug: {config.FLASK_DEBUG}")
    print(f"   База:  {config.DB_NAME}")
    print("=" * 60)
    print(f"📡 Endpoints:")
    for rule in app.url_map.iter_rules():
        # Прескачаме статичните файлове на Flask
        if rule.endpoint == "static":
            continue
        methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        print(f"   [{methods:7s}] http://{config.FLASK_HOST}:{config.FLASK_PORT}{rule.rule}")
    print("=" * 60)

    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG
    )