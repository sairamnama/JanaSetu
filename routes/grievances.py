"""
GramSeva - Grievance Management Routes
Handles public feeds, complaint registration, grievance details, status workflows,
department assignment, and priority escalation.
"""

import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from core.database import get_db_connection
from core.config import UPLOAD_FOLDER, allowed_file, validate_uploaded_file
from core.security import login_required, role_required, mask_text, mask_phone
from core.constants import (
    VALID_STATUSES, VALID_TRANSITIONS, CATEGORY_DEPARTMENT_MAP,
    validate_transition, record_status_history, apply_status_transition
)
from services.notification_service import send_notification, notify_admins

grievances_bp = Blueprint('grievances', __name__, url_prefix='/api')

@grievances_bp.route('/public-feed', methods=['GET'])
def get_public_feed():
    """Returns non-PII recent grievance cards for the public landing page."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT g.tracking_id, g.category, g.title, g.ward_number, g.location_landmark,
           g.priority, g.status, g.created_at
    FROM grievances g
    ORDER BY g.created_at DESC
    LIMIT 6
    ''')
    rows = cursor.fetchall()
    feed = [dict(r) for r in rows]
    conn.close()
    return jsonify({'success': True, 'feed': feed})

@grievances_bp.route('/grievances', methods=['GET'])
@login_required
def get_grievances():
    """Returns role-scoped list of grievances with multi-parameter filtering."""
    status = request.args.get('status')
    category = request.args.get('category')
    ward = request.args.get('ward')
    priority = request.args.get('priority')
    search = request.args.get('search', '').strip()
    scope = request.args.get('scope', 'auto')

    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
    SELECT g.*, 
           u.full_name as citizen_name, u.mobile as citizen_mobile,
           d.name as department_name, d.code as department_code,
           o_u.full_name as officer_name, o.designation as officer_designation,
           w_u.full_name as worker_name, w.skill_trade as worker_trade,
           f.star_rating, f.satisfaction,
           (SELECT assigned_at FROM worker_assignments wa WHERE wa.grievance_id = g.id ORDER BY wa.id DESC LIMIT 1) as assigned_at
    FROM grievances g
    LEFT JOIN users u ON g.citizen_id = u.id
    LEFT JOIN departments d ON g.department_id = d.id
    LEFT JOIN officers o ON g.assigned_officer_id = o.id
    LEFT JOIN users o_u ON o.user_id = o_u.id
    LEFT JOIN workers w ON g.assigned_worker_id = w.id
    LEFT JOIN users w_u ON w.user_id = w_u.id
    LEFT JOIN feedback f ON g.id = f.grievance_id
    WHERE 1=1
    '''
    params = []

    user_role = session.get('role')
    user_id = session.get('user_id')

    if user_role == 'citizen' or scope == 'my':
        query += " AND g.citizen_id = ?"
        params.append(user_id)
    elif user_role == 'worker':
        cursor.execute("SELECT id FROM workers WHERE user_id = ?", (user_id,))
        w_row = cursor.fetchone()
        if w_row:
            query += " AND g.assigned_worker_id = ?"
            params.append(w_row['id'])
        else:
            query += " AND 1=0"
    elif user_role == 'officer':
        cursor.execute("SELECT id, department_id FROM officers WHERE user_id = ?", (user_id,))
        off_info = cursor.fetchone()
        if off_info:
            query += " AND (g.assigned_officer_id = ? OR g.department_id = ?)"
            params.extend([off_info['id'], off_info['department_id']])
        else:
            query += " AND 1=0"

    if status and status != 'ALL':
        query += " AND g.status = ?"
        params.append(status)

    if category and category != 'ALL':
        query += " AND g.category = ?"
        params.append(category)

    if ward and ward != 'ALL':
        query += " AND g.ward_number = ?"
        params.append(ward)

    if priority and priority != 'ALL':
        query += " AND g.priority = ?"
        params.append(priority)

    if search:
        query += " AND (g.title LIKE ? OR g.description LIKE ? OR g.tracking_id LIKE ? OR g.location_landmark LIKE ?)"
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    query += " ORDER BY g.created_at DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]
    conn.close()

    return jsonify({'success': True, 'grievances': results, 'count': len(results)})

@grievances_bp.route('/grievances', methods=['POST'])
@login_required
@role_required(['citizen'])
def create_grievance():
    """Registers a new civic complaint submitted by an authenticated citizen."""
    data = request.get_json(silent=True) or request.form or {}
    title = (data.get('title') or '').strip()
    category = (data.get('category') or '').strip()
    description = (data.get('description') or '').strip()
    try:
        ward_number = int(data.get('ward_number')) if data.get('ward_number') is not None else None
    except (ValueError, TypeError):
        ward_number = None
    location_landmark = (data.get('location_landmark') or '').strip()
    priority = data.get('priority', 'Medium')

    if not title or not category or not description or not ward_number or not location_landmark:
        return jsonify({'success': False, 'error': 'Please provide all mandatory fields.'}), 400

    evidence_image = None
    if 'evidence_image' in request.files and request.files['evidence_image'].filename:
        file = request.files['evidence_image']
        is_valid, err_msg, file_info = validate_uploaded_file(file)
        if not is_valid:
            return jsonify({'success': False, 'error': f"Evidence file validation failed: {err_msg}"}), 400
        ext = file_info['extension']
        random_token = uuid.uuid4().hex
        filename = f"grv_{session['user_id']}_{random_token}.{ext}"
        file.seek(0)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        evidence_image = f"/api/uploads/{filename}"

    conn = get_db_connection()
    cursor = conn.cursor()

    year = datetime.now().year
    cursor.execute("SELECT COUNT(*) FROM grievances WHERE tracking_id LIKE ?", (f"GRV-{year}-%",))
    seq = cursor.fetchone()[0] + 101
    tracking_id = f"GRV-{year}-{seq:05d}"

    dept_code = CATEGORY_DEPARTMENT_MAP.get(category, 'GEN')
    cursor.execute("SELECT id FROM departments WHERE code = ?", (dept_code,))
    dept_row = cursor.fetchone()
    department_id = dept_row['id'] if dept_row else None

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
    INSERT INTO grievances (
        tracking_id, citizen_id, category, title, description,
        ward_number, location_landmark, priority, status, department_id,
        evidence_image, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'SUBMITTED', ?, ?, ?, ?)
    ''', (tracking_id, session['user_id'], category, title, description,
          ward_number, location_landmark, priority, department_id, evidence_image, now_str, now_str))

    grievance_id = cursor.lastrowid

    record_status_history(
        cursor=cursor,
        grievance_id=grievance_id,
        from_status=None,
        to_status='SUBMITTED',
        remarks='Grievance submitted by citizen via portal.',
        user_id=session['user_id'],
        user_role=session.get('role', 'citizen'),
        created_at=now_str
    )

    send_notification(
        cursor, session['user_id'], grievance_id,
        'Grievance Registered Successfully',
        f"Your complaint '{title}' has been registered with ID: {tracking_id}.", now_str
    )

    notify_admins(
        cursor, grievance_id,
        'New Civic Grievance',
        f"New complaint {tracking_id} in Ward {ward_number} ({category}).", now_str
    )

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f'Grievance registered successfully with ID: {tracking_id}',
        'tracking_id': tracking_id,
        'grievance_id': grievance_id
    })

@grievances_bp.route('/track/<tracking_id>', methods=['GET'])
@grievances_bp.route('/grievances/track/<tracking_id>', methods=['GET'])
def get_public_tracking(tracking_id):
    """
    Public Grievance Tracker API.
    Does NOT require authentication.
    Strictly sanitized to prevent PII exposure:
    - OMITTED: citizen phone, citizen email, citizen name, private address/landmark,
               worker/officer personal identifiers, internal notes, verification logs.
    - ALLOWED: tracking_id, category, title, status, created_at, basic timeline.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT g.id, g.tracking_id, g.category, g.title, g.status, g.created_at
    FROM grievances g
    WHERE g.tracking_id = ? OR (g.id = ? AND ? GLOB '[0-9]*')
    ''', (tracking_id, int(tracking_id) if str(tracking_id).isdigit() else 0, str(tracking_id)))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Grievance not found'}), 404

    grievance = dict(row)

    # Basic sanitized timeline (only status progression and date, no internal remarks/staff names)
    cursor.execute('''
    SELECT gu.to_status as status, gu.created_at
    FROM grievance_updates gu
    WHERE gu.grievance_id = ?
    ORDER BY gu.created_at ASC
    ''', (grievance['id'],))
    timeline_rows = cursor.fetchall()
    grievance['timeline'] = [{'status': r['status'], 'created_at': r['created_at']} for r in timeline_rows]

    # Don't expose internal db integer id in public tracking response
    grievance.pop('id', None)

    conn.close()
    return jsonify({'success': True, 'grievance': grievance})

@grievances_bp.route('/grievances/<id_or_tracking>', methods=['GET'])
@login_required
def get_grievance_detail(id_or_tracking):
    """
    Retrieves full grievance record, audit timeline, historical proofs, and verification attempts.
    Requires authentication. Role-based access control strictly enforced:
    - Citizen: own grievances only
    - Worker: assigned grievances only
    - Officer: authorized grievances only (assigned officer or same department)
    - Admin: system-wide access
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    sql = '''
    SELECT g.*, 
           u.full_name as citizen_name, u.mobile as citizen_mobile, u.email as citizen_email,
           d.name as department_name, d.code as department_code,
           o_u.full_name as officer_name, o.designation as officer_designation, o.badge_id as officer_badge,
           w_u.full_name as worker_name, w.skill_trade as worker_trade, w.badge_id as worker_badge
    FROM grievances g
    LEFT JOIN users u ON g.citizen_id = u.id
    LEFT JOIN departments d ON g.department_id = d.id
    LEFT JOIN officers o ON g.assigned_officer_id = o.id
    LEFT JOIN users o_u ON o.user_id = o_u.id
    LEFT JOIN workers w ON g.assigned_worker_id = w.id
    LEFT JOIN users w_u ON w.user_id = w_u.id
    WHERE ''' + ("g.id = ?" if id_or_tracking.isdigit() else "g.tracking_id = ?")

    cursor.execute(sql, (int(id_or_tracking) if id_or_tracking.isdigit() else id_or_tracking,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Grievance not found'}), 404

    grievance = dict(row)

    # Privacy Protection & Role Access Authorization Checks
    current_uid = session.get('user_id')
    current_role = session.get('role')

    # Security Guardrail: Citizen can only access own grievances
    if current_role == 'citizen':
        if current_uid != grievance.get('citizen_id'):
            conn.close()
            return jsonify({'success': False, 'error': 'Access denied: Citizens can only access their own grievances.'}), 403

    # Security Guardrail: Worker can only access assigned grievances
    elif current_role == 'worker':
        cursor.execute("SELECT id FROM workers WHERE user_id = ?", (current_uid,))
        w_row = cursor.fetchone()
        if not w_row or grievance.get('assigned_worker_id') != w_row['id']:
            conn.close()
            return jsonify({'success': False, 'error': 'Access denied: Workers can only access their assigned grievances.'}), 403

    # Security Guardrail: Officer can only access authorized grievances (assigned or within department)
    elif current_role == 'officer':
        cursor.execute("SELECT id, department_id FROM officers WHERE user_id = ?", (current_uid,))
        off_info = cursor.fetchone()
        if not off_info:
            conn.close()
            return jsonify({'success': False, 'error': 'Access denied: Officer record not found.'}), 403
        is_assigned = (grievance.get('assigned_officer_id') == off_info['id'])
        is_dept = (grievance.get('department_id') == off_info['department_id'])
        if not (is_assigned or is_dept):
            conn.close()
            return jsonify({'success': False, 'error': 'Access denied: Officers can only access grievances authorized for their department.'}), 403

    # Admin role: has system-wide access
    elif current_role == 'admin':
        pass
    else:
        conn.close()
        return jsonify({'success': False, 'error': 'Access denied: Unauthorized role.'}), 403

    # Fetch updates / timeline
    cursor.execute('''
    SELECT gu.*, u.full_name as updated_by_name, COALESCE(gu.user_role, u.role) as updated_by_role
    FROM grievance_updates gu
    JOIN users u ON gu.updated_by_user_id = u.id
    WHERE gu.grievance_id = ?
    ORDER BY gu.created_at ASC
    ''', (grievance['id'],))
    grievance['timeline'] = [dict(u) for u in cursor.fetchall()]

    # Fetch historical worker assignments
    cursor.execute('''
    SELECT wa.*, u.full_name as worker_name, w.skill_trade as worker_trade,
           ab.full_name as assigned_by_name, ab.role as assigned_by_role,
           d.name as department_name, d.code as department_code
    FROM worker_assignments wa
    JOIN workers w ON wa.worker_id = w.id
    JOIN users u ON w.user_id = u.id
    JOIN users ab ON wa.assigned_by_user_id = ab.id
    LEFT JOIN departments d ON wa.department_id = d.id
    WHERE wa.grievance_id = ?
    ORDER BY wa.assigned_at DESC
    ''', (grievance['id'],))
    grievance['worker_assignments'] = [dict(a) for a in cursor.fetchall()]

    # Fetch historical resolution proofs (preserving all versions/rework attempts)
    cursor.execute('''
    SELECT rp.*, u.full_name as worker_name, w.skill_trade as worker_trade, w.badge_id as worker_badge
    FROM resolution_proofs rp
    LEFT JOIN users u ON rp.worker_id = u.id
    LEFT JOIN workers w ON w.user_id = u.id
    WHERE rp.grievance_id = ?
    ORDER BY rp.proof_version DESC, rp.created_at DESC
    ''', (grievance['id'],))
    proofs_list = []
    for p in cursor.fetchall():
        pd = dict(p)
        pd['description'] = pd.get('completion_notes')
        proofs_list.append(pd)
    grievance['resolution_proofs'] = proofs_list

    # Fetch historical officer verifications
    cursor.execute('''
    SELECT ov.*, u.full_name as officer_name
    FROM officer_verifications ov
    JOIN users u ON ov.officer_id = u.id
    WHERE ov.grievance_id = ?
    ORDER BY ov.created_at DESC
    ''', (grievance['id'],))
    grievance['officer_verifications'] = [dict(ov) for ov in cursor.fetchall()]

    # Fetch historical citizen verifications
    cursor.execute('''
    SELECT cv.*, u.full_name as citizen_name
    FROM citizen_verifications cv
    JOIN users u ON cv.citizen_id = u.id
    WHERE cv.grievance_id = ?
    ORDER BY cv.attempt_number DESC, cv.id DESC
    ''', (grievance['id'],))
    grievance['citizen_verifications'] = [dict(cv) for cv in cursor.fetchall()]

    # Fetch all verification attempts
    cursor.execute('''
    SELECT va.*, u.full_name as attempted_by_name
    FROM verification_attempts va
    LEFT JOIN users u ON va.attempted_by_user_id = u.id
    WHERE va.grievance_id = ?
    ORDER BY va.attempted_at DESC
    ''', (grievance['id'],))
    grievance['verification_attempts'] = [dict(va) for va in cursor.fetchall()]

    # Fetch feedback if available
    cursor.execute("SELECT * FROM feedback WHERE grievance_id = ?", (grievance['id'],))
    fb_row = cursor.fetchone()
    grievance['feedback'] = dict(fb_row) if fb_row else None

    conn.close()
    return jsonify({'success': True, 'grievance': grievance})

@grievances_bp.route('/grievances/<int:grievance_id>/status', methods=['PUT', 'POST'])
@login_required
@role_required(['admin', 'officer', 'worker'])
def update_grievance_status(grievance_id):
    """Enforces state transitions and role-based lifecycle progression."""
    data = request.get_json(silent=True) or request.form or {}
    new_status = data.get('status')
    remarks = data.get('remarks', '').strip()
    resolution_notes = data.get('resolution_notes', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM grievances WHERE id = ?", (grievance_id,))
    grievance = cursor.fetchone()

    if not grievance:
        conn.close()
        return jsonify({'success': False, 'error': 'Grievance not found'}), 404

    old_status = grievance['status']
    user_role = session.get('role')
    user_id = session.get('user_id')

    # Security Guardrail: A worker attempting to modify another worker's grievance must be denied
    worker_record = None
    if user_role == 'worker':
        cursor.execute("SELECT id FROM workers WHERE user_id = ?", (user_id,))
        worker_record = cursor.fetchone()
        if not worker_record or grievance['assigned_worker_id'] != worker_record['id']:
            conn.close()
            return jsonify({'success': False, 'error': 'Access denied: You are not assigned to this grievance.'}), 403

    is_valid, err_msg, status_code = validate_transition(
        current_status=old_status,
        new_status=new_status,
        user_role=user_role,
        remarks=remarks,
        resolution_notes=resolution_notes
    )

    if not is_valid:
        conn.close()
        return jsonify({'success': False, 'error': err_msg}), status_code

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    apply_status_transition(
        cursor=cursor,
        grievance_id=grievance_id,
        from_status=old_status,
        to_status=new_status,
        remarks=remarks,
        user_id=user_id,
        user_role=user_role,
        resolution_notes=resolution_notes,
        now_str=now_str
    )

    # Sync worker_assignments table if moving to IN_PROGRESS
    if user_role == 'worker' and worker_record and new_status == 'IN_PROGRESS':
        cursor.execute('''
        UPDATE worker_assignments
        SET assignment_status = 'IN_PROGRESS'
        WHERE grievance_id = ? AND worker_id = ? AND assignment_status = 'ASSIGNED'
        ''', (grievance_id, worker_record['id']))

    send_notification(
        cursor, grievance['citizen_id'], grievance_id,
        f"Status Update: {new_status}",
        f"Your grievance {grievance['tracking_id']} status updated to {new_status}. Official remarks: '{remarks}'", now_str
    )

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f'Status updated to {new_status} successfully.',
        'from_status': old_status,
        'to_status': new_status
    })

@grievances_bp.route('/status', methods=['POST', 'PUT'])
@login_required
@role_required(['admin', 'officer', 'worker'])
def direct_status_update():
    """Alternative status transition endpoint supporting direct POST/PUT /status requests."""
    data = request.get_json(silent=True) or request.form or {}
    grievance_id = data.get('grievance_id') or data.get('id')
    if not grievance_id:
        return jsonify({'success': False, 'error': 'Grievance ID is required.'}), 400
    try:
        gid = int(grievance_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid grievance ID format.'}), 400
    return update_grievance_status(gid)


@grievances_bp.route('/grievances/<int:grievance_id>/eligible-workers', methods=['GET'])
@login_required
@role_required(['admin', 'officer'])
def get_grievance_eligible_workers(grievance_id):
    """Returns matching and evaluated workers for a grievance with points and workload."""
    from services.assignment_service import get_eligible_workers
    from core.config import MIN_ASSIGNMENT_LOYALTY_POINTS
    dept_id = request.args.get('department_id')
    try:
        dept_id = int(dept_id) if dept_id else None
    except (ValueError, TypeError):
        dept_id = None
    workers = get_eligible_workers(grievance_id=grievance_id, department_id=dept_id)
    return jsonify({
        'success': True,
        'workers': workers,
        'min_points_required': MIN_ASSIGNMENT_LOYALTY_POINTS
    })

@grievances_bp.route('/grievances/<int:grievance_id>/assign', methods=['PUT'])
@login_required
@role_required(['admin', 'officer'])
def assign_grievance(grievance_id):
    """Assigns department, supervising officer, and field technician to a grievance."""
    data = request.json or {}
    department_id = data.get('department_id')
    assigned_officer_id = data.get('assigned_officer_id')
    assigned_worker_id = data.get('assigned_worker_id')
    remarks = data.get('remarks', 'Assigned by Panchayat Administration').strip()

    user_role = session.get('role')
    user_id = session.get('user_id')

    # If worker is specified, use unified assignment service enforcing eligibility rules
    if assigned_worker_id:
        from services.assignment_service import assign_worker_to_grievance
        try:
            w_id = int(assigned_worker_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid worker ID format.'}), 400

        try:
            d_id = int(department_id) if department_id else None
        except (ValueError, TypeError):
            d_id = None

        try:
            o_id = int(assigned_officer_id) if assigned_officer_id else None
        except (ValueError, TypeError):
            o_id = None

        ok, msg, res_data, status_code = assign_worker_to_grievance(
            grievance_id=grievance_id,
            worker_id=w_id,
            department_id=d_id,
            officer_id=o_id,
            remarks=remarks,
            admin_user_id=user_id,
            admin_role=user_role
        )
        if not ok:
            return jsonify({'success': False, 'error': msg}), status_code

        return jsonify({
            'success': True,
            'message': msg,
            'data': res_data
        }), 200

    # Fallback for department/officer-only assignment
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM grievances WHERE id = ?", (grievance_id,))
    grievance = cursor.fetchone()

    if not grievance:
        conn.close()
        return jsonify({'success': False, 'error': 'Grievance not found'}), 404

    if user_role == 'officer':
        cursor.execute("SELECT id, department_id FROM officers WHERE user_id = ?", (user_id,))
        off_info = cursor.fetchone()
        if off_info:
            if not department_id:
                department_id = grievance['department_id'] or off_info['department_id']
            if not assigned_officer_id:
                assigned_officer_id = grievance['assigned_officer_id'] or off_info['id']

    old_status = grievance['status']
    new_status = 'ASSIGNED' if old_status in ('SUBMITTED', 'UNDER_REVIEW', 'ACCEPTED', 'REWORK_REQUIRED', 'REOPENED') else old_status

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
    UPDATE grievances 
    SET department_id = COALESCE(?, department_id),
        assigned_officer_id = COALESCE(?, assigned_officer_id),
        status = ?, updated_at = ?
    WHERE id = ?
    ''', (department_id, assigned_officer_id, new_status, now_str, grievance_id))

    record_status_history(
        cursor=cursor,
        grievance_id=grievance_id,
        from_status=old_status,
        to_status=new_status,
        remarks=f"Department/Officer assigned: {remarks}",
        user_id=user_id,
        user_role=user_role,
        created_at=now_str
    )

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': 'Grievance departmental assignment updated successfully.'
    })

    return jsonify({'success': True, 'message': 'Grievance assignment updated successfully.'})

