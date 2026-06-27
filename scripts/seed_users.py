# seed_users.py — запълва таблицата users.
# Създава: 1 admin + 2 демо потребителя (от .env) + 30 генерирани от OpenAI.

import os
import sys
import json
import bcrypt
import mysql.connector
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

NUM_GENERATED_USERS = 30

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}


def hash_password(plain_password: str) -> str:
    """Хешира парола с bcrypt."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def generate_users_with_openai(count: int) -> list[dict]:
    """Генерира {count} потребителски профила с OpenAI. Връща [{username, email}, ...]"""
    print(f"🤖 Генерирам {count} потребителя с OpenAI...")

    prompt = f"""Генерирай {count} реалистични български потребителски профила за уеб платформа за филмови ревюта.

За всеки потребител:
- username: латиница, малки букви, може с долна черта или цифра
- email: реалистичен имейл (@gmail.com, @abv.bg, @mail.bg, @example.com)

Разнообразни български имена (мъжки и женски). Без повторения.

Върни САМО валиден JSON:
{{"users": [
  {{"username": "ivan_petrov", "email": "ivan.petrov@gmail.com"}}
]}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Връщаш САМО валиден JSON."},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.8,
        response_format={"type": "json_object"},
    )

    parsed = json.loads(response.choices[0].message.content)

    if isinstance(parsed, dict):
        for key, value in parsed.items():
            if isinstance(value, list):
                users = value
                break
        else:
            raise ValueError("OpenAI не върна списък с потребители")
    else:
        users = parsed

    print(f"✅ OpenAI върна {len(users)} потребителя")
    return users


def insert_user(cursor, username, email, password_hash, role):
    cursor.execute(
        "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)",
        (username, email, password_hash, role)
    )


def seed_users():
    admin = {
        "username": os.getenv("DEMO_ADMIN_USERNAME"),
        "email":    os.getenv("DEMO_ADMIN_EMAIL"),
        "password": os.getenv("DEMO_ADMIN_PASSWORD"),
        "role": "admin",
    }
    demo_user1 = {
        "username": os.getenv("DEMO_USER1_USERNAME"),
        "email":    os.getenv("DEMO_USER1_EMAIL"),
        "password": os.getenv("DEMO_USER1_PASSWORD"),
        "role": "user",
    }
    demo_user2 = {
        "username": os.getenv("DEMO_USER2_USERNAME"),
        "email":    os.getenv("DEMO_USER2_EMAIL"),
        "password": os.getenv("DEMO_USER2_PASSWORD"),
        "role": "user",
    }
    default_password = os.getenv("DEMO_USER_DEFAULT_PASSWORD")

    if not all([admin["username"], admin["password"], default_password]):
        print("❌ Грешка: липсват DEMO_* променливи в .env файла!")
        sys.exit(1)

    print("🔌 Свързвам се с MySQL...")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            print(f"⚠️  Таблицата users вече съдържа {existing_count} реда.")
            answer = input("Искаш ли да изтриеш съществуващите потребители? (y/n): ")
            if answer.lower() == "y":
                cursor.execute("DELETE FROM reviews")
                cursor.execute("DELETE FROM users")
                cursor.execute("ALTER TABLE users AUTO_INCREMENT = 1")
                cursor.execute("ALTER TABLE reviews AUTO_INCREMENT = 1")
                conn.commit()
                print("🗑️  Изтрити: всички ревюта и потребители")
            else:
                print("❌ Прекъсвам.")
                return

        print("\n👤 Вмъквам admin потребителя...")
        insert_user(cursor, admin["username"], admin["email"], hash_password(admin["password"]), admin["role"])
        print(f"   ✅ {admin['username']} (admin)")

        print("\n👥 Вмъквам демо потребителите...")
        for demo in [demo_user1, demo_user2]:
            insert_user(cursor, demo["username"], demo["email"], hash_password(demo["password"]), demo["role"])
            print(f"   ✅ {demo['username']} (user)")

        print(f"\n🎲 Генерирам {NUM_GENERATED_USERS} потребителя от OpenAI...")
        generated_users  = generate_users_with_openai(NUM_GENERATED_USERS)
        default_hash     = hash_password(default_password)

        inserted_count = 0
        skipped_count  = 0

        print(f"\n💾 Вмъквам {len(generated_users)} потребителя в базата...")
        for user in generated_users:
            try:
                insert_user(cursor, user["username"], user["email"], default_hash, "user")
                inserted_count += 1
                print(f"   ✅ {user['username']} ({user['email']})")
            except mysql.connector.errors.IntegrityError:
                skipped_count += 1
                print(f"   ⚠️  Пропуснат (дупликат): {user['username']}")

        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        print("\n" + "=" * 50)
        print("✅ SEED ЗАВЪРШЕН!")
        print("=" * 50)
        print(f"   📊 Общо потребители: {total}")
        print(f"   👤 Admin: 1 | 👥 Demo: 2 | 🤖 Генерирани: {inserted_count}")
        if skipped_count > 0:
            print(f"   ⚠️  Пропуснати (дупликати): {skipped_count}")
        print(f"\n🔑 Demo креденшъли:")
        print(f"   Admin: {admin['username']} / {admin['password']}")
        print(f"   User1: {demo_user1['username']} / {demo_user1['password']}")
        print(f"   User2: {demo_user2['username']} / {demo_user2['password']}")
        print(f"   Останалите: <username> / {default_password}")
        print("=" * 50)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Грешка: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
        print("\n🔌 Връзката затворена.")


if __name__ == "__main__":
    seed_users()