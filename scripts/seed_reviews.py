# seed_reviews.py — генерира 171 ревюта чрез OpenAI (1 admin + 170 потребителски).
# Sentiment: 45% позитивни, 30% негативни, 25% неутрални.
# Стилове: formal, informal, casual_with_typos, short_and_punchy.
# Дължина: 50–100, 100–250 или 250–500 думи (случайно).

import os
import json
import random
import time
import mysql.connector
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

REVIEWS_PER_MOVIE = 10

SENTIMENT_WEIGHTS = {"positive": 0.45, "negative": 0.30, "neutral": 0.25}
SENTIMENT_RANGES  = {"positive": (70, 100), "negative": (0, 30), "neutral": (40, 60)}
STYLES            = ["formal", "informal", "casual_with_typos", "short_and_punchy"]
LENGTH_OPTIONS    = [
    {"name": "кратко", "words": (50, 100)},
    {"name": "средно",  "words": (100, 250)},
    {"name": "дълго",   "words": (250, 500)},
]

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def fetch_movies(cursor) -> list[dict]:
    cursor.execute("SELECT id, title, year, director FROM movies ORDER BY id")
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetch_users(cursor) -> dict:
    """Връща {"admin": [...], "users": [...]}."""
    cursor.execute("SELECT id, username, role FROM users ORDER BY id")
    columns = [desc[0] for desc in cursor.description]
    all_users = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return {
        "admin": [u for u in all_users if u["role"] == "admin"],
        "users": [u for u in all_users if u["role"] == "user"],
    }


def choose_sentiment_category() -> str:
    rand = random.random()
    if rand < SENTIMENT_WEIGHTS["positive"]:
        return "positive"
    elif rand < SENTIMENT_WEIGHTS["positive"] + SENTIMENT_WEIGHTS["negative"]:
        return "negative"
    return "neutral"


def build_prompt(movie: dict, sentiment_category: str, style: str, length: dict) -> str:
    sentiment_descriptions = {
        "positive": "ПОЗИТИВНО (харесал си филма, препоръчваш го)",
        "negative": "НЕГАТИВНО (не си харесал филма, критикуваш го)",
        "neutral":  "НЕУТРАЛНО (смесени чувства)",
    }
    style_descriptions = {
        "formal":            "формален език, като професионален критик",
        "informal":          "неформален разговорен стил",
        "casual_with_typos": "небрежен стил с няколко правописни грешки",
        "short_and_punchy":  "кратък и директен, без излишни думи",
    }
    sentiment_range = SENTIMENT_RANGES[sentiment_category]
    min_words, max_words = length["words"]

    return f"""Напиши ревю на български за филма "{movie['title']}" ({movie['year']}), режисьор {movie['director']}.

Изисквания:
- Sentiment: {sentiment_descriptions[sentiment_category]}
- Стил: {style_descriptions[style]}
- Дължина: между {min_words} и {max_words} думи
- Звучи като реален човек

Върни САМО валиден JSON:
{{
  "text": "тук е текстът...",
  "true_sentiment": число между {sentiment_range[0]} и {sentiment_range[1]}
}}"""


def generate_review(movie: dict, sentiment_category: str) -> dict:
    """Генерира едно ревю с OpenAI. Връща {text, true_sentiment}."""
    style  = random.choice(STYLES)
    length = random.choice(LENGTH_OPTIONS)
    prompt = build_prompt(movie, sentiment_category, style, length)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Генерираш реалистични български филмови ревюта. Връщаш САМО валиден JSON."},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.9,
        response_format={"type": "json_object"},
    )

    parsed = json.loads(response.choices[0].message.content)

    if "text" not in parsed or "true_sentiment" not in parsed:
        raise ValueError(f"Неочакван формат: {parsed}")

    parsed["true_sentiment"] = float(parsed["true_sentiment"])
    parsed["true_sentiment"] = max(0.0, min(100.0, parsed["true_sentiment"]))
    return parsed


def insert_review(cursor, user_id: int, movie_id: int, text: str, true_sentiment: float):
    cursor.execute(
        "INSERT INTO reviews (user_id, movie_id, text, true_sentiment, lstm_prediction, bilstm_prediction) VALUES (%s, %s, %s, %s, NULL, NULL)",
        (user_id, movie_id, text, true_sentiment)
    )


