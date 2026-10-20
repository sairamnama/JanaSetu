"""
GramSeva - Department, Officer & Field Worker Roster Routes
Provides rosters of Panchayat civic departments, supervising officers, and skilled field workers.
"""

from flask import Blueprint, request, jsonify
from core.database import get_db_connection

departments_bp = Blueprint('departments', __name__, url_prefix='/api')

@departments_bp.route('/departments', methods=['GET'])
def get_departments():
    """Returns list of all active Panchayat departments."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM departments ORDER BY name ASC")
    departments = [dict(d) for d in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'departments': departments})

@departments_bp.route('/officers', methods=['GET'])
def get_officers():
    """Returns field officers optionally filtered by department with active ticket load counts."""
    dept_id = request.args.get('department_id')
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
    SELECT o.id, o.designation, o.badge_id,
           u.id as user_id, u.full_name, u.mobile, u.email,
           d.id as department_id, d.name as department_name, d.code as department_code,
           (SELECT COUNT(*) FROM grievances g WHERE g.assigned_officer_id = o.id AND g.status IN ('ASSIGNED', 'IN_PROGRESS', 'WORK_COMPLETED', 'OFFICER_VERIFICATION')) as active_tickets
    FROM officers o
    JOIN users u ON o.user_id = u.id
    JOIN departments d ON o.department_id = d.id
    '''
    params = []
    if dept_id:
        query += " WHERE o.department_id = ?"
        params.append(dept_id)

    query += " ORDER BY u.full_name ASC"
    cursor.execute(query, params)
    officers = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify({'success': True, 'officers': officers})

@departments_bp.route('/workers', methods=['GET'])
def get_workers():
    """Returns skilled field workers and technicians filtered optionally by department."""
    dept_id = request.args.get('department_id')
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
    SELECT w.id, w.skill_trade, w.badge_id, COALESCE(w.loyalty_points, 100) as loyalty_points,
           u.id as user_id, u.full_name, u.mobile,
           d.id as department_id, d.name as department_name, d.code as department_code,
           (SELECT COUNT(*) FROM grievances g WHERE g.assigned_worker_id = w.id AND g.status IN ('ASSIGNED', 'IN_PROGRESS', 'REWORK_REQUIRED')) as active_tickets
    FROM workers w
    JOIN users u ON w.user_id = u.id
    JOIN departments d ON w.department_id = d.id
    '''
    params = []
    if dept_id:
        query += " WHERE w.department_id = ?"
        params.append(dept_id)

    query += " ORDER BY u.full_name ASC"
    cursor.execute(query, params)
    workers = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify({'success': True, 'workers': workers})
