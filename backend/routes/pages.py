"""
Blueprint за HTML страниците на frontend-а.

Всеки route тук връща HTML файл от frontend/ папката.
JavaScript-ът вътре в HTML файла после прави fetch заявки
към API endpoint-ите (/api/movies, /api/auth/login, и т.н.)
за реалните данни.

Структурата е инкрементална – нови route-ове се добавят
само когато се прави съответната HTML страница.
"""

import os
from flask import Blueprint, send_from_directory

pages_bp = Blueprint("pages", __name__)

# Абсолютен път до frontend/ папката.
# __file__ = backend/routes/pages.py
# os.path.dirname(__file__) = backend/routes
# .. = backend
# ../.. = главната папка (Diploma-Project)
# ../../frontend = frontend/ папката
FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
)


@pages_bp.route("/")
def index():
    """Главна страница – списък с филми."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@pages_bp.route("/movies/<int:movie_id>")
def movie_details(movie_id):
    """
    Страница за детайли на филм.

    movie_id се извлича от URL-а, но не се ползва в Python код –
    JavaScript-ът (reviews.js) ще го прочете отново от window.location
    и ще извика /api/movies/<id> и /api/movies/<id>/reviews.

    Защо така: backend-ът сервира статичен HTML, frontend-ът прави
    динамичните заявки за данни. Това позволява cache-ване на HTML-а
    и държи route handler-а тривиален.
    """
    return send_from_directory(FRONTEND_DIR, "movie-details.html")


@pages_bp.route("/login")
def login():
    """Login страница – форма за email + password."""
    return send_from_directory(FRONTEND_DIR, "login.html")


@pages_bp.route("/register")
def register():
    """Регистрационна страница – форма за нов акаунт."""
    return send_from_directory(FRONTEND_DIR, "register.html")