# routes/analysis.py — ML анализ на ревюта (admin-only).
# Анализират се само ревюта с NULL предсказания — съществуващите не се презаписват.

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from mysql.connector import Error

from database.connection import get_connection
from routes.auth import admin_required
from ml.inference import predict


analysis_bp = Blueprint("analysis", __name__, url_prefix="/api")


# Endpoint: POST /api/movies/<id>/analyze
@analysis_bp.route("/movies/<int:movie_id>/analyze", methods=["POST"])
@jwt_required()
@admin_required
def analyze_movie_reviews(movie_id):
    """
    Пуска ML анализ върху неанализираните ревюта на филм. (200 | 401 | 403 | 404 | 500)

    При първо извикване след startup на сървъра има ~5–10 сек забавяне
    заради зареждане на TensorFlow моделите.
    """
    connection = None
    cursor     = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, title FROM movies WHERE id = %s", (movie_id,))
        movie = cursor.fetchone()

        if movie is None:
            return jsonify({"status": "error", "message": f"Филм с id={movie_id} не съществува"}), 404

        cursor.execute("SELECT COUNT(*) AS total FROM reviews WHERE movie_id = %s", (movie_id,))
        total_reviews = cursor.fetchone()["total"]

        # Само ревюта с поне една NULL колона
        cursor.execute(
            """
            SELECT id, text FROM reviews
            WHERE movie_id = %s
              AND (lstm_prediction IS NULL OR bilstm_prediction IS NULL)
            """,
            (movie_id,)
        )
        unanalyzed = cursor.fetchall()

        if not unanalyzed:
            cursor.close()
            connection.close()
            return jsonify({
                "status": "ok",
                "message": "Всички ревюта вече са анализирани",
                "movie_id": movie_id,
                "movie_title": movie["title"],
                "total_reviews": total_reviews,
                "newly_analyzed_count": 0
            }), 200

        review_ids   = [r["id"] for r in unanalyzed]
        review_texts = [r["text"] for r in unanalyzed]

        predictions = predict(review_texts)

        update_query = """
            UPDATE reviews
            SET lstm_prediction = %s, bilstm_prediction = %s
            WHERE id = %s
        """
        update_params = [
            (pred["lstm_rating"], pred["bilstm_rating"], rid)
            for rid, pred in zip(review_ids, predictions)
        ]

        cursor.close()
        cursor = connection.cursor()
        cursor.executemany(update_query, update_params)
        connection.commit()

        newly_analyzed = cursor.rowcount

        cursor.close()
        connection.close()

        return jsonify({
            "status": "ok",
            "message": f"Анализирани са {newly_analyzed} ревюта",
            "movie_id": movie_id,
            "movie_title": movie["title"],
            "total_reviews": total_reviews,
            "newly_analyzed_count": newly_analyzed
        }), 200

    except Error as e:
        if cursor: cursor.close()
        if connection: connection.close()
        return jsonify({"status": "error", "message": "Грешка при достъп до базата", "details": str(e)}), 500

    except Exception as e:
        if cursor: cursor.close()
        if connection: connection.close()
        return jsonify({"status": "error", "message": "Грешка при ML анализ", "details": str(e)}), 500