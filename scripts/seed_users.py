"""
seed_users.py - Запълва таблицата users с тестови потребители

Създава:
- 1 admin потребител (от .env)
- 2 демо потребителя (от .env)
- 30 регулярни потребителя (генерирани от OpenAI на български)

Общо: 33 потребителя в базата
"""

import os
import sys
import json
import bcrypt
import mysql.connector
from openai import OpenAI
from dotenv import load_dotenv

# Зареждаме environment variables
load_dotenv()

# ================================
# Конфигурация
# ================================

NUM_GENERATED_USERS = 30  # Брой OpenAI-генерирани потребителя

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

def hash_password(plain_password: str) -> str:
    """Хешира паролата с bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def get_db_connection():
    """Създава връзка към MySQL базата."""
    return mysql.connector.connect(**DB_CONFIG)


def generate_users_with_openai(count: int) -> list[dict]:
    """
    Генерира списък от потребители с OpenAI.
    Връща списък с речници: [{username, email}, ...]
    """
    print(f"🤖 Генерирам {count} потребителя с OpenAI...")

    prompt = f"""Генерирай {count} реалистични български потребителски профила за уеб платформа за филмови ревюта.

За всеки потребител създай:
- username: латиница, малки букви, може с долна черта или цифра (напр. ivan_petrov, maria88, georgi_dimitrov)
- email: реалистичен имейл базиран на username (примерно с домейни @gmail.com, @abv.bg, @mail.bg, @example.com)

Имената трябва да са разнообразни български имена (мъжки и женски).
Не повтаряй username или email.

Върни САМО валиден JSON масив, без markdown форматиране, без коментари. Формат:
{{"users": [
  {{"username": "ivan_petrov", "email": "ivan.petrov@gmail.com"}},
  {{"username": "maria_ivanova", "email": "maria.ivanova@abv.bg"}}
]}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ти си helpful асистент, който връща САМО валиден JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    parsed = json.loads(content)

    # OpenAI връща обект - намираме списъка вътре
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


def insert_user(cursor, username: str, email: str, password_hash: str, role: str):
    """Вмъква един потребител в таблицата users."""
    query = """
        INSERT INTO users (username, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (username, email, password_hash, role))


# ================================
# Главна логика
# ================================

def seed_users():
    """Главната функция - запълва таблицата users."""

    # Прочитаме демо креденшъли от .env
    admin = {
        "username": os.getenv("DEMO_ADMIN_USERNAME"),
        "email": os.getenv("DEMO_ADMIN_EMAIL"),
        "password": os.getenv("DEMO_ADMIN_PASSWORD"),
        "role": "admin",
    }

    demo_user1 = {
        "username": os.getenv("DEMO_USER1_USERNAME"),
        "email": os.getenv("DEMO_USER1_EMAIL"),
        "password": os.getenv("DEMO_USER1_PASSWORD"),
        "role": "user",
    }

    demo_user2 = {
        "username": os.getenv("DEMO_USER2_USERNAME"),
        "email": os.getenv("DEMO_USER2_EMAIL"),
        "password": os.getenv("DEMO_USER2_PASSWORD"),
        "role": "user",
    }

    default_password = os.getenv("DEMO_USER_DEFAULT_PASSWORD")

    # Проверка дали .env е попълнен правилно
    if not all([admin["username"], admin["password"], default_password]):
        print("❌ Грешка: липсват DEMO_* променливи в .env файла!")
        sys.exit(1)

    # Свързваме се с базата
    print("🔌 Свързвам се с MySQL...")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # ==========================================
        # 1. Проверка дали таблицата вече има данни
        # ==========================================
        cursor.execute("SELECT COUNT(*) FROM users")
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            print(f"⚠️  Таблицата users вече съдържа {existing_count} реда.")
            answer = input("Искаш ли да изтриеш съществуващите потребители? (y/n): ")
            if answer.lower() == "y":
                # Първо трием ревютата (foreign key constraint)
                cursor.execute("DELETE FROM reviews")
                cursor.execute("DELETE FROM users")
                cursor.execute("ALTER TABLE users AUTO_INCREMENT = 1")
                cursor.execute("ALTER TABLE reviews AUTO_INCREMENT = 1")
                conn.commit()
                print("🗑️  Изтрити: всички ревюта и потребители (auto_increment ресетнат)")
            else:
                print("❌ Прекъсвам - не искаш да трия съществуващите данни.")
                return

        # ==========================================
        # 2. Вмъкваме admin потребителя
        # ==========================================
        print("\n👤 Вмъквам admin потребителя...")
        insert_user(
            cursor,
            admin["username"],
            admin["email"],
            hash_password(admin["password"]),
            admin["role"],
        )
        print(f"   ✅ {admin['username']} (admin)")

        # ==========================================
        # 3. Вмъкваме 2-та демо потребителя
        # ==========================================
        print("\n👥 Вмъквам демо потребителите...")
        for demo in [demo_user1, demo_user2]:
            insert_user(
                cursor,
                demo["username"],
                demo["email"],
                hash_password(demo["password"]),
                demo["role"],
            )
            print(f"   ✅ {demo['username']} (user)")

        # ==========================================
        # 4. Генерираме и вмъкваме 30 потребителя от OpenAI
        # ==========================================
        print(f"\n🎲 Генерирам {NUM_GENERATED_USERS} потребителя от OpenAI...")
        generated_users = generate_users_with_openai(NUM_GENERATED_USERS)

        # Хешираме default паролата веднъж (за всички 30)
        default_password_hash = hash_password(default_password)

        print(f"\n💾 Вмъквам {len(generated_users)} генерирани потребителя в базата...")
        inserted_count = 0
        skipped_count = 0

        for user in generated_users:
            try:
                insert_user(
                    cursor,
                    user["username"],
                    user["email"],
                    default_password_hash,
                    "user",
                )
                inserted_count += 1
                print(f"   ✅ {user['username']} ({user['email']})")
            except mysql.connector.errors.IntegrityError:
                # Дупликат username или email - пропускаме
                skipped_count += 1
                print(f"   ⚠️  Пропуснат (дупликат): {user['username']}")

        # ==========================================
        # 5. Commit и финално резюме
        # ==========================================
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        print("\n" + "=" * 50)
        print("✅ SEED ЗАВЪРШЕН УСПЕШНО!")
        print("=" * 50)
        print(f"   📊 Общо потребители в базата: {total}")
        print(f"   👤 Admin: 1")
        print(f"   👥 Demo users: 2")
        print(f"   🤖 Генерирани от OpenAI: {inserted_count}")
        if skipped_count > 0:
            print(f"   ⚠️  Пропуснати (дупликати): {skipped_count}")
        print("\n🔑 Demo креденшъли за вход:")
        print(f"   Admin:  {admin['username']} / {admin['password']}")
        print(f"   User1:  {demo_user1['username']} / {demo_user1['password']}")
        print(f"   User2:  {demo_user2['username']} / {demo_user2['password']}")
        print(f"   Останалите: <username> / {default_password}")
        print("=" * 50)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Грешка: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
        print("\n🔌 Връзката с базата затворена.")


if __name__ == "__main__":
    seed_users()