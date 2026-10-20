"""
GramSeva - Notification Center Routes
Manages in-app notification alerts, status-change tracking updates, and read acknowledgments.
"""

from flask import Blueprint, jsonify, session
from core.database import get_db_connection
from core.security import login_required

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api')

@notifications_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    """Retrieves recent 30 notifications for the authenticated user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM notifications 
    WHERE user_id = ?
    ORDER BY created_at DESC LIMIT 30
    ''', (session['user_id'],))
    notifs = [dict(n) for n in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'notifications': notifs})

@notifications_bp.route('/notifications/<int:nid>/read', methods=['POST'])
@login_required
def mark_notification_read(nid):
    """Marks an individual notification as read."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (nid, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@notifications_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Marks all notifications for the authenticated user as read."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (session['user_id'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True})
