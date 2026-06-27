# routes/movies.py — endpoints за филми.

from flask import Blueprint, jsonify
from mysql.connector import Error
from flask_jwt_extended import jwt_required, get_jwt

from database.connection import get_connection


movies_bp = Blueprint("movies", __name__, url_prefix="/api/movies")


# Endpoint: GET /api/movies
@movies_bp.route("", methods=["GET"])
def get_all_movies():
    """Връща всички филми с жанрове, сортирани по заглавие. (200 | 500)"""
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # GROUP_CONCAT събира жанровете в един низ "Crime,Drama"
        # LEFT JOIN — филми без жанрове се връщат с genres = NULL
        query = """
            SELECT
                m.id,
                m.title,
                m.year,
                m.director,
                m.poster_url,
                GROUP_CONCAT(g.name ORDER BY g.name SEPARATOR ',') AS genres
            FROM movies m
            LEFT JOIN movie_genres mg ON m.id = mg.movie_id
            LEFT JOIN genres g ON mg.genre_id = g.id
            GROUP BY m.id, m.title, m.year, m.director, m.poster_url
            ORDER BY m.title
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        cursor.close()
        connection.close()

    except Error as e:
        return jsonify({"status": "error", "message": "Грешка при достъп до базата", "details": str(e)}), 500

    movies = []
    for row in rows:
        genres_str = row["genres"]
        movies.append({
            "id":         row["id"],
            "title":      row["title"],
            "year":       row["year"],
            "director":   row["director"],
            "poster_url": row["poster_url"],
            "genres":     genres_str.split(",") if genres_str else []
        })

    return jsonify({"status": "ok", "count": len(movies), "movies": movies}), 200


# Endpoint: GET /api/movies/<id>
# optional=True — публичен endpoint, но admin получава avg_true_sentiment допълнително
@movies_bp.route("/<int:movie_id>", methods=["GET"])
@jwt_required(optional=True)
def get_movie_by_id(movie_id):
    """Връща пълни детайли за филм: жанрове, актьори и статистика. (200 | 404 | 500)"""
    claims   = get_jwt()
    is_admin = claims.get("role") == "admin"

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        movie_query = """
            SELECT
                m.id, m.title, m.year, m.director, m.poster_url, m.created_at,
                GROUP_CONCAT(g.name ORDER BY g.name SEPARATOR ',') AS genres
            FROM movies m
            LEFT JOIN movie_genres mg ON m.id = mg.movie_id
            LEFT JOIN genres g ON mg.genre_id = g.id
            WHERE m.id = %s
            GROUP BY m.id, m.title, m.year, m.director, m.poster_url, m.created_at
        """
        cursor.execute(movie_query, (movie_id,))
        movie_row = cursor.fetchone()

        if movie_row is None:
            cursor.close()
            connection.close()
            return jsonify({"status": "error", "message": f"Филм с ID {movie_id} не съществува"}), 404

        actors_query = """
            SELECT a.name FROM actors a
            JOIN movie_actors ma ON a.id = ma.actor_id
            WHERE ma.movie_id = %s
            ORDER BY a.name
        """
        cursor.execute(actors_query, (movie_id,))
        actors_list = [row["name"] for row in cursor.fetchall()]

        # AVG игнорира NULL автоматично — докато Analyze не се пусне, връща NULL
        stats_query = """
            SELECT
                COUNT(*) AS reviews_count,
                AVG(true_sentiment) AS avg_true_sentiment,
                AVG(lstm_prediction) AS avg_lstm_prediction,
                AVG(bilstm_prediction) AS avg_bilstm_prediction
            FROM reviews
            WHERE movie_id = %s
        """
        cursor.execute(stats_query, (movie_id,))
        stats_row = cursor.fetchone()

        cursor.close()
        connection.close()

    except Error as e:
        return jsonify({"status": "error", "message": "Грешка при достъп до базата", "details": str(e)}), 500

    genres_str = movie_row["genres"]

    def format_avg(value):
        """Decimal → float (2 знака); None → None."""
        return None if value is None else round(float(value), 2)

    stats = {
        "reviews_count":        stats_row["reviews_count"],
        "avg_lstm_prediction":  format_avg(stats_row["avg_lstm_prediction"]),
        "avg_bilstm_prediction": format_avg(stats_row["avg_bilstm_prediction"])
    }
    if is_admin:
        stats["avg_true_sentiment"] = format_avg(stats_row["avg_true_sentiment"])

    movie = {
        "id":         movie_row["id"],
        "title":      movie_row["title"],
        "year":       movie_row["year"],
        "director":   movie_row["director"],
        "poster_url": movie_row["poster_url"],
        "genres":     genres_str.split(",") if genres_str else [],
        "actors":     actors_list,
        "stats":      stats,
        "created_at": movie_row["created_at"].isoformat() if movie_row["created_at"] else None
    }

    return jsonify({"status": "ok", "movie": movie}), 200