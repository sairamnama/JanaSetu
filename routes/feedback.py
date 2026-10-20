"""
GramSeva - Citizen Feedback Routes
Handles 5-star ratings, resolution satisfaction feedback, and automatic ticket closure.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, session
from core.database import get_db_connection
from core.security import login_required
from core.constants import apply_status_transition

feedback_bp = Blueprint('feedback', __name__, url_prefix='/api')

@feedback_bp.route('/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Records citizen satisfaction rating and closes the resolved grievance."""
    data = request.json or {}
    grievance_id = data.get('grievance_id')
    star_rating = data.get('star_rating')
    satisfaction = data.get('satisfaction')
    comments = data.get('comments', '').strip()

    if not grievance_id or not star_rating or not satisfaction:
        return jsonify({'success': False, 'error': 'Grievance ID, star rating (1-5), and satisfaction are required.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM grievances WHERE id = ?", (grievance_id,))
    grievance = cursor.fetchone()

    if not grievance:
        conn.close()
        return jsonify({'success': False, 'error': 'Grievance not found'}), 404

    if grievance['citizen_id'] != session['user_id']:
        conn.close()
        return jsonify({'success': False, 'error': 'You can only provide feedback for your own grievance.'}), 403

    if grievance['status'] not in ('RESOLVED', 'CLOSED'):
        conn.close()
        return jsonify({'success': False, 'error': 'Feedback can only be submitted for resolved grievances.'}), 400

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
    INSERT OR REPLACE INTO feedback (grievance_id, citizen_id, star_rating, satisfaction, comments, submitted_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (grievance_id, session['user_id'], int(star_rating), satisfaction, comments, now_str))

    if grievance['status'] == 'RESOLVED':
        apply_status_transition(
            cursor=cursor,
            grievance_id=grievance_id,
            from_status='RESOLVED',
            to_status='CLOSED',
            remarks='Citizen submitted feedback. Grievance closed.',
            user_id=session['user_id'],
            user_role='citizen',
            now_str=now_str
        )

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Thank you! Your feedback has been recorded and grievance is closed.'})
