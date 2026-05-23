"""
seed_reviews.py - Запълва таблицата reviews с тестови ревюта

Генерира:
- 1 ревю от admin потребителя (на случаен филм)
- 170 ревюта от non-admin потребителите (по 10 на филм × 17 филма)
- Общо: 171 ревюта

Sentiment разпределение (приблизително):
- 45% позитивни (true_sentiment 70-100)
- 30% негативни (true_sentiment 0-30)
- 25% неутрални (true_sentiment 40-60)

Стилове на ревютата (случайно вариране):
- Формални / Неформални
- Кратки (50-100 думи) / Средни (100-250 думи) / Дълги (250-500 думи)
- С/Без правописни грешки
"""

import os
import sys
import json
import random
import time
import mysql.connector
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ================================
# Конфигурация
# ================================

REVIEWS_PER_MOVIE = 10  # Брой ревюта на филм (от non-admin)

# Sentiment разпределение (Вариант B)
SENTIMENT_WEIGHTS = {
    "positive": 0.45,  # 45%
    "negative": 0.30,  # 30%
    "neutral": 0.25,   # 25%
}

# Sentiment диапазони (стойност 0-100)
SENTIMENT_RANGES = {
    "positive": (70, 100),
    "negative": (0, 30),
    "neutral": (40, 60),
}

# Стилове на писане
STYLES = ["formal", "informal", "casual_with_typos", "short_and_punchy"]

# Дължина на ревютата
LENGTH_OPTIONS = [
    {"name": "кратко", "words": (50, 100)},
    {"name": "средно", "words": (100, 250)},
    {"name": "дълго", "words": (250, 500)},
]

# OpenAI клиент
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# DB конфигурация от .env
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}


# ================================
# Помощни функции
# ================================

def get_db_connection():
    """Създава връзка към MySQL базата."""
    return mysql.connector.connect(**DB_CONFIG)


def fetch_movies(cursor) -> list[dict]:
    """Извлича всички филми от базата."""
    cursor.execute("SELECT id, title, year, director FROM movies ORDER BY id")
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetch_users(cursor) -> dict:
    """
    Извлича всички потребители и ги разделя на admin / non-admin.
    Връща: {"admin": [...], "users": [...]}
    """
    cursor.execute("SELECT id, username, role FROM users ORDER BY id")
    columns = [desc[0] for desc in cursor.description]
    all_users = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return {
        "admin": [u for u in all_users if u["role"] == "admin"],
        "users": [u for u in all_users if u["role"] == "user"],
    }


def choose_sentiment_category() -> str:
    """Избира sentiment категория според weighted разпределение."""
    rand = random.random()
    if rand < SENTIMENT_WEIGHTS["positive"]:
        return "positive"
    elif rand < SENTIMENT_WEIGHTS["positive"] + SENTIMENT_WEIGHTS["negative"]:
        return "negative"
    else:
        return "neutral"


def build_prompt(movie: dict, sentiment_category: str, style: str, length: dict) -> str:
    """Конструира prompt за OpenAI на базата на филма, sentiment-а и стила."""

    sentiment_descriptions = {
        "positive": "ПОЗИТИВНО (харесал си филма, препоръчваш го)",
        "negative": "НЕГАТИВНО (не си харесал филма, критикуваш го)",
        "neutral": "НЕУТРАЛНО (смесени чувства, някои неща харесваш, други не)",
    }

    style_descriptions = {
        "formal": "формален език, граматически коректно, като професионален критик",
        "informal": "неформален разговорен стил, като обикновен зрител в социалните медии",
        "casual_with_typos": "небрежен стил с няколко правописни грешки или типографски грешки (както пишат хората бързо в социалните мрежи)",
        "short_and_punchy": "кратък и директен стил, без излишни обяснения",
    }

    sentiment_range = SENTIMENT_RANGES[sentiment_category]
    min_words, max_words = length["words"]

    prompt = f"""Напиши ревю на български език за филма "{movie['title']}" ({movie['year']}), режисьор {movie['director']}.

Изисквания:
- Sentiment: {sentiment_descriptions[sentiment_category]}
- Стил: {style_descriptions[style]}
- Дължина: между {min_words} и {max_words} думи
- Не споменавай че си AI или че пишеш ревю за тестове
- Звучи като реален човек написал ревюто
- Може да споменеш конкретни сцени, актьори или елементи от филма

Върни САМО валиден JSON формат:
{{
  "text": "тук е текстът на ревюто...",
  "true_sentiment": число между {sentiment_range[0]} и {sentiment_range[1]}
}}

`true_sentiment` трябва да отразява реалната емоционална оценка в текста (0=много негативно, 100=много позитивно)."""

    return prompt


