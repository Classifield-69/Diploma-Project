"""
Blueprint за health check endpoints.

Тези endpoints се използват за:
- Проверка дали сървърът работи (/health)
- Проверка на връзката с базата (/api/db-status)

Полезни са за monitoring tools и за бърза диагностика при проблеми.
"""

from flask import Blueprint, jsonify
from mysql.connector import Error

import config
from database.connection import get_connection


# ============================================================
# Създаваме Blueprint
# ============================================================
# Първи аргумент: име на blueprint-а (използва се вътрешно от Flask)
# Втори аргумент: __name__ – помага на Flask да намира ресурсите
health_bp = Blueprint("health", __name__)


# ============================================================
# Endpoint: /health
# ============================================================
@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Базов health check endpoint.
    Връща статус 200 и съобщение, ако сървърът работи.
    """
    return jsonify({
        "status": "ok",
        "message": "Backend сървърът работи",
        "service": "Movie Reviews API"
    }), 200


# ============================================================
# Endpoint: /api/db-status
# ============================================================
@health_bp.route("/api/db-status", methods=["GET"])
def db_status():
    """
    Проверява връзката с MySQL базата.
    Връща информация за версията, базата и броя таблици.
    """
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "status": "ok",
            "database": config.DB_NAME,
            "mysql_version": version,
            "tables_count": len(tables),
            "tables": tables
        }), 200
        
    except Error as e:
        return jsonify({
            "status": "error",
            "message": "Неуспешно свързване с базата",
            "details": str(e)
        }), 500