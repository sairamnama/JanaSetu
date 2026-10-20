"""
GramSeva - Field Worker Remediation Routes
Handles field worker task remediation, completion notes, and resolution proof uploads.
"""

import os
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from core.database import get_db_connection
from core.config import UPLOAD_FOLDER, validate_uploaded_file
from core.security import login_required, role_required
from core.constants import validate_transition, apply_status_transition
from services.notification_service import send_notification

worker_bp = Blueprint('worker', __name__, url_prefix='/api')

@worker_bp.route('/grievances/<int:grievance_id>/complete-work', methods=['POST'])
@login_required
@role_required(['worker', 'officer', 'admin'])
def worker_complete_work(grievance_id):
    """
    Worker marks remediation as complete:
    - Sets status to WORK_COMPLETED (STRICTLY NEVER RESOLVED)
    - Validates file type, MIME type, size, content magic bytes
    - Uses randomized filenames
    - Records persistent resolution proof with versioning & audit metadata
    """
    completion_notes = (request.form.get('completion_notes') or request.form.get('description') or '').strip()
    remarks = request.form.get('remarks', 'Field work completed with proof attachment.').strip()
    if not remarks:
        remarks = 'Field work completed with proof attachment.'

    location_coords = (request.form.get('location_coords') or request.form.get('location') or '').strip() or None
    completion_timestamp = request.form.get('completion_timestamp', '').strip()

    if not completion_notes:
        return jsonify({'success': False, 'error': 'Work completion description is mandatory.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM grievances WHERE id = ?", (grievance_id,))
    grievance = cursor.fetchone()

    if not grievance:
        conn.close()
        return jsonify({'success': False, 'error': 'Grievance not found'}), 404

    # Security Guardrail: A worker attempting to complete another worker's grievance must be denied
    w_row = None
    if session.get('role') == 'worker':
        cursor.execute("SELECT id FROM workers WHERE user_id = ?", (session['user_id'],))
        w_row = cursor.fetchone()
        if not w_row or grievance['assigned_worker_id'] != w_row['id']:
            conn.close()
            return jsonify({'success': False, 'error': 'Access denied: You are not assigned to this grievance.'}), 403

    # Enforce workflow state machine: completion allowed from active/rework states
    if grievance['status'] not in ('IN_PROGRESS', 'REWORK_REQUIRED', 'REOPENED', 'ESCALATED'):
        conn.close()
        return jsonify({
            'success': False,
            'error': f"Work completion can only be submitted from IN_PROGRESS, REWORK_REQUIRED, REOPENED, or ESCALATED (Current: {grievance['status']})."
        }), 400

    if 'proof_file' not in request.files:
        conn.close()
        return jsonify({'success': False, 'error': 'Resolution proof file (photo/evidence) is required.'}), 400

    file = request.files['proof_file']
    is_valid, err_msg, file_info = validate_uploaded_file(file)
    if not is_valid:
        conn.close()
        return jsonify({'success': False, 'error': f"Resolution proof validation failed: {err_msg}"}), 400

    # Optional additional supporting evidence
    additional_proof_url = None
    add_file_info = None
    if 'additional_evidence' in request.files and request.files['additional_evidence'].filename:
        add_file = request.files['additional_evidence']
        is_add_valid, add_err_msg, add_file_info = validate_uploaded_file(add_file)
        if not is_add_valid:
            conn.close()
            return jsonify({'success': False, 'error': f"Additional evidence validation failed: {add_err_msg}"}), 400

    # Save primary proof file with unguessable randomized filename
    ext = file_info['extension']
    random_token = uuid.uuid4().hex
    filename = f"proof_{grievance_id}_{session['user_id']}_{random_token}.{ext}"
    file.seek(0)
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    proof_url = f"/api/uploads/{filename}"

    # Save optional additional evidence if uploaded
    if add_file_info:
        add_ext = add_file_info['extension']
        add_filename = f"proof_add_{grievance_id}_{session['user_id']}_{uuid.uuid4().hex}.{add_ext}"
        add_file.seek(0)
        add_file.save(os.path.join(UPLOAD_FOLDER, add_filename))
        additional_proof_url = f"/api/uploads/{add_filename}"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    upload_timestamp = completion_timestamp if completion_timestamp else now_str

    # Compute proof version/attempt (never overwrite previous submissions)
    cursor.execute("SELECT COUNT(*) FROM resolution_proofs WHERE grievance_id = ?", (grievance_id,))
    proof_count = cursor.fetchone()[0]
    proof_version = proof_count + 1

    # Structured metadata for file & remediation verification
    metadata_dict = {
        'original_filename': file_info['original_filename'],
        'clean_filename': file_info['clean_filename'],
        'file_size': file_info['size'],
        'mime_type': file_info['mime_type'],
        'sha256': file_info['sha256'],
        'completion_timestamp': upload_timestamp,
        'location': location_coords,
        'has_additional_evidence': bool(additional_proof_url),
        'additional_evidence_name': add_file_info['original_filename'] if add_file_info else None
    }

    # 1. Insert into resolution_proofs (Persistent historical archive)
    cursor.execute('''
    INSERT INTO resolution_proofs (
        grievance_id, worker_id, proof_file, completion_notes, remarks,
        location_coords, additional_evidence, metadata, proof_version, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        grievance_id, session['user_id'], proof_url, completion_notes, remarks,
        location_coords, additional_proof_url, json.dumps(metadata_dict), proof_version, upload_timestamp
    ))
    proof_id = cursor.lastrowid

    # 2. Update grievance status to WORK_COMPLETED via central transition engine
    old_status = grievance['status']
    new_status = 'WORK_COMPLETED'
    is_valid, err_msg, status_code = validate_transition(
        current_status=old_status,
        new_status=new_status,
        user_role=session.get('role', 'worker'),
        remarks=f"Work Completed: {remarks}"
    )
    if not is_valid:
        conn.close()
        return jsonify({'success': False, 'error': err_msg}), status_code

    apply_status_transition(
        cursor=cursor,
        grievance_id=grievance_id,
        from_status=old_status,
        to_status=new_status,
        remarks=f"Work Completed (Proof Attempt #{proof_version}): {remarks}",
        user_id=session['user_id'],
        user_role=session.get('role', 'worker'),
        resolution_notes=completion_notes,
        now_str=now_str
    )

    # 3. Update worker_assignments audit table
    if w_row:
        cursor.execute('''
        UPDATE worker_assignments
        SET assignment_status = 'COMPLETED'
        WHERE grievance_id = ? AND worker_id = ?
        ''', (grievance_id, w_row['id']))

    # 4. Notify Officer & Admin to review proof
    if grievance['assigned_officer_id']:
        cursor.execute("SELECT user_id FROM officers WHERE id = ?", (grievance['assigned_officer_id'],))
        off = cursor.fetchone()
        if off:
            send_notification(
                cursor, off['user_id'], grievance_id,
                'Resolution Proof Ready for Review',
                f"Worker submitted completion proof (Attempt #{proof_version}) for {grievance['tracking_id']}. Please review.", now_str
            )

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f'Resolution proof (Attempt #{proof_version}) recorded successfully. Status updated to WORK_COMPLETED.',
        'proof_id': proof_id,
        'proof_version': proof_version,
        'status': new_status
    })

# ==========================================
# WORKER LOYALTY POINTS ENDPOINTS
# ==========================================

@worker_bp.route('/worker/loyalty-points', methods=['GET'])
@worker_bp.route('/worker/points', methods=['GET'])
@login_required
@role_required(['worker'])
def get_current_worker_points():
    """
    Returns the authenticated worker's current loyalty points balance and transaction history.
    Workers can only view their own points and cannot access another worker's ledger.
    """
    from services.points_service import get_worker_points_summary, get_worker_transactions

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM workers WHERE user_id = ?", (session['user_id'],))
    w_row = cursor.fetchone()
    conn.close()

    if not w_row:
        return jsonify({'success': False, 'error': 'No field worker profile found for this account.'}), 404

    worker_id = w_row['id']
    summary = get_worker_points_summary(worker_id)
    transactions = get_worker_transactions(worker_id)

    return jsonify({
        'success': True,
        'worker': summary,
        'transactions': transactions
    })

@worker_bp.route('/admin/workers/<int:worker_id>/points', methods=['GET'])
@login_required
@role_required(['admin', 'officer'])
def get_worker_points_for_admin(worker_id):
    """
    Allows authorized administrators/officers to view a worker's loyalty points and transaction history.
    """
    from services.points_service import get_worker_points_summary, get_worker_transactions

    summary = get_worker_points_summary(worker_id)
    if not summary:
        return jsonify({'success': False, 'error': f'Worker with ID {worker_id} not found.'}), 404

    transactions = get_worker_transactions(worker_id)
    return jsonify({
        'success': True,
        'worker': summary,
        'transactions': transactions
    })

@worker_bp.route('/admin/points-transactions', methods=['GET'])
@login_required
@role_required(['admin', 'officer'])
def get_all_points_audit_log():
    """
    Allows authorized administrators/officers to view system-wide loyalty points transaction history.
    """
    from services.points_service import get_all_points_transactions
    limit = request.args.get('limit', 100)
    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 100

    transactions = get_all_points_transactions(limit=limit)
    return jsonify({
        'success': True,
        'transactions': transactions
    })

@worker_bp.route('/admin/workers/<int:worker_id>/adjust-points', methods=['POST'])
@login_required
@role_required(['admin', 'officer'])
def admin_adjust_worker_points(worker_id):
    """
    Allows authorized administrators/officers to manually add or deduct loyalty points for a worker.
    Enforces mandatory reason, valid delta, balance integrity, and transaction audit recording.
    """
    from services.points_service import adjust_worker_points

    data = request.json or request.form or {}
    points_raw = data.get('points') if data.get('points') is not None else data.get('amount')
    action = (data.get('action') or '').strip().lower()
    reason = (data.get('reason') or '').strip()

    if points_raw is None or points_raw == '':
        return jsonify({'success': False, 'error': 'Points adjustment amount is required.'}), 400

    try:
        points_val = int(points_raw)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Points value must be a valid integer.'}), 400

    if points_val == 0:
        return jsonify({'success': False, 'error': 'Points adjustment amount cannot be 0.'}), 400

    if action == 'deduct':
        points_val = -abs(points_val)
    elif action == 'add':
        points_val = abs(points_val)

    if not reason:
        return jsonify({'success': False, 'error': 'A mandatory reason is required for adjusting loyalty points.'}), 400

    actor_id = session.get('user_id')
    actor_role = session.get('role', 'admin').title()
    actor_name = session.get('full_name') or session.get('username') or 'Admin'
    actor_source = f"{actor_role} ({actor_name})"

    ok, msg, tx_record = adjust_worker_points(
        worker_id=worker_id,
        points_delta=points_val,
        reason=reason,
        actor_id=actor_id,
        actor_source=actor_source
    )

    if not ok:
        return jsonify({'success': False, 'error': msg}), 400

    return jsonify({
        'success': True,
        'message': msg,
        'transaction': tx_record,
        'new_balance': tx_record['new_balance']
    })

# ==========================================
# WORKER ASSIGNMENT ACCEPT / REJECT ENDPOINTS
# ==========================================

@worker_bp.route('/worker/grievances/<int:grievance_id>/accept', methods=['POST'])
@worker_bp.route('/worker/assignments/<int:grievance_id>/accept', methods=['POST'])
@login_required
@role_required(['worker'])
def worker_accept_task(grievance_id):
    """
    Worker accepts an assigned task.
    Transitions grievance from ASSIGNED -> ACCEPTED and updates assignment status.
    """
    from services.assignment_service import worker_accept_assignment

    ok, msg, data, status_code = worker_accept_assignment(
        grievance_id=grievance_id,
        worker_user_id=session['user_id']
    )
    if not ok:
        return jsonify({'success': False, 'error': msg}), status_code

    return jsonify({
        'success': True,
        'message': msg,
        'data': data
    }), 200

@worker_bp.route('/worker/grievances/<int:grievance_id>/reject', methods=['POST'])
@worker_bp.route('/worker/assignments/<int:grievance_id>/reject', methods=['POST'])
@login_required
@role_required(['worker'])
def worker_reject_task(grievance_id):
    """
    Worker rejects an assigned task with a mandatory reason.
    Releases grievance back to SUBMITTED for reassignment, notifies admins,
    and deducts the configurable rejection penalty (-5 points) exactly once.
    """
    from services.assignment_service import worker_reject_assignment

    req_data = request.json or request.form or {}
    reason = (req_data.get('reason') or req_data.get('rejection_reason') or '').strip()

    if not reason:
        return jsonify({'success': False, 'error': 'A mandatory rejection reason is required.'}), 400

    ok, msg, data, status_code = worker_reject_assignment(
        grievance_id=grievance_id,
        worker_user_id=session['user_id'],
        rejection_reason=reason
    )
    if not ok:
        return jsonify({'success': False, 'error': msg}), status_code

    return jsonify({
        'success': True,
        'message': msg,
        'data': data
    }), 200
