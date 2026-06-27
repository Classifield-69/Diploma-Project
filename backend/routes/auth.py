# routes/auth.py — authentication endpoints и admin_required декоратор.
# Паролите се хешират с bcrypt, authentication се прави чрез JWT.

import re
import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from mysql.connector import Error, IntegrityError
from database.connection import get_connection
from functools import wraps


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# Валидация
def is_valid_email(email):
    """Проверява дали email-а има валиден формат."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def is_valid_password(password):
    """Минимум 8 символа, поне една буква и поне една цифра."""
    if len(password) < 8:
        return False, "Паролата трябва да е поне 8 символа"
    if not re.search(r"[A-Za-z]", password):
        return False, "Паролата трябва да съдържа поне една буква"
    if not re.search(r"\d", password):
        return False, "Паролата трябва да съдържа поне една цифра"
    return True, None


def is_valid_username(username):
    """3–50 символа, само букви, цифри, точки, тирета и долни черти."""
    if len(username) < 3 or len(username) > 50:
        return False, "Username трябва да е между 3 и 50 символа"
    if not re.match(r"^[a-zA-Z0-9._-]+$", username):
        return False, "Username може да съдържа само букви, цифри, точки, тирета и долни черти"
    return True, None


# Endpoint: POST /api/auth/register
@auth_bp.route("/register", methods=["POST"])
def register():
    """Регистрира нов потребител и връща JWT токен. (201 | 400 | 409 | 500)"""
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "Липсва JSON тяло на заявката"}), 400

    username = data.get("username", "").strip()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"status": "error", "message": "Полетата username, email и password са задължителни"}), 400

    valid, error_msg = is_valid_username(username)
    if not valid:
        return jsonify({"status": "error", "message": error_msg}), 400

    if not is_valid_email(email):
        return jsonify({"status": "error", "message": "Невалиден email адрес"}), 400

    valid, error_msg = is_valid_password(password)
    if not valid:
        return jsonify({"status": "error", "message": error_msg}), 400

    password_bytes = password.encode("utf-8")
    password_hash  = bcrypt.hashpw(password_bytes, bcrypt.gensalt())

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, 'user')",
            (username, email, password_hash.decode("utf-8"))
        )
        connection.commit()
        user_id = cursor.lastrowid

        cursor.close()
        connection.close()

    except IntegrityError as e:
        error_str = str(e).lower()
        if "username" in error_str:
            return jsonify({"status": "error", "message": "Този username вече е зает"}), 409
        elif "email" in error_str:
            return jsonify({"status": "error", "message": "Този email вече е регистриран"}), 409
        else:
            return jsonify({"status": "error", "message": "Username или email вече съществуват"}), 409

    except Error as e:
        return jsonify({"status": "error", "message": "Грешка при записване в базата", "details": str(e)}), 500

    access_token = create_access_token(
        identity=str(user_id),
        additional_claims={"role": "user", "username": username}
    )

    return jsonify({
        "status": "ok",
        "message": "Регистрацията е успешна",
        "user": {"id": user_id, "username": username, "email": email, "role": "user"},
        "access_token": access_token
    }), 201


# Endpoint: POST /api/auth/login
@auth_bp.route("/login", methods=["POST"])
def login():
    """Логва потребител и връща JWT токен. (200 | 400 | 401 | 500)"""
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "Липсва JSON тяло на заявката"}), 400

    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"status": "error", "message": "Полетата email и password са задължителни"}), 400

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, username, email, password_hash, role FROM users WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()

        cursor.close()
        connection.close()

    except Error as e:
        return jsonify({"status": "error", "message": "Грешка при достъп до базата", "details": str(e)}), 500

    # Едно и също съобщение за "няма такъв email" и "грешна парола"
    # — предотвратява username enumeration атаки
    if user is None:
        return jsonify({"status": "error", "message": "Грешен email или парола"}), 401

    password_bytes     = password.encode("utf-8")
    stored_hash_bytes  = user["password_hash"].encode("utf-8")

    if not bcrypt.checkpw(password_bytes, stored_hash_bytes):
        return jsonify({"status": "error", "message": "Грешен email или парола"}), 401

    access_token = create_access_token(
        identity=str(user["id"]),
        additional_claims={"role": user["role"], "username": user["username"]}
    )

    return jsonify({
        "status": "ok",
        "message": "Успешен login",
        "user": {"id": user["id"], "username": user["username"], "email": user["email"], "role": user["role"]},
        "access_token": access_token
    }), 200


# Endpoint: GET /api/auth/me
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Връща пресни данни за текущия логнат потребител. (200 | 401 | 404 | 500)"""
    user_id = get_jwt_identity()

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, username, email, role, created_at FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        cursor.close()
        connection.close()

    except Error as e:
        return jsonify({"status": "error", "message": "Грешка при достъп до базата", "details": str(e)}), 500

    if user is None:
        return jsonify({"status": "error", "message": "Потребителят не съществува"}), 404

    return jsonify({
        "status": "ok",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "created_at": user["created_at"].isoformat() if user["created_at"] else None
        }
    }), 200


# Декоратор: admin_required
def admin_required(fn):
    """
    Декоратор за admin-only endpoint-и.

    ВАЖНО: трябва да е под @jwt_required() — JWT се валидира първо,
    после се чете role от claims-овете.

        @jwt_required()
        @admin_required
        def my_endpoint(): ...

    Връща 403 ако потребителят не е admin.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"status": "error", "message": "Достъпът е разрешен само за администратори"}), 403
        return fn(*args, **kwargs)
    return wrapper