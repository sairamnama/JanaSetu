"""
GramSeva - Panchayat Announcements & Dynamic Localization Routes
Handles civic public announcements, emergency broadcasts, Gram Sabha notices,
and dynamic system message translation via Google Cloud Translation API.
"""

from flask import Blueprint, request, jsonify, session
from core.database import get_db_connection
from core.security import login_required, role_required
from services.translation_service import translate_announcement, translate_dynamic_text, is_api_configured

announcements_bp = Blueprint('announcements', __name__, url_prefix='/api')


@announcements_bp.route('/announcements', methods=['GET'])
def get_announcements():
    """
    Retrieves all published Panchayat announcements sorted chronologically.
    Automatically translates announcements to Telugu when Telugu language is selected.
    """
    lang = request.args.get('lang') or session.get('lang') or request.cookies.get('gramseva_lang') or 'en'

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT a.*, u.full_name as published_by_name
    FROM announcements a
    JOIN users u ON a.published_by = u.id
    ORDER BY a.created_at DESC
    ''')
    raw_announcements = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if lang == 'te':
        announcements = [translate_announcement(a, target_lang='te') for a in raw_announcements]
    else:
        announcements = raw_announcements

    return jsonify({'success': True, 'announcements': announcements, 'lang': lang})


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


@announcements_bp.route('/translate-text', methods=['POST'])
def translate_text_endpoint():
    """
    Translates dynamic system-generated text securely from the backend.
    API key is kept strictly on the server and never exposed to the client.
    """
    data = request.get_json(silent=True) or request.form or {}
    text = data.get('text', '').strip()
    target_lang = data.get('target', 'te').strip().lower()
    source_lang = data.get('source', 'en').strip().lower()

    if not text:
        return jsonify({'success': True, 'translated': '', 'original': ''})

    translated = translate_dynamic_text(text, target_lang=target_lang, source_lang=source_lang)
    return jsonify({
        'success': True,
        'translated': translated,
        'original': text,
        'target': target_lang,
        'api_configured': is_api_configured()
    })
