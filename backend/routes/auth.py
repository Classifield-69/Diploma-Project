"""
Blueprint за authentication endpoints.

Този модул се грижи за:
- Регистрация на нови потребители (POST /api/auth/register)
- Login на съществуващи потребители (POST /api/auth/login)
- Информация за текущия потребител (GET /api/auth/me)

Сигурност:
- Паролите се хешират с bcrypt преди записване в базата
- Authentication се прави чрез JWT (JSON Web Tokens)
"""

import re
import bcrypt
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from mysql.connector import Error, IntegrityError
from database.connection import get_connection


# ============================================================
# Създаваме Blueprint с url_prefix
# ============================================================
# url_prefix="/api/auth" означава, че всички endpoint-и в този
# Blueprint автоматично започват с /api/auth/...
# Например: @auth_bp.route("/register") става /api/auth/register
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ============================================================
# Помощни функции за валидация
# ============================================================
def is_valid_email(email):
    """Проверява дали email-а има валиден формат."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def is_valid_password(password):
    """
    Проверява дали паролата отговаря на минималните изисквания за сигурност.
    Изисквания: минимум 8 символа, поне една буква и поне една цифра.
    """
    if len(password) < 8:
        return False, "Паролата трябва да е поне 8 символа"
    if not re.search(r"[A-Za-z]", password):
        return False, "Паролата трябва да съдържа поне една буква"
    if not re.search(r"\d", password):
        return False, "Паролата трябва да съдържа поне една цифра"
    return True, None


def is_valid_username(username):
    """
    Проверява дали username-а е валиден.
    Изисквания: 3-50 символа, букви, цифри, точки, тирета и долни черти.
    """
    if len(username) < 3 or len(username) > 50:
        return False, "Username трябва да е между 3 и 50 символа"
    if not re.match(r"^[a-zA-Z0-9._-]+$", username):
        return False, "Username може да съдържа само букви, цифри, точки, тирета и долни черти"
    return True, None


# ============================================================
# Endpoint: POST /api/auth/register
# ============================================================
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Регистрира нов потребител в системата.
    
    Очаквано тяло на заявката (JSON):
    {
        "username": "petur",
        "email": "petur@example.com",
        "password": "силна_парола_123"
    }
    
    Връща:
    - 201: Успешна регистрация, заедно с JWT токен
    - 400: Невалидни данни (липсващи полета, грешен формат)
    - 409: Username или email вече съществуват
    - 500: Сървърна грешка
    """
    # ----- Стъпка 1: Извличане на данните от JSON тялото -----
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "Липсва JSON тяло на заявката"
        }), 400
    
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    # ----- Стъпка 2: Валидация на полетата -----
    if not username or not email or not password:
        return jsonify({
            "status": "error",
            "message": "Полетата username, email и password са задължителни"
        }), 400
    
    # Валидация на username
    valid, error_msg = is_valid_username(username)
    if not valid:
        return jsonify({"status": "error", "message": error_msg}), 400
    
    # Валидация на email
    if not is_valid_email(email):
        return jsonify({
            "status": "error",
            "message": "Невалиден email адрес"
        }), 400
    
    # Валидация на парола
    valid, error_msg = is_valid_password(password)
    if not valid:
        return jsonify({"status": "error", "message": error_msg}), 400
    
    # ----- Стъпка 3: Хеширане на паролата с bcrypt -----
    # bcrypt.gensalt() генерира случаен salt
    # bcrypt.hashpw() прави хеш от паролата + salt-а
    password_bytes = password.encode("utf-8")
    password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    
    # ----- Стъпка 4: Записване в базата данни -----
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        # Записваме потребителя; role е "user" по подразбиране
        insert_query = """
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, 'user')
        """
        cursor.execute(insert_query, (username, email, password_hash.decode("utf-8")))
        connection.commit()
        
        # Взимаме ID-то на новосъздадения потребител
        user_id = cursor.lastrowid
        
        cursor.close()
        connection.close()
        
    except IntegrityError as e:
        # IntegrityError се случва при нарушение на UNIQUE constraint
        # (username или email вече съществуват)
        error_str = str(e).lower()
        if "username" in error_str:
            return jsonify({
                "status": "error",
                "message": "Този username вече е зает"
            }), 409
        elif "email" in error_str:
            return jsonify({
                "status": "error",
                "message": "Този email вече е регистриран"
            }), 409
        else:
            return jsonify({
                "status": "error",
                "message": "Username или email вече съществуват"
            }), 409
            
    except Error as e:
        return jsonify({
            "status": "error",
            "message": "Грешка при записване в базата",
            "details": str(e)
        }), 500
    
    # ----- Стъпка 5: Създаване на JWT токен -----
    # identity е каквото искаме да "опаковаме" в токена
    # Тук слагаме user_id и role – ще ни трябват за authorization
    access_token = create_access_token(
        identity=str(user_id),
        additional_claims={"role": "user", "username": username}
    )
    
    # ----- Стъпка 6: Връщане на успешен отговор -----
    return jsonify({
        "status": "ok",
        "message": "Регистрацията е успешна",
        "user": {
            "id": user_id,
            "username": username,
            "email": email,
            "role": "user"
        },
        "access_token": access_token
    }), 201

