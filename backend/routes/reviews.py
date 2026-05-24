"""
Blueprint за reviews endpoints.

Този модул се грижи за ревютата в системата:
- Списък на ревюта за филм (GET /api/movies/<id>/reviews)
- Създаване на ново ревю (POST /api/reviews) – ще добавим следващо
- Изтриване на ревю (DELETE /api/reviews/<id>) – ще добавим следващо

Бележки за sentiment полетата:
- true_sentiment НЕ се връща на ниво ревю (вътрешна метрика за моделите)
- lstm_prediction и bilstm_prediction се връщат за всички (засега са NULL,
  ще се пълнят след като admin натисне "Analyze" и моделите се обучат)
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from mysql.connector import Error

from database.connection import get_connection


# ============================================================
# Създаваме Blueprint
# ============================================================
# ВАЖНО: НЕ слагаме url_prefix тук, защото endpoint-ите ще са на
# различни пътища:
# - GET /api/movies/<id>/reviews  (под /api/movies)
# - POST /api/reviews             (под /api/reviews)
# - DELETE /api/reviews/<id>      (под /api/reviews)
# Затова всеки endpoint ще си зададе целия път.
reviews_bp = Blueprint("reviews", __name__)


# ============================================================
# Endpoint: GET /api/movies/<id>/reviews
# ============================================================
@reviews_bp.route("/api/movies/<int:movie_id>/reviews", methods=["GET"])
def get_reviews_for_movie(movie_id):
    """
    Връща всички ревюта за конкретен филм.
    
    Не изисква authentication – ревютата са публична информация.
    
    URL параметри:
    - movie_id: ID на филма (integer)
    
    Връща:
    - 200: Списък с ревюта (може да е празен)
    - 404: Филм с това ID не съществува
    - 500: Сървърна грешка
    
    Пример отговор:
    {
        "status": "ok",
        "movie_id": 14,
        "count": 10,
        "reviews": [
            {
                "id": 87,
                "user": {
                    "id": 12,
                    "username": "ivan_petrov"
                },
                "text": "Невероятен филм...",
                "lstm_prediction": null,
                "bilstm_prediction": null,
                "created_at": "2026-05-23T11:35:22"
            },
            ...
        ]
    }
    """
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        # ----- Стъпка 1: Проверка дали филмът съществува -----
        # Това е важно, защото иначе frontend ще получи празен списък
        # и няма да знае дали филмът не съществува, или просто няма ревюта.
        # 404 vs 200 + празен списък е важно UX разграничение.
        cursor.execute("SELECT id FROM movies WHERE id = %s", (movie_id,))
        movie_exists = cursor.fetchone()
        
        if movie_exists is None:
            cursor.close()
            connection.close()
            return jsonify({
                "status": "error",
                "message": f"Филм с ID {movie_id} не съществува"
            }), 404
        
        # ----- Стъпка 2: Взимаме ревютата с info за автора -----
        # 
        # JOIN с users таблицата, за да вземем username-а на автора.
        # Не връщаме email или password_hash – само публична информация.
        # 
        # ВАЖНО: НЕ селектираме true_sentiment, защото не искаме да го
        # излагаме на frontend-а (вътрешна метрика).
        # 
        # ORDER BY r.created_at DESC – най-новите ревюта първи (стандартно).
        reviews_query = """
            SELECT 
                r.id,
                r.text,
                r.lstm_prediction,
                r.bilstm_prediction,
                r.created_at,
                u.id AS user_id,
                u.username
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            WHERE r.movie_id = %s
            ORDER BY r.created_at DESC
        """
        cursor.execute(reviews_query, (movie_id,))
        rows = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
    except Error as e:
        return jsonify({
            "status": "error",
            "message": "Грешка при достъп до базата",
            "details": str(e)
        }), 500
    
    # ----- Помощна функция за обработка на predictions -----
    # Същата логика като в movies.py – Decimal → float, NULL → null
    def format_prediction(value):
        if value is None:
            return None
        return round(float(value), 2)
    
    # ----- Сглобяваме отговора -----
    # Влагаме user info в nested обект, защото е по-чисто за frontend:
    # вместо review.user_id и review.username, имаме review.user.id и
    # review.user.username
    reviews = []
    for row in rows:
        reviews.append({
            "id": row["id"],
            "user": {
                "id": row["user_id"],
                "username": row["username"]
            },
            "text": row["text"],
            "lstm_prediction": format_prediction(row["lstm_prediction"]),
            "bilstm_prediction": format_prediction(row["bilstm_prediction"]),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None
        })
    
    return jsonify({
        "status": "ok",
        "movie_id": movie_id,
        "count": len(reviews),
        "reviews": reviews
    }), 200



# ============================================================
# Endpoint: POST /api/reviews
# ============================================================
@reviews_bp.route("/api/reviews", methods=["POST"])
@jwt_required()
def create_review():
    """
    Създава ново ревю за филм.
    
    Изисква валиден JWT токен в Authorization header:
    Authorization: Bearer <access_token>
    
    Очаквано тяло на заявката (JSON):
    {
        "movie_id": 14,
        "text": "Невероятен филм с дълбок сюжет..."
    }
    
    Връща:
    - 201: Успешно създадено ревю
    - 400: Невалидни данни (липсващи полета, грешна дължина)
    - 401: Липсва или невалиден JWT токен (от @jwt_required)
    - 404: Филм с подаденото movie_id не съществува
    - 500: Сървърна грешка
    
    Сигурност:
    - user_id идва от JWT токена, НЕ от body на заявката.
      Това предотвратява атаки от тип "представяне за друг потребител".
    - true_sentiment, lstm_prediction и bilstm_prediction се записват
      като NULL – те се пълнят само ръчно (seed) или от Analyze процеса.
    """
    # ----- Стъпка 1: Извличаме user_id от JWT токена -----
    # ВАЖНО: НИКОГА не вярваме на frontend-а за това кой потребител пише.
    # user_id ВИНАГИ идва от токена, който е подписан от сървъра.
    # Дори ако някой подмени body-то да съдържа user_id=999, ние го игнорираме.
    user_id = get_jwt_identity()
    
    # Взимаме username от claims-овете – ще го върнем в отговора,
    # за да не правим излишна заявка към базата
    claims = get_jwt()
    username = claims.get("username", "unknown")
    
    # ----- Стъпка 2: Извличаме и валидираме body-то -----
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "message": "Липсва JSON тяло на заявката"
        }), 400
    
    movie_id = data.get("movie_id")
    text = data.get("text", "").strip()  # strip() махва whitespace отпред/отзад
    
    # ----- Стъпка 3: Валидация на полетата -----
    if movie_id is None or not text:
        return jsonify({
            "status": "error",
            "message": "Полетата movie_id и text са задължителни"
        }), 400
    
    # Валидация че movie_id е цяло число
    # (frontend може да подаде string, JSON позволява всякакви типове)
    if not isinstance(movie_id, int):
        return jsonify({
            "status": "error",
            "message": "movie_id трябва да е цяло число"
        }), 400
    
    # Валидация на дължината на текста
    # Минимум 10 символа – предотвратява спам като "ок", "лош", "топ"
    # Максимум 5000 символа – разумно ограничение за дълги ревюта
    if len(text) < 10:
        return jsonify({
            "status": "error",
            "message": "Текстът трябва да е поне 10 символа"
        }), 400
    
    if len(text) > 5000:
        return jsonify({
            "status": "error",
            "message": "Текстът не може да надвишава 5000 символа"
        }), 400
    
    # ----- Стъпка 4: Записване в базата -----
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Първо проверяваме дали филмът съществува.
        # Алтернативата е да оставим foreign key constraint да гръмне,
        # но така ще върнем по-неясна грешка. По-добре е изричната проверка.
        cursor.execute("SELECT id FROM movies WHERE id = %s", (movie_id,))
        movie_exists = cursor.fetchone()
        
        if movie_exists is None:
            cursor.close()
            connection.close()
            return jsonify({
                "status": "error",
                "message": f"Филм с ID {movie_id} не съществува"
            }), 404
        
        # Записваме ревюто.
        # true_sentiment, lstm_prediction и bilstm_prediction НЕ ги задаваме
        # изрично – MySQL ще ги направи NULL по подразбиране (DEFAULT NULL).
        insert_query = """
            INSERT INTO reviews (user_id, movie_id, text)
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_query, (user_id, movie_id, text))
        connection.commit()
        
        # Взимаме ID и created_at на новосъздаденото ревю.
        # MySQL ни дава lastrowid, но created_at се пълни автоматично
        # с CURRENT_TIMESTAMP – трябва да го прочетем обратно.
        new_review_id = cursor.lastrowid
        
        cursor.execute(
            "SELECT id, created_at FROM reviews WHERE id = %s",
            (new_review_id,)
        )
        new_review = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
    except Error as e:
        return jsonify({
            "status": "error",
            "message": "Грешка при записване в базата",
            "details": str(e)
        }), 500
    
    # ----- Стъпка 5: Връщаме успешен отговор -----
    # Връщаме същата структура като GET endpoint-а – така frontend-ът
    # може директно да добави новото ревю към списъка без допълнителна заявка.
    return jsonify({
        "status": "ok",
        "message": "Ревюто е създадено успешно",
        "review": {
            "id": new_review["id"],
            "user": {
                "id": int(user_id),  # JWT identity е string, конвертираме
                "username": username
            },
            "movie_id": movie_id,
            "text": text,
            "lstm_prediction": None,
            "bilstm_prediction": None,
            "created_at": new_review["created_at"].isoformat()
        }
    }), 201



