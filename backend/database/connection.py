# db/connection.py
# Управление на връзката с MySQL базата
# Конфигурацията се чете от config.py (порт, хост, credentials)

import mysql.connector
from mysql.connector import Error
import sys
import os

# Добавяме backend папката към пътя, за да можем да импортираме config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


def get_connection():
    # Отваря и връща нова връзка към базата данни
    # При грешка (неверни credentials, спрян MySQL и др.) вдига Error
    try:
        connection = mysql.connector.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
        )
        
        if connection.is_connected():
            return connection
        else:
            raise Error("Връзката с базата не е активна след свързване")
            
    except Error as e:
        raise Error(
            f"Неуспешно свързване с MySQL базата '{config.DB_NAME}' "
            f"на {config.DB_HOST}:{config.DB_PORT}. Грешка: {e}"
        )


def test_connection():
    # Проверява връзката с базата и отпечатва версия и налични таблици
    try:
        connection = get_connection()
        
        cursor = connection.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        connection.close()
        
        print(f"✅ Връзка с MySQL успешна")
        print(f"   Версия: {version}")
        print(f"   База: {config.DB_NAME}")
        print(f"   Таблици: {len(tables)} ({', '.join(tables)})")
        
        return True
        
    except Error as e:
        print(f"❌ Грешка при свързване: {e}")
        return False


# Ако файлът се пусне директно (не като импорт), пуска тестова проверка
if __name__ == "__main__":
    test_connection()