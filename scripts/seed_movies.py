# seed_movies.py — зарежда 17 филма в базата чрез OpenAI (gpt-4o-mini).
# Извиква се еднократно след seed_users.py.

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import mysql.connector


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


project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"

if not env_path.exists():
    print("❌ ГРЕШКА: .env файлът не съществува!")
    exit(1)

load_dotenv(env_path)

openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    print("❌ ГРЕШКА: OPENAI_API_KEY не е намерен!")
    exit(1)

client = OpenAI(api_key=openai_key)

movie_schema = {
    "type": "object",
    "properties": {
        "title":    {"type": "string", "description": "Точното заглавие на английски, без годината"},
        "year":     {"type": "integer", "description": "Годината на издаване"},
        "director": {"type": "string", "description": "Името на режисьора"},
        "genres":   {"type": "array", "items": {"type": "string"}, "description": "Жанрове на английски"},
        "actors":   {"type": "array", "items": {"type": "string"}, "description": "Топ 5 главни актьора по важност"}
    },
    "required": ["title", "year", "director", "genres", "actors"],
    "additionalProperties": False
}


def fetch_movie_metadata(movie_name: str) -> tuple[dict, int]:
    """Извиква OpenAI и връща метаданни за филма. Връща (movie_data, total_tokens)."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a movie metadata expert. Provide accurate information in structured JSON. Always provide exactly 5 top actors per movie."},
            {"role": "user",   "content": f"Provide metadata for the movie '{movie_name}'."}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "movie_metadata", "schema": movie_schema, "strict": True}
        }
    )
    movie_data = json.loads(response.choices[0].message.content)
    return movie_data, response.usage.total_tokens


# ================================
# База данни
# ================================

def get_or_create_movie(cursor, title, year, director, poster_url) -> tuple[int, bool]:
    """Връща (movie_id, created)."""
    cursor.execute("SELECT id FROM movies WHERE title = %s AND year = %s", (title, year))
    result = cursor.fetchone()
    if result:
        return result[0], False
    cursor.execute(
        "INSERT INTO movies (title, year, director, poster_url) VALUES (%s, %s, %s, %s)",
        (title, year, director, poster_url)
    )
    return cursor.lastrowid, True


def get_or_create_genre(cursor, name) -> tuple[int, bool]:
    """Връща (genre_id, created)."""
    cursor.execute("SELECT id FROM genres WHERE name = %s", (name,))
    result = cursor.fetchone()
    if result:
        return result[0], False
    cursor.execute("INSERT INTO genres (name) VALUES (%s)", (name,))
    return cursor.lastrowid, True


def get_or_create_actor(cursor, name) -> tuple[int, bool]:
    """Връща (actor_id, created)."""
    cursor.execute("SELECT id FROM actors WHERE name = %s", (name,))
    result = cursor.fetchone()
    if result:
        return result[0], False
    cursor.execute("INSERT INTO actors (name) VALUES (%s)", (name,))
    return cursor.lastrowid, True


def save_movie_to_db(conn, movie_data: dict, poster_filename: str) -> dict:
    """Записва филм с жанрове и актьори. Връща статистика."""
    cursor = conn.cursor()
    poster_url = f"/img/posters/{poster_filename}"
    stats = {"movie_created": False, "genres_created": 0, "actors_created": 0}

    try:
        movie_id, was_created = get_or_create_movie(
            cursor, movie_data["title"], movie_data["year"], movie_data["director"], poster_url
        )
        stats["movie_created"] = was_created

        for genre_name in movie_data["genres"]:
            genre_id, created = get_or_create_genre(cursor, genre_name)
            if created:
                stats["genres_created"] += 1
            cursor.execute("INSERT IGNORE INTO movie_genres (movie_id, genre_id) VALUES (%s, %s)", (movie_id, genre_id))

        for actor_name in movie_data["actors"]:
            actor_id, created = get_or_create_actor(cursor, actor_name)
            if created:
                stats["actors_created"] += 1
            cursor.execute("INSERT IGNORE INTO movie_actors (movie_id, actor_id) VALUES (%s, %s)", (movie_id, actor_id))

        conn.commit()
        return stats

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()


# ================================
# Главна логика
# ================================

def main():
    db_config = {
        "host":     os.getenv("DB_HOST"),
        "port":     int(os.getenv("DB_PORT", 3306)),
        "user":     os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
    }

    print("=" * 70)
    print(f"🎬 Seed скрипт — зареждане на {len(MOVIES)} филма")
    print("=" * 70)

    conn = mysql.connector.connect(**db_config)

    total_stats = {
        "movies_created": 0, "movies_skipped": 0, "movies_failed": 0,
        "genres_created": 0, "actors_created": 0,
        "total_tokens": 0, "total_cost": 0.0,
    }

    start_time = time.time()

    for index, (movie_name, poster_filename) in enumerate(MOVIES, start=1):
        print(f"\n[{index}/{len(MOVIES)}] 🎬 {movie_name}")

        try:
            print("   ⏳ Извиквам OpenAI...")
            movie_data, tokens_used = fetch_movie_metadata(movie_name)
            total_stats["total_tokens"] += tokens_used
            total_stats["total_cost"]   += tokens_used * 0.150 / 1_000_000

            print(f"   📋 {movie_data['title']} ({movie_data['year']}) - {movie_data['director']}")

            stats = save_movie_to_db(conn, movie_data, poster_filename)

            if stats["movie_created"]:
                total_stats["movies_created"] += 1
                print(f"   ✅ Записан (нови: {stats['genres_created']} жанра, {stats['actors_created']} актьора)")
            else:
                total_stats["movies_skipped"] += 1
                print("   ℹ️  Вече съществуваше (пропуснат)")

            total_stats["genres_created"] += stats["genres_created"]
            total_stats["actors_created"] += stats["actors_created"]

        except Exception as e:
            total_stats["movies_failed"] += 1
            print(f"   ❌ ГРЕШКА: {e}")

    conn.close()
    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("📊 ФИНАЛНА СТАТИСТИКА")
    print("=" * 70)
    print(f"⏱️  Време: {elapsed:.1f} сек")
    print(f"🎬 Създадени: {total_stats['movies_created']} | Пропуснати: {total_stats['movies_skipped']} | Неуспешни: {total_stats['movies_failed']}")
    print(f"🎭 Нови жанрове: {total_stats['genres_created']} | ⭐ Нови актьори: {total_stats['actors_created']}")
    print(f"💰 Tokens: {total_stats['total_tokens']:,} | Цена: ${total_stats['total_cost']:.4f}")

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM movies")
    print(f"\n📈 Общо в базата: {cursor.fetchone()[0]} филма", end="")
    cursor.execute("SELECT COUNT(*) FROM genres")
    print(f", {cursor.fetchone()[0]} жанра", end="")
    cursor.execute("SELECT COUNT(*) FROM actors")
    print(f", {cursor.fetchone()[0]} актьора")
    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("🎉 Готово!")
    print("=" * 70)


if __name__ == "__main__":
    main()