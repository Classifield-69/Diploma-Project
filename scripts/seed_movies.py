"""
Seed скрипт за филми
Етап 3: Записване на един филм в базата

Този скрипт извиква OpenAI за един филм ("The Godfather"),
после записва данните в базата с правилна нормализация
и избягване на дубликати.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import mysql.connector


# ============================================================
# 1. Зареждане на .env файла
# ============================================================
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"

if not env_path.exists():
    print(f"❌ ГРЕШКА: .env файлът не съществува!")
    exit(1)

load_dotenv(env_path)


# ============================================================
# 2. Инициализация на OpenAI клиента
# ============================================================
openai_key = os.getenv("OPENAI_API_KEY")

if not openai_key:
    print("❌ ГРЕШКА: OPENAI_API_KEY не е намерен!")
    exit(1)

client = OpenAI(api_key=openai_key)


# ============================================================
# 3. JSON схема за филма (както в Етап 2)
# ============================================================
movie_schema = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Точното заглавие на филма на английски"
        },
        "year": {
            "type": "integer",
            "description": "Годината на издаване на филма"
        },
        "director": {
            "type": "string",
            "description": "Името на режисьора на филма"
        },
        "genres": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Списък с жанрове на английски (например Drama, Action, Sci-Fi)"
        },
        "actors": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Топ 5 главни актьори, подредени по важност в ролите"
        }
    },
    "required": ["title", "year", "director", "genres", "actors"],
    "additionalProperties": False
}


# ============================================================
# 4. Функция за извикване на OpenAI
# ============================================================
def fetch_movie_metadata(movie_name: str) -> dict:
    """
    Извиква OpenAI и връща метаданни за филма като Python dict.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a movie metadata expert. You provide accurate "
                    "information about movies in structured JSON format. "
                    "Always provide exactly 5 top actors per movie."
                )
            },
            {
                "role": "user",
                "content": f"Provide metadata for the movie '{movie_name}'."
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "movie_metadata",
                "schema": movie_schema,
                "strict": True
            }
        }
    )
    
    return json.loads(response.choices[0].message.content)


# ============================================================
# 5. Функции за работа с базата данни
# ============================================================

def get_or_create_movie(cursor, title: str, year: int, director: str, poster_url: str) -> tuple[int, bool]:
    """
    Проверява дали филмът вече съществува.
    Връща (movie_id, created), където created е True ако е създаден сега.
    """
    cursor.execute(
        "SELECT id FROM movies WHERE title = %s AND year = %s",
        (title, year)
    )
    result = cursor.fetchone()
    
    if result:
        # Филмът вече съществува
        return result[0], False
    
    # Създаваме нов филм
    cursor.execute(
        "INSERT INTO movies (title, year, director, poster_url) VALUES (%s, %s, %s, %s)",
        (title, year, director, poster_url)
    )
    return cursor.lastrowid, True


