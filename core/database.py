"""
GramSeva - Database Connection Manager
Provides thread-safe SQLite connection factory with row factory and foreign key constraints enabled.
"""

import sqlite3
from core.config import DB_PATH

def get_db_connection():
    """
    Creates and returns a connection to SQLite database.
    Configures row_factory for dict-like access and enables SQLite foreign key enforcement.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
