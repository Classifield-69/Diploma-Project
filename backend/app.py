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

import config
from routes.health import health_bp


# ============================================================
# Инициализация на Flask приложението
# ============================================================
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False  # позволява кирилица в JSON отговорите

# Валидираме конфигурацията при стартиране
config.validate_config()

# CORS позволява на frontend (на различен порт) да прави заявки към backend
CORS(app)


# ============================================================
# Регистриране на Blueprint-и
# ============================================================
# Всеки Blueprint съдържа група от свързани endpoint-и.
# Тук ги "закачаме" към главното приложение.
app.register_blueprint(health_bp)


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
    print(f"   http://{config.FLASK_HOST}:{config.FLASK_PORT}/health")
    print(f"   http://{config.FLASK_HOST}:{config.FLASK_PORT}/api/db-status")
    print("=" * 60)
    
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG
    )