"""
Blueprint за movies endpoints.

Този модул се грижи за филмите в системата:
- Списък на всички филми (GET /api/movies)
- Детайли за един филм (GET /api/movies/<id>) – ще добавим в следваща стъпка

Връзки в базата:
- movies <-> genres е many-to-many през movie_genres
- movies <-> actors е many-to-many през movie_actors
"""

from flask import Blueprint, jsonify
from mysql.connector import Error
from flask_jwt_extended import jwt_required, get_jwt

from database.connection import get_connection


# ============================================================
# Създаваме Blueprint с url_prefix
# ============================================================
# url_prefix="/api/movies" означава, че всички endpoint-и в този
# Blueprint автоматично започват с /api/movies/...
# Например: @movies_bp.route("") става /api/movies
#           @movies_bp.route("/<id>") става /api/movies/<id>
movies_bp = Blueprint("movies", __name__, url_prefix="/api/movies")


# ============================================================
# Endpoint: GET /api/movies
# ============================================================
@movies_bp.route("", methods=["GET"])
def get_all_movies():
    """
    Връща списък на всички филми от базата, заедно с техните жанрове.
    
    Не изисква authentication – филмите са публична информация.
    
    Връща:
    - 200: Списък с филми (може да е празен ако базата е празна)
    - 500: Сървърна грешка
    
    Пример отговор:
    {
        "status": "ok",
        "count": 17,
        "movies": [
            {
                "id": 1,
                "title": "The Godfather",
                "year": 1972,
                "director": "Francis Ford Coppola",
                "poster_url": "/img/posters/the-godfather.webp",
                "genres": ["Crime", "Drama"]
            },
            ...
        ]
    }
    """
    try:
        connection = get_connection()
        # dictionary=True връща резултатите като dict вместо tuple
        # Така можем да достъпваме колоните по име: row["title"]
        cursor = connection.cursor(dictionary=True)
        
        # ----- SQL заявка с GROUP_CONCAT за жанровете -----
        # 
        # Обяснение на заявката:
        # 1. Взимаме всички колони от movies (m.id, m.title, ...)
        # 2. LEFT JOIN с movie_genres – свързваща таблица за many-to-many
        # 3. LEFT JOIN с genres – за да вземем името на жанра
        # 4. GROUP_CONCAT събира всички жанрове на филма в един низ
        #    разделени със запетая: "Crime,Drama"
        # 5. GROUP BY m.id групира редовете по филм (иначе ще имаме
        #    отделен ред за всеки жанр)
        # 
        # Защо LEFT JOIN, а не INNER JOIN?
        # Ако филм няма зададени жанрове, LEFT JOIN ще го върне с 
        # genres = NULL. INNER JOIN би го пропуснал. По-безопасно е.
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
        return jsonify({
            "status": "error",
            "message": "Грешка при достъп до базата",
            "details": str(e)
        }), 500
    
    # ----- Обработваме резултатите -----
    # GROUP_CONCAT връща низ "Crime,Drama" – трябва да го разделим на масив
    # за да е по-удобно за frontend-а: ["Crime", "Drama"]
    movies = []
    for row in rows:
        # Ако филмът няма жанрове (NULL), връщаме празен масив
        genres_str = row["genres"]
        if genres_str:
            genres_list = genres_str.split(",")
        else:
            genres_list = []
        
        movies.append({
            "id": row["id"],
            "title": row["title"],
            "year": row["year"],
            "director": row["director"],
            "poster_url": row["poster_url"],
            "genres": genres_list
        })
    
    # ----- Връщаме отговор -----
    return jsonify({
        "status": "ok",
        "count": len(movies),
        "movies": movies
    }), 200



