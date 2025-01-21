import sqlite3
import os

DB_NAME = os.path.join(os.path.dirname(__file__), "app.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create table for user sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            session_token TEXT NOT NULL UNIQUE
        )
    """)

    # Create table for random numbers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS random_numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            random_number INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()

def get_db_connection():
    """
    Returns a new SQLite connection for each call.
    """
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)  # Disable thread check
    conn.row_factory = sqlite3.Row
    return conn

init_db()
