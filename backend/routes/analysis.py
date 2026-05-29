"""
Blueprint за ML анализ на ревюта.

Този модул се грижи за:
- Анализ на ревюта с LSTM и BiLSTM модели (POST /api/movies/<id>/analyze)

Endpoint-ът е admin-only — само администратори могат да тригерират ML анализ.
Това предпазва системата от:
- Случайно/злоумишлено натоварване на сървъра (TF inference е скъп)
- Презапис на съществуващи предсказания от обикновени потребители

Стратегия на анализа:
- Анализират се САМО ревюта, при които поне една от колоните
  lstm_prediction или bilstm_prediction е NULL
- Старите ревюта със вече попълнени оценки НЕ се преанализират
- Двата модела се пускат заедно в един batch (по-ефикасно)
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from mysql.connector import Error

from database.connection import get_connection
from routes.auth import admin_required
from ml.inference import predict


# ============================================================
# Blueprint
# ============================================================
analysis_bp = Blueprint("analysis", __name__, url_prefix="/api")


# ============================================================
# Endpoint: POST /api/movies/<movie_id>/analyze
# ============================================================
@analysis_bp.route("/movies/<int:movie_id>/analyze", methods=["POST"])
@jwt_required()
@admin_required
def analyze_movie_reviews(movie_id):
    """
    Пуска ML анализ върху ревютата на даден филм.

    Анализира САМО ревютата, при които lstm_prediction ИЛИ bilstm_prediction
    е NULL. Ревюта с вече попълнени и двете оценки се пропускат — резултатите
    биха били почти същите, така че няма смисъл да тормозим моделите.

    Защитен endpoint:
    - Изисква валиден JWT (@jwt_required)
    - Изисква role = 'admin' (@admin_required)

    Връща:
    - 200: Успешен анализ, със статистика колко са анализирани
    - 401: Липсва или невалиден JWT
    - 403: User не е admin
    - 404: Филмът не съществува
    - 500: Сървърна грешка (база, модели и т.н.)
    """
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # ----- Стъпка 1: Проверяваме че филмът съществува -----
        cursor.execute("SELECT id, title FROM movies WHERE id = %s", (movie_id,))
        movie = cursor.fetchone()

        if movie is None:
            return jsonify({
                "status": "error",
                "message": f"Филм с id={movie_id} не съществува"
            }), 404

        # ----- Стъпка 2: Общ брой ревюта на филма (за статистика) -----
        cursor.execute(
            "SELECT COUNT(*) AS total FROM reviews WHERE movie_id = %s",
            (movie_id,)
        )
        total_reviews = cursor.fetchone()["total"]

        # ----- Стъпка 3: Намираме само неанализираните ревюта -----
        # Условието: поне една от двете predict колони е NULL
        cursor.execute(
            """
            SELECT id, text
            FROM reviews
            WHERE movie_id = %s
              AND (lstm_prediction IS NULL OR bilstm_prediction IS NULL)
            """,
            (movie_id,)
        )
        unanalyzed = cursor.fetchall()

        # ----- Стъпка 4: Ако няма какво за анализ, излизаме рано -----
        if not unanalyzed:
            cursor.close()
            connection.close()
            return jsonify({
                "status": "ok",
                "message": "Всички ревюта вече са анализирани",
                "movie_id": movie_id,
                "movie_title": movie["title"],
                "total_reviews": total_reviews,
                "analyzed_count": 0,
                "newly_analyzed_count": 0
            }), 200

        # ----- Стъпка 5: Batch ML предсказание -----
        # Извличаме само текстовете и id-тата в отделни списъци
        review_ids = [r["id"] for r in unanalyzed]
        review_texts = [r["text"] for r in unanalyzed]

        # ВАЖНО: При първи predict() след startup на сървъра, тук ще има
        # ~5-10 сек забавяне (зареждане на TF + двата .keras файла).
        # Следващи извиквания са бързи.
        predictions = predict(review_texts)

        # ----- Стъпка 6: UPDATE на базата с резултатите -----
        # executemany е по-ефикасно от цикъл с execute() — една заявка с N стойности
        update_query = """
            UPDATE reviews
            SET lstm_prediction = %s, bilstm_prediction = %s
            WHERE id = %s
        """
        update_params = [
            (pred["lstm_rating"], pred["bilstm_rating"], rid)
            for rid, pred in zip(review_ids, predictions)
        ]

        # Trябва нов cursor без dictionary=True за UPDATE-и
        cursor.close()
        cursor = connection.cursor()
        cursor.executemany(update_query, update_params)
        connection.commit()

        newly_analyzed = cursor.rowcount  # колко реда са обновени

        cursor.close()
        connection.close()

        # ----- Стъпка 7: Връщаме статистика -----
        return jsonify({
            "status": "ok",
            "message": f"Анализирани са {newly_analyzed} ревюта",
            "movie_id": movie_id,
            "movie_title": movie["title"],
            "total_reviews": total_reviews,
            "newly_analyzed_count": newly_analyzed
        }), 200

    except Error as e:
        # MySQL грешка
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        return jsonify({
            "status": "error",
            "message": "Грешка при достъп до базата",
            "details": str(e)
        }), 500

    except Exception as e:
        # ML или друга неочаквана грешка
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        return jsonify({
            "status": "error",
            "message": "Грешка при ML анализ",
            "details": str(e)
        }), 500