# ============================================================
# Endpoint: POST /api/auth/login
# ============================================================
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Логва съществуващ потребител и връща JWT токен.
    
    Очаквано тяло на заявката (JSON):
    {
        "email": "petur@example.com",
        "password": "силна_парола_123"
    }
    
    Връща:
    - 200: Успешен login заедно с JWT токен
    - 400: Липсващи данни
    - 401: Грешен email или парола
    - 500: Сървърна грешка
    """
    # ----- Стъпка 1: Извличане на данните -----
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "Липсва JSON тяло на заявката"
        }), 400
    
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({
            "status": "error",
            "message": "Полетата email и password са задължителни"
        }), 400
    
    # ----- Стъпка 2: Намираме потребителя в базата -----
    try:
        connection = get_connection()
        # dictionary=True връща резултатите като dict вместо tuple
        # Така можем да достъпваме колоните по име: user["username"]
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute(
            "SELECT id, username, email, password_hash, role FROM users WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
    except Error as e:
        return jsonify({
            "status": "error",
            "message": "Грешка при достъп до базата",
            "details": str(e)
        }), 500
    
    # ----- Стъпка 3: Проверка дали потребителят съществува -----
    # ВАЖНО: Връщаме същото съобщение и за "няма такъв email", и за
    # "грешна парола". Това предотвратява username enumeration атаки –
    # хакер не може да разбере дали даден email е регистриран в системата.
    if user is None:
        return jsonify({
            "status": "error",
            "message": "Грешен email или парола"
        }), 401
    
    # ----- Стъпка 4: Сравняваме паролата с хеша -----
    # bcrypt.checkpw приема два байтови низа:
    # - изпратената парола (от потребителя)
    # - хеша от базата
    # Връща True ако съвпадат, False ако не
    password_bytes = password.encode("utf-8")
    stored_hash_bytes = user["password_hash"].encode("utf-8")
    
    if not bcrypt.checkpw(password_bytes, stored_hash_bytes):
        return jsonify({
            "status": "error",
            "message": "Грешен email или парола"
        }), 401
    
    # ----- Стъпка 5: Създаваме нов JWT токен -----
    access_token = create_access_token(
        identity=str(user["id"]),
        additional_claims={
            "role": user["role"],
            "username": user["username"]
        }
    )
    
    # ----- Стъпка 6: Връщаме успешен отговор -----
    return jsonify({
        "status": "ok",
        "message": "Успешен login",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        },
        "access_token": access_token
    }), 200

# ============================================================
# Endpoint: GET /api/auth/me
# Защитен endpoint – изисква валиден JWT токен
# ============================================================
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """
    Връща информация за текущия логнат потребител.
    
    Този endpoint е защитен – изисква валиден JWT токен в Authorization header:
    Authorization: Bearer <access_token>
    
    Връща:
    - 200: Информация за потребителя
    - 401: Липсва токен, изтекъл е, или е невалиден
    - 404: Потребителят от токена вече не съществува в базата
    - 500: Сървърна грешка
    
    Полезен за:
    - Проверка кой е логнат в момента (frontend стартова заявка)
    - Получаване на пресни данни за потребителя (име, role)
    - Валидация дали токенът все още работи
    """
    # ----- Стъпка 1: Извличаме user_id от токена -----
    # get_jwt_identity() връща стойността, която сложихме в create_access_token(identity=...)
    # При нас това беше str(user_id)
    user_id = get_jwt_identity()
    
    # ----- Стъпка 2: Извличаме допълнителните claims (role, username) -----
    # get_jwt() връща целия payload на токена
    claims = get_jwt()
    
    # ----- Стъпка 3: Взимаме пресни данни от базата -----
    # Защо не ползваме директно claims-овете?
    # Защото те са от момента на login-а. Ако междувременно потребителят
    # е променил username или role, базата има по-актуалните данни.
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
        return jsonify({
            "status": "error",
            "message": "Грешка при достъп до базата",
            "details": str(e)
        }), 500
    
    # ----- Стъпка 4: Проверка дали потребителят още съществува -----
    # Може да е изтрит междувременно, но токенът му все още да е валиден
    if user is None:
        return jsonify({
            "status": "error",
            "message": "Потребителят не съществува"
        }), 404
    
    # ----- Стъпка 5: Връщаме данните -----
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