def generate_review(movie: dict, sentiment_category: str) -> dict:
    """
    Генерира едно ревю с OpenAI.
    Връща: {"text": "...", "true_sentiment": 87.5}
    """
    style = random.choice(STYLES)
    length = random.choice(LENGTH_OPTIONS)

    prompt = build_prompt(movie, sentiment_category, style, length)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ти си генератор на реалистични български филмови ревюта. Връщаш САМО валиден JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.9,  # По-висока за повече вариация
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    parsed = json.loads(content)

    # Валидираме структурата
    if "text" not in parsed or "true_sentiment" not in parsed:
        raise ValueError(f"OpenAI не върна правилен формат: {parsed}")

    # Уверяваме се, че sentiment е число
    parsed["true_sentiment"] = float(parsed["true_sentiment"])

    # Clamp между 0 и 100 (за всеки случай)
    parsed["true_sentiment"] = max(0.0, min(100.0, parsed["true_sentiment"]))

    return parsed


def insert_review(cursor, user_id: int, movie_id: int, text: str, true_sentiment: float):
    """Вмъква едно ревю в таблицата reviews."""
    query = """
        INSERT INTO reviews (user_id, movie_id, text, true_sentiment, lstm_prediction, bilstm_prediction)
        VALUES (%s, %s, %s, %s, NULL, NULL)
    """
    cursor.execute(query, (user_id, movie_id, text, true_sentiment))


# ================================
# Главна логика
# ================================