def seed_reviews():
    print("🔌 Свързвам се с MySQL...")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM reviews")
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            print(f"⚠️  Таблицата reviews вече съдържа {existing_count} реда.")
            answer = input("Искаш ли да изтриеш съществуващите ревюта? (y/n): ")
            if answer.lower() == "y":
                cursor.execute("DELETE FROM reviews")
                cursor.execute("ALTER TABLE reviews AUTO_INCREMENT = 1")
                conn.commit()
                print("🗑️  Изтрити всички ревюта")
            else:
                print("❌ Прекъсвам.")
                return

        print("\n📚 Извличам филми и потребители...")
        movies = fetch_movies(cursor)
        if not movies:
            print("❌ Няма филми! Първо пусни seed_movies.py")
            return

        users_by_role  = fetch_users(cursor)
        admins         = users_by_role["admin"]
        regular_users  = users_by_role["users"]
        print(f"   ✅ {len(movies)} филма | Admin: {len(admins)} | Users: {len(regular_users)}")

        if not admins or not regular_users:
            print("❌ Липсват потребители! Първо пусни seed_users.py")
            return

        # Задачи: 1 admin ревю + 10 на филм от regular users
        tasks = []
        admin = admins[0]
        admin_movie = random.choice(movies)
        tasks.append((admin["id"], admin_movie["id"], choose_sentiment_category(), "admin"))

        for movie in movies:
            for _ in range(REVIEWS_PER_MOVIE):
                user = random.choice(regular_users)
                tasks.append((user["id"], movie["id"], choose_sentiment_category(), "user"))

        total_tasks = len(tasks)
        print(f"\n🎯 Ревюта за генериране: {total_tasks} (~5–10 минути)\n")

        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        inserted_count   = 0
        failed_count     = 0
        movies_by_id     = {m["id"]: m for m in movies}

        for i, (user_id, movie_id, sentiment_cat, user_type) in enumerate(tasks, start=1):
            movie = movies_by_id[movie_id]
            try:
                review_data = generate_review(movie, sentiment_cat)
                insert_review(cursor, user_id, movie_id, review_data["text"], review_data["true_sentiment"])

                sentiment_counts[sentiment_cat] += 1
                inserted_count += 1

                marker  = "👑" if user_type == "admin" else "  "
                emoji   = {"positive": "😊", "negative": "😞", "neutral": "😐"}[sentiment_cat]
                preview = review_data["text"][:60].replace("\n", " ")
                print(f"   [{i:3d}/{total_tasks}] {marker} {emoji} {sentiment_cat:8s} ({review_data['true_sentiment']:5.1f}) → {movie['title'][:25]:25s} | {preview}...")

                if i % 10 == 0:
                    conn.commit()

                time.sleep(0.1)

            except Exception as e:
                failed_count += 1
                print(f"   ❌ [{i:3d}/{total_tasks}] ГРЕШКА: {e}")

        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM reviews")
        total_in_db = cursor.fetchone()[0]
        cursor.execute("SELECT AVG(true_sentiment), MIN(true_sentiment), MAX(true_sentiment) FROM reviews")
        stats = cursor.fetchone()

        print("\n" + "=" * 60)
        print("✅ SEED ЗАВЪРШЕН!")
        print("=" * 60)
        print(f"   📊 Общо ревюта: {total_in_db} | Успешни: {inserted_count}" + (f" | Неуспешни: {failed_count}" if failed_count else ""))
        print(f"\n   Sentiment разпределение:")
        for sent, count in sentiment_counts.items():
            pct   = (count / inserted_count * 100) if inserted_count else 0
            emoji = {"positive": "😊", "negative": "😞", "neutral": "😐"}[sent]
            print(f"      {emoji} {sent:10s}: {count:3d} ({pct:5.1f}%)")
        print(f"\n   true_sentiment: avg={stats[0]:.2f}, min={stats[1]:.2f}, max={stats[2]:.2f}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n⚠️  Прекъснато. Запазвам генерираното до момента...")
        conn.commit()
        print("✅ Запазено!")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Грешка: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
        print("\n🔌 Връзката затворена.")


if __name__ == "__main__":
    seed_reviews()