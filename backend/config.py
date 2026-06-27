"""
Конфигурационен модул за backend приложението.

Чете променливите от .env файла и ги предоставя като Python константи.
Никога не пишем чувствителни данни (пароли, ключове) директно в кода –
всичко е външно в .env, който не се качва в Git.
"""

import os
from dotenv import load_dotenv

# Зареждаме .env файла от коренната папка на проекта
# load_dotenv() автоматично търси .env нагоре по дървото
load_dotenv()


# Конфигурация на базата данни
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


# Конфигурация на Flask приложението
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5001))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"


# Конфигурация на JWT (за по-късно, когато добавим authentication)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
JWT_ACCESS_TOKEN_EXPIRES_HOURS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", 24))


# Валидация – проверяваме че критичните променливи са заредени
def validate_config():
    required = {
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
        "DB_NAME": DB_NAME,
    }
    
    missing = [name for name, value in required.items() if not value]
    
    if missing:
        raise ValueError(
            f"Липсват задължителни променливи в .env файла: {', '.join(missing)}"
        )