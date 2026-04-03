import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "smartreceipt.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def add_expense(item: str, amount: float, category: str) -> Dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (item, amount, category) VALUES (?, ?, ?)",
        (item, amount, category)
    )
    conn.commit()
    expense_id = cursor.lastrowid
    conn.close()

    return {
        "id": expense_id,
        "item": item,
        "amount": amount,
        "category": category,
        "created_at": datetime.now().isoformat()
    }


def get_all_expenses() -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]
