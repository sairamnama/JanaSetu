"""
GramSeva - Protected Uploads & Attachment Routes
Enforces role-based access control on uploaded evidence photos and completion proof documents.
"""

import os
from flask import Blueprint, jsonify, session, send_from_directory
from werkzeug.utils import secure_filename
from core.database import get_db_connection
from core.config import UPLOAD_FOLDER
from core.security import login_required

uploads_bp = Blueprint('uploads', __name__, url_prefix='/api')

@uploads_bp.route('/uploads/<path:filename>', methods=['GET'])
@login_required
def get_protected_upload(filename):
    """
    Security Verification: Ensures private evidence files are only accessible to authorized roles:
    - Submitting citizen
    - Assigned supervising officer
    - Assigned field technician/worker
    - Administrator
    """
    safe_name = secure_filename(filename)
    if not safe_name:
        return jsonify({'success': False, 'error': 'Invalid attachment filename.'}), 400

    # Check database association
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT g.citizen_id, g.assigned_officer_id, g.assigned_worker_id, g.department_id,
           o.user_id as officer_user_id, w.user_id as worker_user_id,
           rp.worker_id as proof_worker_user_id
    FROM grievances g
    LEFT JOIN officers o ON g.assigned_officer_id = o.id
    LEFT JOIN workers w ON g.assigned_worker_id = w.id
    LEFT JOIN resolution_proofs rp ON rp.grievance_id = g.id
    WHERE g.evidence_image LIKE ? OR rp.proof_file LIKE ? OR rp.additional_evidence LIKE ?
    ''', (f"%{safe_name}", f"%{safe_name}", f"%{safe_name}"))
    row = cursor.fetchone()

    user_id = session.get('user_id')
    user_role = session.get('role')

    authorized = False
    if user_role == 'admin':
        authorized = True
    elif row:
        if user_role == 'officer':
            cursor.execute("SELECT id, department_id FROM officers WHERE user_id = ?", (user_id,))
            off_row = cursor.fetchone()
            if off_row and (off_row['id'] == row['assigned_officer_id'] or off_row['department_id'] == row['department_id']):
                authorized = True
        else:
            authorized = (
                user_id == row['citizen_id'] or
                user_id == row['officer_user_id'] or
                user_id == row['worker_user_id'] or
                user_id == row['proof_worker_user_id']
            )
    conn.close()

    if not authorized:
        return jsonify({'success': False, 'error': 'Unauthorized to view this evidence attachment.'}), 403

    filepath = os.path.join(UPLOAD_FOLDER, safe_name)
    if not os.path.isfile(filepath):
        return jsonify({'success': False, 'error': 'Evidence file not found on disk.'}), 404

    return send_from_directory(UPLOAD_FOLDER, safe_name)
