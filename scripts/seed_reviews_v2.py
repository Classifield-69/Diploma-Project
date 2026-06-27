# seed_reviews_v2.py — генерира 140 кратки ревюта (5–15 думи) за 14 филма.
# Филми 1, 14, 15 се пропускат — вече имат дълги ревюта (контролна група).

import os
import json
import random
import time
import mysql.connector
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

REVIEWS_PER_MOVIE = 10
SKIP_MOVIE_IDS    = {1, 14, 15}

SENTIMENT_WEIGHTS = {"positive": 0.45, "negative": 0.30, "neutral": 0.25}
SENTIMENT_RANGES  = {"positive": (70, 100), "negative": (0, 30), "neutral": (40, 60)}
STYLES            = ["formal", "informal", "casual_with_typos", "short_and_punchy"]

# Само кратки ревюта — в рамките на P95=19 токена от тренировъчния dataset
LENGTH_OPTIONS = [{"name": "кратко", "words": (5, 15)}]

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


def fetch_users(cursor) -> list[dict]:
    """Връща само non-admin потребители."""
    cursor.execute("SELECT id, username FROM users WHERE role = 'user' ORDER BY id")
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def choose_sentiment() -> str:
    rand = random.random()
    if rand < SENTIMENT_WEIGHTS["positive"]:
        return "positive"
    elif rand < SENTIMENT_WEIGHTS["positive"] + SENTIMENT_WEIGHTS["negative"]:
        return "negative"
    return "neutral"


def build_prompt(movie: dict, sentiment_category: str, style: str) -> str:
    sentiment_descriptions = {
        "positive": "ПОЗИТИВНО (харесал си филма)",
        "negative": "НЕГАТИВНО (не си харесал филма)",
        "neutral":  "НЕУТРАЛНО (смесени чувства)",
    }
    style_descriptions = {
        "formal":            "формален език, кратък и точен",
        "informal":          "неформален разговорен стил",
        "casual_with_typos": "небрежен стил с някоя правописна грешка",
        "short_and_punchy":  "директен стил, без излишни думи",
    }
    sentiment_range = SENTIMENT_RANGES[sentiment_category]

    return f"""Напиши ЕДНО ревю на български за филма "{movie['title']}" ({movie['year']}), режисьор {movie['director']}.

Изисквания:
- Sentiment: {sentiment_descriptions[sentiment_category]}
- Стил: {style_descriptions[style]}
- Дължина: между 5 и 15 думи (ЗАДЪЛЖИТЕЛНО)
- Звучи като реален човек

Върни САМО валиден JSON:
{{
  "text": "тук е ревюто...",
  "true_sentiment": число между {sentiment_range[0]} и {sentiment_range[1]}
}}"""


def generate_review(movie: dict, sentiment_category: str) -> dict:
    """Генерира едно кратко ревю. Връща {text, true_sentiment}."""
    style  = random.choice(STYLES)
    prompt = build_prompt(movie, sentiment_category, style)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Генерираш кратки български филмови ревюта. Връщаш САМО валиден JSON."},
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


def seed_short_reviews():
    print("🔌 Свързвам се с MySQL...")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM reviews")
        print(f"ℹ️  Текущо ревюта в базата: {cursor.fetchone()[0]} (запазват се)")

        movies        = fetch_movies(cursor)
        target_movies = [m for m in movies if m["id"] not in SKIP_MOVIE_IDS]
        print(f"🎬 Филми за генериране: {len(target_movies)} (пропускам {SKIP_MOVIE_IDS})")

        users = fetch_users(cursor)
        if not users:
            print("❌ Няма regular users в базата!")
            return
        print(f"👥 Потребители: {len(users)}")

        tasks = []
        for movie in target_movies:
            for _ in range(REVIEWS_PER_MOVIE):
                user      = random.choice(users)
                sentiment = choose_sentiment()
                tasks.append((user["id"], movie["id"], movie, sentiment))

        total = len(tasks)
        print(f"\n🎯 Ревюта за генериране: {total} (~{total // 60 + 1} мин)\n")

        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        inserted = 0
        failed   = 0

        for i, (user_id, movie_id, movie, sentiment_cat) in enumerate(tasks, start=1):
            try:
                review_data = generate_review(movie, sentiment_cat)
                insert_review(cursor, user_id, movie_id, review_data["text"], review_data["true_sentiment"])

                sentiment_counts[sentiment_cat] += 1
                inserted += 1

                emoji   = {"positive": "😊", "negative": "😞", "neutral": "😐"}[sentiment_cat]
                preview = review_data["text"][:70].replace("\n", " ")
                print(f"  [{i:3d}/{total}] {emoji} {sentiment_cat:8s} ({review_data['true_sentiment']:5.1f}) → {movie['title'][:25]:25s} | {preview}")

                if i % 10 == 0:
                    conn.commit()

                time.sleep(0.1)

            except Exception as e:
                failed += 1
                print(f"  [{i:3d}/{total}] ❌ ГРЕШКА: {e}")

        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM reviews")
        total_in_db = cursor.fetchone()[0]

        print("\n" + "=" * 60)
        print("✅ ГОТОВО!")
        print("=" * 60)
        print(f"  📊 Общо ревюта в базата: {total_in_db} | Добавени: {inserted}" + (f" | Неуспешни: {failed}" if failed else ""))
        print(f"\n  Sentiment разпределение:")
        for sent, count in sentiment_counts.items():
            pct   = (count / inserted * 100) if inserted else 0
            emoji = {"positive": "😊", "negative": "😞", "neutral": "😐"}[sent]
            print(f"    {emoji} {sent:10s}: {count:3d} ({pct:5.1f}%)")
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
        print("🔌 Връзката затворена.")


if __name__ == "__main__":
    seed_short_reviews()