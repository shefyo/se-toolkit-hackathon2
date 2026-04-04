import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "smartreceipt.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Advice history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS advice_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Chat messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT NOT NULL,
            bot_response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ==================== EXPENSES ====================

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


def get_expenses_by_category() -> Dict[str, float]:
    """Get total spending per category."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        GROUP BY category
        ORDER BY total DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return {row["category"]: row["total"] for row in rows}


def get_total_spending() -> float:
    """Get total spending across all expenses."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM expenses")
    result = cursor.fetchone()
    conn.close()
    return result["total"] if result else 0.0


def get_recent_expenses(limit: int = 50) -> List[Dict]:
    """Get recent expenses for context."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==================== ADVICE ====================

def save_advice(content: str) -> Dict:
    """Save generated advice to history."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO advice_history (content) VALUES (?)", (content,))
    conn.commit()
    advice_id = cursor.lastrowid
    conn.close()

    return {
        "id": advice_id,
        "content": content,
        "created_at": datetime.now().isoformat()
    }


def get_advice_history(limit: int = 10) -> List[Dict]:
    """Get recent advice entries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM advice_history ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==================== CHAT ====================

def save_chat_message(user_message: str, bot_response: str) -> Dict:
    """Save a chat exchange."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_messages (user_message, bot_response) VALUES (?, ?)",
        (user_message, bot_response)
    )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()

    return {
        "id": msg_id,
        "user_message": user_message,
        "bot_response": bot_response,
        "created_at": datetime.now().isoformat()
    }


def get_chat_history(limit: int = 20) -> List[Dict]:
    """Get recent chat messages."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
