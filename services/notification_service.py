"""
GramSeva - Notification Service
Centralized helper for creating in-app notifications for citizens, officers, workers, and admins.
"""

from datetime import datetime
import sqlite3

def send_notification(cursor: sqlite3.Cursor, user_id: int, grievance_id: int, title: str, message: str, timestamp_str: str = None):
    """Inserts a notification record for a specific user."""
    if not timestamp_str:
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
    INSERT INTO notifications (user_id, grievance_id, title, message, created_at)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, grievance_id, title, message, timestamp_str))

def notify_admins(cursor: sqlite3.Cursor, grievance_id: int, title: str, message: str, timestamp_str: str = None):
    """Sends a notification to all registered administrators."""
    if not timestamp_str:
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT id FROM users WHERE role = 'admin'")
    admins = cursor.fetchall()
    for admin in admins:
        send_notification(cursor, admin['id'], grievance_id, title, message, timestamp_str)