# ============================================================
# Endpoint: GET /api/movies/<id>
# ============================================================
# @jwt_required(optional=True) означава, че токенът Е по избор:
# - Ако потребителят НЕ е логнат → endpoint-ът работи нормално (публично)
# - Ако потребителят Е логнат → имаме достъп до claims-овете (role, username)
# Това ни позволява да върнем повече информация на admin потребители.
@movies_bp.route("/<int:movie_id>", methods=["GET"])
@jwt_required(optional=True)
def get_movie_by_id(movie_id):
    """
    Връща пълни детайли за един филм по неговото ID.
    
    URL параметри:
    - movie_id: ID на филма (integer)
    
    Authentication:
    - Не е задължително (публичен endpoint)
    - Ако е admin потребител, отговорът включва допълнителна 
      статистика (avg_true_sentiment)
    
    Връща:
    - 200: Детайли за филма (с жанрове, актьори и статистика)
    - 404: Филм с това ID не съществува
    - 500: Сървърна грешка
    """
    # ----- Проверка дали потребителят е admin -----
    # get_jwt() връща празен dict ако няма токен (заради optional=True)
    # Ако има токен, връща всички claims, които сме сложили при login/register
    claims = get_jwt()
    is_admin = claims.get("role") == "admin"
    
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        
        # ----- Заявка 1: Филмът + жанровете -----
        movie_query = """
            SELECT 
                m.id,
                m.title,
                m.year,
                m.director,
                m.poster_url,
                m.created_at,
                GROUP_CONCAT(g.name ORDER BY g.name SEPARATOR ',') AS genres
            FROM movies m
            LEFT JOIN movie_genres mg ON m.id = mg.movie_id
            LEFT JOIN genres g ON mg.genre_id = g.id
            WHERE m.id = %s
            GROUP BY m.id, m.title, m.year, m.director, m.poster_url, m.created_at
        """
        cursor.execute(movie_query, (movie_id,))
        movie_row = cursor.fetchone()
        
        # ----- Проверка дали филмът съществува -----
        if movie_row is None:
            cursor.close()
            connection.close()
            return jsonify({
                "status": "error",
                "message": f"Филм с ID {movie_id} не съществува"
            }), 404
        
        # ----- Заявка 2: Актьорите на филма -----
        actors_query = """
            SELECT a.name
            FROM actors a
            JOIN movie_actors ma ON a.id = ma.actor_id
            WHERE ma.movie_id = %s
            ORDER BY a.name
        """
        cursor.execute(actors_query, (movie_id,))
        actors_rows = cursor.fetchall()
        actors_list = [row["name"] for row in actors_rows]
        
        # ----- Заявка 3: Статистика за ревютата -----
        # Добавяме AVG за LSTM и BiLSTM predictions.
        # AVG автоматично игнорира NULL стойности – докато моделите не са
        # обучени, тези колони са NULL и AVG ще върне NULL.
        # След като admin натисне "Analyze", стойностите ще се пълнят.
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
        return jsonify({
            "status": "error",
            "message": "Грешка при достъп до базата",
            "details": str(e)
        }), 500
    
    # ----- Обработваме жанровете -----
    genres_str = movie_row["genres"]
    if genres_str:
        genres_list = genres_str.split(",")
    else:
        genres_list = []
    
    # ----- Помощна функция за обработка на AVG стойности -----
    # AVG връща Decimal обект, който JSON не може да сериализира.
    # Конвертираме във float и закръгляме до 2 знака.
    # Ако всички стойности са NULL, AVG връща None – пазим го като null.
    def format_avg(value):
        if value is None:
            return None
        return round(float(value), 2)
    
    # ----- Сглобяваме статистиката -----
    # avg_lstm_prediction и avg_bilstm_prediction се връщат винаги
    # (засега ще са null, защото моделите не са обучени).
    # avg_true_sentiment се връща САМО за admin потребители.
    stats = {
        "reviews_count": stats_row["reviews_count"],
        "avg_lstm_prediction": format_avg(stats_row["avg_lstm_prediction"]),
        "avg_bilstm_prediction": format_avg(stats_row["avg_bilstm_prediction"])
    }
    
    if is_admin:
        stats["avg_true_sentiment"] = format_avg(stats_row["avg_true_sentiment"])
    
    # ----- Сглобяваме отговора -----
    movie = {
        "id": movie_row["id"],
        "title": movie_row["title"],
        "year": movie_row["year"],
        "director": movie_row["director"],
        "poster_url": movie_row["poster_url"],
        "genres": genres_list,
        "actors": actors_list,
        "stats": stats,
        "created_at": movie_row["created_at"].isoformat() if movie_row["created_at"] else None
    }
    
    return jsonify({
        "status": "ok",
        "movie": movie
    }), 200