@grievances_bp.route('/grievances/<int:grievance_id>/assign-worker', methods=['POST'])
@login_required
@role_required(['officer', 'admin'])
def assign_worker_to_grievance(grievance_id):
    """Allows an officer or admin to assign a grievance directly to a field worker."""
    data = request.json or {}
    worker_id = data.get('worker_id') or data.get('assigned_worker_id')
    remarks = data.get('remarks', 'Assigned to field worker by officer.').strip()

    if not worker_id:
        return jsonify({'success': False, 'error': 'Worker ID is required.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM grievances WHERE id = ?", (grievance_id,))
    grievance = cursor.fetchone()

    if not grievance:
        conn.close()
        return jsonify({'success': False, 'error': 'Grievance not found'}), 404

    cursor.execute('''
    SELECT w.id, w.department_id, u.full_name as worker_name, w.user_id as worker_user_id
    FROM workers w
    JOIN users u ON w.user_id = u.id
    WHERE w.id = ?
    ''', (worker_id,))
    worker = cursor.fetchone()
    if not worker:
        conn.close()
        return jsonify({'success': False, 'error': 'Field worker not found.'}), 404

    old_status = grievance['status']
    if old_status in ('SUBMITTED', 'UNDER_REVIEW'):
        conn.close()
        return jsonify({
            'success': False,
            'error': f"Cannot assign grievance in '{old_status}' state. Grievance must be reviewed and accepted before assignment."
        }), 400

    new_status = 'ASSIGNED' if old_status in ('ACCEPTED', 'REWORK_REQUIRED', 'REOPENED') else old_status
    user_role = session.get('role')
    user_id = session.get('user_id')
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    dept_id = grievance['department_id'] or worker['department_id']

    if new_status != old_status:
        is_valid, err_msg, status_code = validate_transition(
            current_status=old_status,
            new_status=new_status,
            user_role=user_role,
            remarks=remarks
        )
        if not is_valid:
            conn.close()
            return jsonify({'success': False, 'error': err_msg}), status_code

    cursor.execute('''
    UPDATE grievances
    SET assigned_worker_id = ?, department_id = ?, status = ?, updated_at = ?
    WHERE id = ?
    ''', (worker['id'], dept_id, new_status, now_str, grievance_id))

    cursor.execute('''
    UPDATE worker_assignments
    SET assignment_status = 'REASSIGNED'
    WHERE grievance_id = ? AND assignment_status IN ('ASSIGNED', 'IN_PROGRESS', 'REWORK_REQUIRED') AND worker_id != ?
    ''', (grievance_id, worker['id']))

    cursor.execute('''
    INSERT INTO worker_assignments (
        grievance_id, worker_id, department_id, assigned_by_user_id, assigned_at, assignment_status
    ) VALUES (?, ?, ?, ?, ?, 'ASSIGNED')
    ''', (grievance_id, worker['id'], dept_id, user_id, now_str))

    record_status_history(
        cursor=cursor,
        grievance_id=grievance_id,
        from_status=old_status,
        to_status=new_status,
        remarks=f"Assigned to field worker {worker['worker_name']}: {remarks}",
        user_id=user_id,
        user_role=user_role,
        created_at=now_str
    )

    send_notification(
        cursor, worker['worker_user_id'], grievance_id,
        'New Field Assignment',
        f"You have been assigned to remediate grievance {grievance['tracking_id']}.", now_str
    )
    send_notification(
        cursor, grievance['citizen_id'], grievance_id,
        'Worker Assigned',
        f"Field worker {worker['worker_name']} has been assigned to your grievance {grievance['tracking_id']}.", now_str
    )

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f"Assigned to worker {worker['worker_name']} successfully.",
        'assigned_worker_id': worker['id'],
        'status': new_status
    })


@grievances_bp.route('/grievances/<int:grievance_id>/priority', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_priority(grievance_id):
    """Updates the urgency priority level of a civic ticket."""
    priority = (request.json or {}).get('priority')
    if priority not in ('Low', 'Medium', 'High'):
        return jsonify({'success': False, 'error': 'Invalid priority level'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE grievances SET priority = ?, updated_at = ? WHERE id = ?",
                   (priority, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), grievance_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f'Priority updated to {priority}.'})
