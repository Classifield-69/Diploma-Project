"""
Seed скрипт за филми
Етап 4: Цикъл за всичките 17 филма

Този скрипт извиква OpenAI за всеки филм от списъка и
записва данните в базата с правилна нормализация.
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import mysql.connector


# ============================================================
# 1. Списък с филмите за seed-ване
# ============================================================
# Всеки запис е tuple: (заглавие за OpenAI, име на файла за постер)
MOVIES = [
    ("Avengers: Endgame", "avengers-endgame.webp"),
    ("Braveheart", "braveheart.webp"),
    ("Joker (2019)", "joker-2019.webp"),
    ("Oppenheimer (2023)", "oppenheimer.webp"),
    ("Senna (2010 documentary)", "senna.webp"),
    ("The Conjuring", "the-conjuring.webp"),
    ("The Dark Knight", "the-dark-knight.webp"),
    ("The Devil Wears Prada 2", "the-devil-wears-prada-2.webp"),
    ("The Godfather", "the-godfather.webp"),
    ("The Lion King (1994)", "the-lion-king-1994.webp"),
    ("The Lord of the Rings: The Fellowship of the Ring", "the-lord-of-the-rings-the-fellowship-of-the-ring.webp"),
    ("The Lord of the Rings: The Return of the King", "the-lord-of-the-rings-the-return-of-the-king.webp"),
    ("The Lord of the Rings: The Two Towers", "the-lord-of-the-rings-the-two-towers.webp"),
    ("The Matrix", "the-matrix.webp"),
    ("The Terminator", "the-terminator.webp"),
    ("The Wolf of Wall Street", "the-wolf-of-wall-street.webp"),
    ("Top Gun (1986)", "top-gun.webp"),
]


# ============================================================
# 2. Зареждане на .env файла
# ============================================================
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"

if not env_path.exists():
    print(f"❌ ГРЕШКА: .env файлът не съществува!")
    exit(1)

load_dotenv(env_path)


# ============================================================
# 3. Инициализация на OpenAI клиента
# ============================================================
openai_key = os.getenv("OPENAI_API_KEY")

if not openai_key:
    print("❌ ГРЕШКА: OPENAI_API_KEY не е намерен!")
    exit(1)

client = OpenAI(api_key=openai_key)


# ============================================================
# 4. JSON схема за филма
# ============================================================
movie_schema = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Точното заглавие на филма на английски, без годината"
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
# 5. Функция за извикване на OpenAI
# ============================================================
def fetch_movie_metadata(movie_name: str) -> tuple[dict, int]:
    """
    Извиква OpenAI и връща метаданни за филма като Python dict.
    Връща (movie_data, total_tokens).
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
    
    movie_data = json.loads(response.choices[0].message.content)
    return movie_data, response.usage.total_tokens


# ============================================================
# 6. Функции за работа с базата данни
# ============================================================

def movie_exists(cursor, title: str, year: int) -> bool:
    """Проверява дали филмът вече съществува в базата."""
    cursor.execute(
        "SELECT id FROM movies WHERE title = %s AND year = %s",
        (title, year)
    )
    return cursor.fetchone() is not None


def get_or_create_movie(cursor, title: str, year: int, director: str, poster_url: str) -> tuple[int, bool]:
    """Връща (movie_id, created)."""
    cursor.execute(
        "SELECT id FROM movies WHERE title = %s AND year = %s",
        (title, year)
    )
    result = cursor.fetchone()
    
    if result:
        return result[0], False
    
    cursor.execute(
        "INSERT INTO movies (title, year, director, poster_url) VALUES (%s, %s, %s, %s)",
        (title, year, director, poster_url)
    )
    return cursor.lastrowid, True


def get_or_create_genre(cursor, name: str) -> tuple[int, bool]:
    """Връща (genre_id, created)."""
    cursor.execute("SELECT id FROM genres WHERE name = %s", (name,))
    result = cursor.fetchone()
    
    if result:
        return result[0], False
    
    cursor.execute("INSERT INTO genres (name) VALUES (%s)", (name,))
    return cursor.lastrowid, True


def get_or_create_actor(cursor, name: str) -> tuple[int, bool]:
    """Връща (actor_id, created)."""
    cursor.execute("SELECT id FROM actors WHERE name = %s", (name,))
    result = cursor.fetchone()
    
    if result:
        return result[0], False
    
    cursor.execute("INSERT INTO actors (name) VALUES (%s)", (name,))
    return cursor.lastrowid, True