def seed_reviews():
    """Главната функция - запълва таблицата reviews."""

    # Свързваме се с базата
    print("🔌 Свързвам се с MySQL...")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # ==========================================
        # 1. Проверка дали таблицата вече има данни
        # ==========================================
        cursor.execute("SELECT COUNT(*) FROM reviews")
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            print(f"⚠️  Таблицата reviews вече съдържа {existing_count} реда.")
            answer = input("Искаш ли да изтриеш съществуващите ревюта? (y/n): ")
            if answer.lower() == "y":
                cursor.execute("DELETE FROM reviews")
                cursor.execute("ALTER TABLE reviews AUTO_INCREMENT = 1")
                conn.commit()
                print("🗑️  Изтрити: всички ревюта (auto_increment ресетнат)")
            else:
                print("❌ Прекъсвам - не искаш да трия съществуващите данни.")
                return

        # ==========================================
        # 2. Извличаме филмите и потребителите
        # ==========================================
        print("\n📚 Извличам филми от базата...")
        movies = fetch_movies(cursor)
        print(f"   ✅ Намерих {len(movies)} филма")

        if len(movies) == 0:
            print("❌ Няма филми в базата! Първо пусни seed_movies.py")
            return

        print("\n👥 Извличам потребители от базата...")
        users_by_role = fetch_users(cursor)
        admins = users_by_role["admin"]
        regular_users = users_by_role["users"]
        print(f"   ✅ Admin: {len(admins)}, Regular users: {len(regular_users)}")

        if len(admins) == 0 or len(regular_users) == 0:
            print("❌ Липсват потребители! Първо пусни seed_users.py")
            return

        # ==========================================
        # 3. Подготовка на задачите за генериране
        # ==========================================
        tasks = []  # Списък: [(user_id, movie_id, sentiment_category), ...]

        # 3.1 Admin ревю - 1 ревю на случаен филм
        admin = admins[0]
        admin_movie = random.choice(movies)
        admin_sentiment = choose_sentiment_category()
        tasks.append((admin["id"], admin_movie["id"], admin_sentiment, "admin"))

        # 3.2 Non-admin ревюта - 10 на филм
        for movie in movies:
            for _ in range(REVIEWS_PER_MOVIE):
                user = random.choice(regular_users)
                sentiment = choose_sentiment_category()
                tasks.append((user["id"], movie["id"], sentiment, "user"))

        total_tasks = len(tasks)
        print(f"\n🎯 Общо ревюта за генериране: {total_tasks}")
        print(f"   👤 От admin: 1")
        print(f"   👥 От regular users: {total_tasks - 1}")

        # ==========================================
        # 4. Генериране и вмъкване на ревюта
        # ==========================================
        print(f"\n🤖 Започвам генериране с OpenAI (gpt-4o-mini)...")
        print(f"   ⏱️  Очаквано време: 5-10 минути\n")

        # Brояч по sentiment категории
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        inserted_count = 0
        failed_count = 0

        # Map с филмите за бърз lookup по id
        movies_by_id = {m["id"]: m for m in movies}

        for i, (user_id, movie_id, sentiment_cat, user_type) in enumerate(tasks, start=1):
            movie = movies_by_id[movie_id]
            try:
                # Генерираме ревюто
                review_data = generate_review(movie, sentiment_cat)

                # Вмъкваме в базата
                insert_review(
                    cursor,
                    user_id,
                    movie_id,
                    review_data["text"],
                    review_data["true_sentiment"],
                )

                sentiment_counts[sentiment_cat] += 1
                inserted_count += 1

                # Progress индикатор
                marker = "👑" if user_type == "admin" else "  "
                sentiment_emoji = {
                    "positive": "😊",
                    "negative": "😞",
                    "neutral": "😐",
                }[sentiment_cat]

                preview = review_data["text"][:60].replace("\n", " ")
                print(
                    f"   [{i:3d}/{total_tasks}] {marker} {sentiment_emoji} "
                    f"{sentiment_cat:8s} ({review_data['true_sentiment']:5.1f}) "
                    f"→ {movie['title'][:25]:25s} | {preview}..."
                )

                # Commit на всеки 10 ревюта (защита при срив)
                if i % 10 == 0:
                    conn.commit()

                # Леко забавяне за rate limiting (защитна мярка)
                time.sleep(0.1)

            except Exception as e:
                failed_count += 1
                print(f"   ❌ [{i:3d}/{total_tasks}] ГРЕШКА: {e}")
                continue

        # Финален commit
        conn.commit()

        # ==========================================
        # 5. Финално резюме
        # ==========================================
        cursor.execute("SELECT COUNT(*) FROM reviews")
        total_in_db = cursor.fetchone()[0]

        cursor.execute("""
            SELECT 
                AVG(true_sentiment) as avg_sentiment,
                MIN(true_sentiment) as min_sentiment,
                MAX(true_sentiment) as max_sentiment
            FROM reviews
        """)
        stats = cursor.fetchone()

        print("\n" + "=" * 60)
        print("✅ SEED ЗАВЪРШЕН УСПЕШНО!")
        print("=" * 60)
        print(f"   📊 Общо ревюта в базата: {total_in_db}")
        print(f"   ✅ Успешно генерирани: {inserted_count}")
        if failed_count > 0:
            print(f"   ❌ Неуспешни: {failed_count}")
        print(f"\n   📈 Sentiment разпределение:")
        for sent, count in sentiment_counts.items():
            percent = (count / inserted_count * 100) if inserted_count > 0 else 0
            emoji = {"positive": "😊", "negative": "😞", "neutral": "😐"}[sent]
            print(f"      {emoji} {sent:10s}: {count:3d} ({percent:5.1f}%)")
        print(f"\n   📊 Статистика на true_sentiment:")
        print(f"      Средно: {stats[0]:.2f}")
        print(f"      Мин:    {stats[1]:.2f}")
        print(f"      Макс:   {stats[2]:.2f}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠️  Прекъснато от потребителя. Запазвам каквото е генерирано до момента...")
        conn.commit()
        print("✅ Запазено!")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Грешка: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
        print("\n🔌 Връзката с базата затворена.")


if __name__ == "__main__":
    seed_reviews()