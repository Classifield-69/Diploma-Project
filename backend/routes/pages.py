# routes/pages.py — сервира HTML файловете от frontend/ папката.

import os
from flask import Blueprint, send_from_directory

pages_bp = Blueprint("pages", __name__)

# __file__ = backend/routes/pages.py → ../../frontend = frontend/
FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
)


@pages_bp.route("/")
def index():
    """Главна страница."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@pages_bp.route("/movies/<int:movie_id>")
def movie_details(movie_id):
    """
    Страница за детайли на филм.
    movie_id не се ползва в Python — reviews.js го чете от window.location
    и сам извиква /api/movies/<id> и /api/movies/<id>/reviews.
    """
    return send_from_directory(FRONTEND_DIR, "movie-details.html")


@pages_bp.route("/login")
def login():
    """Login страница."""
    return send_from_directory(FRONTEND_DIR, "login.html")


@pages_bp.route("/register")
def register():
    """Регистрационна страница."""
    return send_from_directory(FRONTEND_DIR, "register.html")