def save_movie_to_db(conn, movie_data: dict, poster_filename: str) -> dict:
    """Записва филм в базата с всички връзки. Връща статистика."""
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
            genre_id, created = get_or_create_genre(cursor, genre_name)
            if created:
                stats["genres_created"] += 1
            cursor.execute(
                "INSERT IGNORE INTO movie_genres (movie_id, genre_id) VALUES (%s, %s)",
                (movie_id, genre_id)
            )
        
        # 3. Актьори
        for actor_name in movie_data["actors"]:
            actor_id, created = get_or_create_actor(cursor, actor_name)
            if created:
                stats["actors_created"] += 1
            cursor.execute(
                "INSERT IGNORE INTO movie_actors (movie_id, actor_id) VALUES (%s, %s)",
                (movie_id, actor_id)
            )
        
        conn.commit()
        return stats
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()


# ============================================================
# 7. Главна логика - цикъл през всички филми
# ============================================================
def main():
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
    }
    
    print("=" * 70)
    print(f"🎬 Seed скрипт - Етап 4: Зареждане на {len(MOVIES)} филма")
    print("=" * 70)
    
    # Свързване с базата
    conn = mysql.connector.connect(**db_config)
    
    # Глобална статистика
    total_stats = {
        "processed": 0,
        "movies_created": 0,
        "movies_skipped": 0,
        "movies_failed": 0,
        "genres_created": 0,
        "actors_created": 0,
        "total_tokens": 0,
        "total_cost": 0.0,
    }
    
    start_time = time.time()
    
    # Цикъл през всички филми
    for index, (movie_name, poster_filename) in enumerate(MOVIES, start=1):
        print(f"\n[{index}/{len(MOVIES)}] 🎬 {movie_name}")
        
        try:
            # Извикване на OpenAI
            print(f"   ⏳ Извиквам OpenAI...")
            movie_data, tokens_used = fetch_movie_metadata(movie_name)
            total_stats["total_tokens"] += tokens_used
            
            # Изчисляване на разхода
            cost = tokens_used * 0.150 / 1_000_000  # приблизително
            total_stats["total_cost"] += cost
            
            print(f"   📋 {movie_data['title']} ({movie_data['year']}) - {movie_data['director']}")
            
            # Записване в базата
            stats = save_movie_to_db(conn, movie_data, poster_filename)
            
            if stats["movie_created"]:
                total_stats["movies_created"] += 1
                print(f"   ✅ Записан в базата (нови: {stats['genres_created']} жанра, {stats['actors_created']} актьора)")
            else:
                total_stats["movies_skipped"] += 1
                print(f"   ℹ️  Вече съществуваше (пропуснат)")
            
            total_stats["genres_created"] += stats["genres_created"]
            total_stats["actors_created"] += stats["actors_created"]
            total_stats["processed"] += 1
            
        except Exception as e:
            total_stats["movies_failed"] += 1
            print(f"   ❌ ГРЕШКА: {e}")
            continue  # продължаваме със следващия филм
    
    # Затваряне на връзката
    conn.close()
    
    elapsed_time = time.time() - start_time
    
    # ============================================================
    # Финална статистика
    # ============================================================
    print("\n" + "=" * 70)
    print("📊 ФИНАЛНА СТАТИСТИКА")
    print("=" * 70)
    print(f"⏱️  Време за изпълнение: {elapsed_time:.1f} секунди")
    print(f"\n🎬 Филми:")
    print(f"   ✅ Създадени:    {total_stats['movies_created']}")
    print(f"   ℹ️  Пропуснати:   {total_stats['movies_skipped']} (вече съществуваха)")
    print(f"   ❌ Неуспешни:    {total_stats['movies_failed']}")
    print(f"\n📁 Нови записи в базата:")
    print(f"   🎭 Жанрове:  {total_stats['genres_created']}")
    print(f"   ⭐ Актьори:  {total_stats['actors_created']}")
    print(f"\n💰 OpenAI разход:")
    print(f"   📊 Tokens:   {total_stats['total_tokens']:,}")
    print(f"   💵 Цена:     ${total_stats['total_cost']:.4f}")
    
    # Финална проверка на базата
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM movies")
    total_movies = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM genres")
    total_genres = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM actors")
    total_actors = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    print(f"\n📈 Общо в базата:")
    print(f"   🎬 Филми:    {total_movies}")
    print(f"   🎭 Жанрове:  {total_genres}")
    print(f"   ⭐ Актьори:  {total_actors}")
    
    print("\n" + "=" * 70)
    print("🎉 Seed скриптът завърши!")
    print("=" * 70)


if __name__ == "__main__":
    main()