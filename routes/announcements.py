"""
GramSeva - Panchayat Announcements Routes
Handles civic public announcements, emergency broadcasts, and Gram Sabha notices.
"""

from flask import Blueprint, request, jsonify, session
from core.database import get_db_connection
from core.security import login_required, role_required

announcements_bp = Blueprint('announcements', __name__, url_prefix='/api')

@announcements_bp.route('/announcements', methods=['GET'])
def get_announcements():
    """Retrieves all published Panchayat announcements sorted chronologically."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT a.*, u.full_name as published_by_name
    FROM announcements a
    JOIN users u ON a.published_by = u.id
    ORDER BY a.created_at DESC
    ''')
    announcements = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'announcements': announcements})

@announcements_bp.route('/announcements', methods=['POST'])
@login_required
@role_required(['admin'])
def create_announcement():
    """Publishes a new Panchayat announcement or emergency notice."""
    data = request.json or {}
    title = data.get('title', '').strip()
    category = data.get('category', 'General').strip()
    content = data.get('content', '').strip()
    is_emergency = 1 if data.get('is_emergency') else 0

    if not title or not content:
        return jsonify({'success': False, 'error': 'Title and content are required.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO announcements (title, category, content, is_emergency, published_by)
    VALUES (?, ?, ?, ?, ?)
    ''', (title, category, content, is_emergency, session['user_id']))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Panchayat announcement published successfully.'})
