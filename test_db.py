"""
Тестов скрипт за проверка на връзката с MySQL базата.
Чете credentials от .env файла и опитва да се свърже.
"""

import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# Зареждаме променливите от .env файла
load_dotenv()

# Конфигурация за връзка с базата
db_config = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

print("=" * 50)
print("Тест на връзката с MySQL")
print("=" * 50)
print(f"Свързване към: {db_config['host']}:{db_config['port']}")
print(f"Потребител: {db_config['user']}")
print(f"База данни: {db_config['database']}")
print("-" * 50)

try:
    conn = mysql.connector.connect(**db_config)
    
    if conn.is_connected():
        server_info = conn.get_server_info
        print(f"✓ Връзката е УСПЕШНА!")
        print(f"  MySQL версия: {server_info}")
        
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        current_db = cursor.fetchone()[0]
        print(f"  Активна база: {current_db}")
        
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        
        if tables:
            print(f"  Таблици в базата: {len(tables)}")
            for table in tables:
                print(f"    - {table[0]}")
        else:
            print(f"  Базата е празна (няма таблици)")
        
        cursor.close()
        
except Error as e:
    print(f"✗ Грешка при свързване: {e}")

finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()
        print("-" * 50)
        print("Връзката е затворена.")

print("=" * 50)