# ============================================================
# Endpoint: DELETE /api/reviews/<id>
# ============================================================
@reviews_bp.route("/api/reviews/<int:review_id>", methods=["DELETE"])
@jwt_required()
def delete_review(review_id):
    """
    Изтрива ревю по ID.
    
    Authorization логика:
    - Авторът на ревюто може да го изтрие
    - Admin потребителите могат да изтрият всяко ревю
    - Други потребители получават 403 Forbidden
    
    URL параметри:
    - review_id: ID на ревюто за изтриване (integer)
    
    Изисква валиден JWT токен в Authorization header:
    Authorization: Bearer <access_token>
    
    Връща:
    - 200: Успешно изтриване
    - 401: Липсва/невалиден JWT (от @jwt_required)
    - 403: Нямате право да изтриете това ревю
    - 404: Ревю с това ID не съществува
    - 500: Сървърна грешка
    """
    # ----- Стъпка 1: Извличаме данните от токена -----
    # user_id ще ни трябва за authorization проверката
    # role определя дали потребителят е admin
    current_user_id = int(get_jwt_identity())
    claims = get_jwt()
    is_admin = claims.get("role") == "admin"
    
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        # ----- Стъпка 2: Намираме ревюто и проверяваме собственика -----
        # Една заявка, която ни дава всичко нужно: 
        # - Дали ревюто съществува (ако fetchone() върне None → не съществува)
        # - Кой е авторът (user_id) – за authorization проверката
        cursor.execute(
            "SELECT id, user_id FROM reviews WHERE id = %s",
            (review_id,)
        )
        review = cursor.fetchone()
        
        # ----- Стъпка 3: Проверка дали ревюто съществува -----
        if review is None:
            cursor.close()
            connection.close()
            return jsonify({
                "status": "error",
                "message": f"Ревю с ID {review_id} не съществува"
            }), 404
        
        # ----- Стъпка 4: Authorization проверка -----
        # Авторът ИЛИ admin може да изтрива.
        # Всеки друг получава 403 Forbidden.
        is_author = review["user_id"] == current_user_id
        
        if not is_author and not is_admin:
            cursor.close()
            connection.close()
            return jsonify({
                "status": "error",
                "message": "Нямате право да изтриете това ревю"
            }), 403
        
        # ----- Стъпка 5: Изтриваме ревюто -----
        cursor.execute("DELETE FROM reviews WHERE id = %s", (review_id,))
        connection.commit()
        
        # rowcount ни казва колко реда са били засегнати.
        # Очакваме точно 1 (току-що проверихме че съществува).
        # Ако е 0, нещо много странно се е случило (race condition?).
        rows_affected = cursor.rowcount
        
        cursor.close()
        connection.close()
        
    except Error as e:
        return jsonify({
            "status": "error",
            "message": "Грешка при изтриване в базата",
            "details": str(e)
        }), 500
    
    # ----- Стъпка 6: Връщаме успешен отговор -----
    return jsonify({
        "status": "ok",
        "message": "Ревюто е изтрито успешно",
        "deleted_review_id": review_id,
        "rows_affected": rows_affected
    }), 200