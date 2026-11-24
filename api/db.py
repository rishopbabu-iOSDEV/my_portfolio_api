import os
from datetime import date, datetime
from decimal import Decimal
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def connect():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "future_portfolio_db")
    )

def fetch_all(conn, sql, params=()):
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()

def to_json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"cannot convert {type(value).__name__} to JSON")
