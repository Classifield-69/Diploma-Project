# routes/reviews.py — endpoints за ревюта.
# true_sentiment не се връща на frontend-а — вътрешна метрика за моделите.

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from mysql.connector import Error

from database.connection import get_connection


# Без url_prefix — endpoint-ите са на различни пътища (/api/movies/... и /api/reviews/...)
reviews_bp = Blueprint("reviews", __name__)


# Endpoint: GET /api/movies/<id>/reviews
@reviews_bp.route("/api/movies/<int:movie_id>/reviews", methods=["GET"])
def get_reviews_for_movie(movie_id):
    """Връща всички ревюта за филм, сортирани по дата (най-ново първо). (200 | 404 | 500)"""
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id FROM movies WHERE id = %s", (movie_id,))
        if cursor.fetchone() is None:
            cursor.close()
            connection.close()
            return jsonify({"status": "error", "message": f"Филм с ID {movie_id} не съществува"}), 404

        # true_sentiment не се селектира — не се излага на frontend-а
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
        return jsonify({"status": "error", "message": "Грешка при достъп до базата", "details": str(e)}), 500

    def format_prediction(value):
        """Decimal → float; NULL → None."""
        return None if value is None else round(float(value), 2)

    reviews = []
    for row in rows:
        reviews.append({
            "id": row["id"],
            "user": {"id": row["user_id"], "username": row["username"]},
            "text": row["text"],
            "lstm_prediction": format_prediction(row["lstm_prediction"]),
            "bilstm_prediction": format_prediction(row["bilstm_prediction"]),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None
        })

    return jsonify({"status": "ok", "movie_id": movie_id, "count": len(reviews), "reviews": reviews}), 200


# Endpoint: POST /api/reviews
@reviews_bp.route("/api/reviews", methods=["POST"])
@jwt_required()
def create_review():
    """
    Създава ново ревю за филм. (201 | 400 | 401 | 404 | 500)

    user_id идва от JWT токена, НЕ от body — предотвратява представяне за друг потребител.
    """
    user_id  = get_jwt_identity()
    claims   = get_jwt()
    username = claims.get("username", "unknown")

    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Липсва JSON тяло на заявката"}), 400

    movie_id = data.get("movie_id")
    text     = data.get("text", "").strip()

    if movie_id is None or not text:
        return jsonify({"status": "error", "message": "Полетата movie_id и text са задължителни"}), 400

    if not isinstance(movie_id, int):
        return jsonify({"status": "error", "message": "movie_id трябва да е цяло число"}), 400

    if len(text) < 10:
        return jsonify({"status": "error", "message": "Текстът трябва да е поне 10 символа"}), 400

    if len(text) > 5000:
        return jsonify({"status": "error", "message": "Текстът не може да надвишава 5000 символа"}), 400

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id FROM movies WHERE id = %s", (movie_id,))
        if cursor.fetchone() is None:
            cursor.close()
            connection.close()
            return jsonify({"status": "error", "message": f"Филм с ID {movie_id} не съществува"}), 404

        # true_sentiment, lstm_prediction и bilstm_prediction остават NULL по подразбиране
        cursor.execute(
            "INSERT INTO reviews (user_id, movie_id, text) VALUES (%s, %s, %s)",
            (user_id, movie_id, text)
        )
        connection.commit()
        new_review_id = cursor.lastrowid

        # Четем created_at обратно — пълни се автоматично с CURRENT_TIMESTAMP
        cursor.execute("SELECT id, created_at FROM reviews WHERE id = %s", (new_review_id,))
        new_review = cursor.fetchone()

        cursor.close()
        connection.close()

    except Error as e:
        return jsonify({"status": "error", "message": "Грешка при записване в базата", "details": str(e)}), 500

    return jsonify({
        "status": "ok",
        "message": "Ревюто е създадено успешно",
        "review": {
            "id": new_review["id"],
            "user": {"id": int(user_id), "username": username},
            "movie_id": movie_id,
            "text": text,
            "lstm_prediction": None,
            "bilstm_prediction": None,
            "created_at": new_review["created_at"].isoformat()
        }
    }), 201


# Endpoint: DELETE /api/reviews/<id>
@reviews_bp.route("/api/reviews/<int:review_id>", methods=["DELETE"])
@jwt_required()
def delete_review(review_id):
    """
    Изтрива ревю по ID. (200 | 401 | 403 | 404 | 500)

    Авторът или admin може да изтрива. Всеки друг получава 403.
    """
    current_user_id = int(get_jwt_identity())
    claims   = get_jwt()
    is_admin = claims.get("role") == "admin"

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, user_id FROM reviews WHERE id = %s", (review_id,))
        review = cursor.fetchone()

        if review is None:
            cursor.close()
            connection.close()
            return jsonify({"status": "error", "message": f"Ревю с ID {review_id} не съществува"}), 404

        is_author = review["user_id"] == current_user_id
        if not is_author and not is_admin:
            cursor.close()
            connection.close()
            return jsonify({"status": "error", "message": "Нямате право да изтриете това ревю"}), 403

        cursor.execute("DELETE FROM reviews WHERE id = %s", (review_id,))
        connection.commit()
        rows_affected = cursor.rowcount

        cursor.close()
        connection.close()

    except Error as e:
        return jsonify({"status": "error", "message": "Грешка при изтриване в базата", "details": str(e)}), 500

    return jsonify({
        "status": "ok",
        "message": "Ревюто е изтрито успешно",
        "deleted_review_id": review_id,
        "rows_affected": rows_affected
    }), 200