def get_or_create_genre(cursor, name: str) -> int:
    """
    Проверява дали жанрът съществува. Ако не - създава го.
    Връща id-то.
    """
    cursor.execute("SELECT id FROM genres WHERE name = %s", (name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    cursor.execute("INSERT INTO genres (name) VALUES (%s)", (name,))
    return cursor.lastrowid


def get_or_create_actor(cursor, name: str) -> int:
    """
    Проверява дали актьорът съществува. Ако не - създава го.
    Връща id-то.
    """
    cursor.execute("SELECT id FROM actors WHERE name = %s", (name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    cursor.execute("INSERT INTO actors (name) VALUES (%s)", (name,))
    return cursor.lastrowid


def link_movie_genre(cursor, movie_id: int, genre_id: int) -> None:
    """
    Свързва филм с жанр в movie_genres таблицата.
    INSERT IGNORE се справя с потенциални дубликати в join таблицата.
    """
    cursor.execute(
        "INSERT IGNORE INTO movie_genres (movie_id, genre_id) VALUES (%s, %s)",
        (movie_id, genre_id)
    )


def link_movie_actor(cursor, movie_id: int, actor_id: int) -> None:
    """
    Свързва филм с актьор в movie_actors таблицата.
    """
    cursor.execute(
        "INSERT IGNORE INTO movie_actors (movie_id, actor_id) VALUES (%s, %s)",
        (movie_id, actor_id)
    )


def save_movie_to_db(conn, movie_data: dict, poster_filename: str) -> dict:
    """
    Записва филм в базата с всички връзки. Всичко в една транзакция.
    Връща статистика за това какво е създадено.
    """
    cursor = conn.cursor()
    poster_url = f"/img/posters/{poster_filename}"
    
    stats = {
        "movie_created": False,
        "genres_created": 0,
        "actors_created": 0,
    }
    
    try:
        # 1. Филм
        movie_id, was_created = get_or_create_movie(
            cursor,
            movie_data["title"],
            movie_data["year"],
            movie_data["director"],
            poster_url
        )
        stats["movie_created"] = was_created
        
        # 2. Жанрове
        for genre_name in movie_data["genres"]:
            # Проверка дали жанрът съществуваше преди
            cursor.execute("SELECT id FROM genres WHERE name = %s", (genre_name,))
            existed = cursor.fetchone() is not None
            
            genre_id = get_or_create_genre(cursor, genre_name)
            link_movie_genre(cursor, movie_id, genre_id)
            
            if not existed:
                stats["genres_created"] += 1
        
        # 3. Актьори
        for actor_name in movie_data["actors"]:
            cursor.execute("SELECT id FROM actors WHERE name = %s", (actor_name,))
            existed = cursor.fetchone() is not None
            
            actor_id = get_or_create_actor(cursor, actor_name)
            link_movie_actor(cursor, movie_id, actor_id)
            
            if not existed:
                stats["actors_created"] += 1
        
        # Ако стигнахме дотук - всичко е ОК, commit
        conn.commit()
        return stats
        
    except Exception as e:
        # При грешка - rollback
        conn.rollback()
        raise e
    finally:
        cursor.close()


# ============================================================
# 6. Главна логика
# ============================================================
def main():
    # Връзка с базата
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
    }
    
    print("=" * 60)
    print("🎬 Seed скрипт - Етап 3: Записване на един филм")
    print("=" * 60)
    
    # Тестов филм
    movie_name = "The Godfather"
    poster_filename = "the-godfather.webp"
    
    # 1. Извикваме OpenAI
    print(f"\n⏳ Извиквам OpenAI за: {movie_name}")
    movie_data = fetch_movie_metadata(movie_name)
    print(f"✅ Получени данни за: {movie_data['title']} ({movie_data['year']})")
    
    # 2. Свързваме се с базата
    print(f"\n🔌 Свързване с базата...")
    conn = mysql.connector.connect(**db_config)
    print(f"✅ Връзка установена")
    
    try:
        # 3. Записваме филма
        print(f"\n💾 Записване в базата...")
        stats = save_movie_to_db(conn, movie_data, poster_filename)
        
        # 4. Показваме резултата
        print("\n" + "=" * 60)
        print("📊 Резултат:")
        print("=" * 60)
        
        if stats["movie_created"]:
            print(f"✅ Филм създаден: {movie_data['title']}")
        else:
            print(f"ℹ️  Филмът вече съществуваше: {movie_data['title']}")
        
        print(f"📁 Нови жанрове:  {stats['genres_created']} / {len(movie_data['genres'])}")
        print(f"⭐ Нови актьори:  {stats['actors_created']} / {len(movie_data['actors'])}")
        
        # 5. Показваме общата статистика на базата
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM movies")
        total_movies = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM genres")
        total_genres = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM actors")
        total_actors = cursor.fetchone()[0]
        cursor.close()
        
        print(f"\n📈 Общо в базата:")
        print(f"   🎬 Филми:    {total_movies}")
        print(f"   🎭 Жанрове:  {total_genres}")
        print(f"   ⭐ Актьори:  {total_actors}")
        
    finally:
        conn.close()
    
    print("\n" + "=" * 60)
    print("🎉 Етап 3 завърши успешно!")
    print("=" * 60)


if __name__ == "__main__":
    main()