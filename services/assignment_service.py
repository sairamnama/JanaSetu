"""
GramSeva - Grievance Assignment & Remediation Workflow Service
Handles matching eligible workers by skills, active status, minimum loyalty points,
workload distribution, assignment dispatch, worker acceptance, and rejection with penalty.
"""

import threading
from datetime import datetime
from typing import Tuple, Dict, Any, List, Optional
from core.database import get_db_connection
from core.config import (
    MIN_ASSIGNMENT_LOYALTY_POINTS,
    REJECTED_ASSIGNMENT_PENALTY_POINTS
)
from services.points_service import deduct_rejected_assignment_points
from services.notification_service import send_notification, notify_admins
from core.constants import record_status_history

_assignment_lock = threading.Lock()

# Skill to Department and Category keyword associations
CATEGORY_SKILL_KEYWORDS = {
    'WAT': ['plumb', 'pipe', 'water', 'pump', 'borewell', 'valve', 'filter'],
    'ELEC': ['electric', 'lineman', 'wire', 'cable', 'pole', 'transformer', 'fuse', 'light'],
    'SAN': ['sanit', 'waste', 'drain', 'sweep', 'clean', 'garbage', 'chlorin'],
    'ROAD': ['road', 'civil', 'engineer', 'cc', 'tar', 'culvert', 'mason', 'concrete'],
    'HLTH': ['health', 'fog', 'medical', 'vector', 'chlorin'],
    'EDU': ['school', 'anganwadi', 'infra'],
    'GEN': ['pension', 'welfare', 'market', 'general']
}

def is_worker_skill_matched(worker_dept_code: str, worker_skill: str, grievance_cat: str, grievance_dept_code: str = None) -> bool:
    """Validates whether a worker's trade or department matches the grievance requirements."""
    if grievance_dept_code and worker_dept_code == grievance_dept_code:
        return True

    skill_lower = (worker_skill or "").lower()
    cat_lower = (grievance_cat or "").lower()

    # Department code match
    if worker_dept_code:
        keywords = CATEGORY_SKILL_KEYWORDS.get(worker_dept_code.upper(), [])
        if any(kw in cat_lower for kw in keywords) or any(kw in skill_lower for kw in keywords):
            return True

    return False

def get_eligible_workers(grievance_id: Optional[int] = None, department_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Returns field workers evaluated for eligibility against a grievance or department:
    - Work type / skill match
    - Active account status
    - Configurable minimum Loyalty Points (default: 60)
    - Current workload (active task count)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    grievance = None
    if grievance_id:
        cursor.execute("SELECT id, category, department_id, tracking_id FROM grievances WHERE id = ?", (grievance_id,))
        g_row = cursor.fetchone()
        if g_row:
            grievance = dict(g_row)
            if not department_id and grievance.get('department_id'):
                department_id = grievance['department_id']

    query = '''
    SELECT w.id, w.user_id, w.department_id, w.skill_trade, w.badge_id,
           COALESCE(w.loyalty_points, 100) as loyalty_points,
           COALESCE(w.is_active, 1) as is_active,
           u.full_name, u.mobile, u.ward_number,
           d.name as department_name, d.code as department_code,
           (
               SELECT COUNT(*) FROM grievances g
               WHERE g.assigned_worker_id = w.id
                 AND g.status IN ('ASSIGNED', 'ACCEPTED', 'IN_PROGRESS', 'REWORK_REQUIRED')
           ) as active_workload
    FROM workers w
    JOIN users u ON w.user_id = u.id
    JOIN departments d ON w.department_id = d.id
    WHERE u.role = 'worker'
    '''
    params = []
    if department_id:
        query += " AND w.department_id = ?"
        params.append(department_id)

    query += " ORDER BY active_workload ASC, loyalty_points DESC, u.full_name ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    min_points = MIN_ASSIGNMENT_LOYALTY_POINTS
    result = []

    for r in rows:
        w = dict(r)
        ineligibility_reasons = []

        # 1. Loyalty Points Check
        has_min_points = (w['loyalty_points'] >= min_points)
        if not has_min_points:
            ineligibility_reasons.append(
                f"Loyalty points ({w['loyalty_points']}) below required threshold of {min_points} pts"
            )

        # 2. Skill & Department Matching
        skill_matched = True
        if grievance:
            skill_matched = is_worker_skill_matched(
                worker_dept_code=w['department_code'],
                worker_skill=w['skill_trade'],
                grievance_cat=grievance.get('category', ''),
                grievance_dept_code=None
            )
            if not skill_matched and department_id and w['department_id'] != department_id:
                ineligibility_reasons.append("Trade/department does not match grievance category")

        # 3. Active status
        is_active = bool(w.get('is_active', 1))
        if not is_active:
            ineligibility_reasons.append("Worker account is inactive or on leave")

        is_eligible = (has_min_points and skill_matched and is_active)

        w['is_eligible'] = is_eligible
        w['ineligibility_reasons'] = ineligibility_reasons
        w['min_points_required'] = min_points
        result.append(w)

    return result

def assign_worker_to_grievance(
    grievance_id: int,
    worker_id: int,
    department_id: Optional[int] = None,
    officer_id: Optional[int] = None,
    remarks: str = "Assigned by administration",
    admin_user_id: int = 1,
    admin_role: str = "admin"
) -> Tuple[bool, str, Optional[Dict[str, Any]], int]:
    """
    Assigns a grievance to an eligible field worker.
    Enforces minimum loyalty points, skill/dept matching, prevents duplicate active assignments,
    and updates assignment audit records.
    """
    clean_remarks = (remarks or "Assigned by administration").strip()

    with _assignment_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch grievance
        cursor.execute("SELECT * FROM grievances WHERE id = ?", (grievance_id,))
        g_row = cursor.fetchone()
        if not g_row:
            conn.close()
            return False, f"Grievance (ID: {grievance_id}) not found.", None, 404
        grievance = dict(g_row)

        # 2. Fetch worker
        cursor.execute('''
        SELECT w.id, w.user_id, w.department_id, w.skill_trade, w.badge_id,
               COALESCE(w.loyalty_points, 100) as loyalty_points,
               COALESCE(w.is_active, 1) as is_active,
               u.full_name as worker_name, d.code as department_code, d.name as department_name
        FROM workers w
        JOIN users u ON w.user_id = u.id
        JOIN departments d ON w.department_id = d.id
        WHERE w.id = ?
        ''', (worker_id,))
        w_row = cursor.fetchone()
        if not w_row:
            conn.close()
            return False, f"Specified field worker (ID: {worker_id}) not found.", None, 404
        worker = dict(w_row)

        # 3. Check Active Status
        if not worker.get('is_active', 1):
            conn.close()
            return False, f"Worker {worker['worker_name']} is currently marked inactive and cannot be assigned tasks.", None, 400

        # 4. Check for Duplicate Active Assignment
        if grievance.get('assigned_worker_id') == worker_id and grievance['status'] in ('ASSIGNED', 'ACCEPTED', 'IN_PROGRESS'):
            conn.close()
            return False, f"Duplicate assignment: Grievance is already actively assigned to {worker['worker_name']}.", None, 400

        # Check existing active assignment in worker_assignments
        cursor.execute('''
        SELECT id, worker_id, assignment_status
        FROM worker_assignments
        WHERE grievance_id = ? AND assignment_status IN ('ASSIGNED', 'ACCEPTED')
        ''', (grievance_id,))
        active_assignment = cursor.fetchone()
        if active_assignment and active_assignment['worker_id'] == worker_id:
            conn.close()
            return False, "Duplicate active assignment: Worker already has an active pending assignment for this grievance.", None, 400

        # 5. Loyalty Points Eligibility Check
        min_points = MIN_ASSIGNMENT_LOYALTY_POINTS
        if worker['loyalty_points'] < min_points:
            conn.close()
            return False, (
                f"Worker {worker['worker_name']} ({worker['badge_id']}) is ineligible for assignment: "
                f"Loyalty points ({worker['loyalty_points']}) are below the required minimum of {min_points} points."
            ), None, 400

        # 5. Determine Department and Officer
        target_dept_id = department_id or grievance.get('department_id') or worker['department_id']
        target_officer_id = officer_id or grievance.get('assigned_officer_id')

        # 6. Apply Status Transition
        old_status = grievance['status']
        new_status = 'ASSIGNED'
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Mark any previous active assignments on this grievance as REASSIGNED
        cursor.execute('''
        UPDATE worker_assignments
        SET assignment_status = 'REASSIGNED'
        WHERE grievance_id = ? AND assignment_status IN ('ASSIGNED', 'ACCEPTED')
        ''', (grievance_id,))

        # Update grievance record
        cursor.execute('''
        UPDATE grievances
        SET department_id = ?,
            assigned_officer_id = ?,
            assigned_worker_id = ?,
            status = ?,
            updated_at = ?
        WHERE id = ?
        ''', (target_dept_id, target_officer_id, worker_id, new_status, now_str, grievance_id))

        # Insert new assignment audit record
        cursor.execute('''
        INSERT INTO worker_assignments (
            grievance_id, worker_id, department_id, assigned_by_user_id, assigned_at, assignment_status
        ) VALUES (?, ?, ?, ?, ?, 'ASSIGNED')
        ''', (grievance_id, worker_id, target_dept_id, admin_user_id, now_str))
        assignment_id = cursor.lastrowid

        # Record audit history in grievance_updates
        record_status_history(
            cursor=cursor,
            grievance_id=grievance_id,
            from_status=old_status,
            to_status=new_status,
            remarks=f"Assigned to {worker['worker_name']} ({worker['badge_id']}): {clean_remarks}",
            user_id=admin_user_id,
            user_role=admin_role,
            created_at=now_str
        )

        # 7. Notifications
        send_notification(
            cursor, worker['user_id'], grievance_id,
            'New Field Task Assigned',
            f"You have been assigned to remediate grievance {grievance['tracking_id']}: '{grievance['title']}'. Please review and accept.", now_str
        )

        if target_officer_id:
            cursor.execute("SELECT user_id FROM officers WHERE id = ?", (target_officer_id,))
            off_u = cursor.fetchone()
            if off_u:
                send_notification(
                    cursor, off_u['user_id'], grievance_id,
                    'Supervising Assignment Updated',
                    f"Grievance {grievance['tracking_id']} assigned to {worker['worker_name']}.", now_str
                )

        send_notification(
            cursor, grievance['citizen_id'], grievance_id,
            'Field Technician Assigned',
            f"Your complaint {grievance['tracking_id']} has been assigned to field technician {worker['worker_name']}.", now_str
        )

        conn.commit()
        conn.close()

        return True, f"Grievance assigned successfully to {worker['worker_name']}.", {
            'assignment_id': assignment_id,
            'grievance_id': grievance_id,
            'worker_id': worker_id,
            'status': new_status,
            'worker_name': worker['worker_name'],
            'loyalty_points': worker['loyalty_points']
        }, 200

def worker_accept_assignment(grievance_id: int, worker_user_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]], int]:
    """
    Worker accepts an assigned task.
    Transitions grievance from ASSIGNED -> ACCEPTED and updates worker assignment record.
    """
    with _assignment_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Find worker record
        cursor.execute("SELECT id, loyalty_points FROM workers WHERE user_id = ?", (worker_user_id,))
        w_row = cursor.fetchone()
        if not w_row:
            conn.close()
            return False, "Worker profile not found for authenticated user.", None, 403
        worker_id = w_row['id']

        # Find grievance
        cursor.execute("SELECT * FROM grievances WHERE id = ?", (grievance_id,))
        g_row = cursor.fetchone()
        if not g_row:
            conn.close()
            return False, f"Grievance (ID: {grievance_id}) not found.", None, 404
        grievance = dict(g_row)

        # Security check: must be assigned to this worker
        if grievance.get('assigned_worker_id') != worker_id:
            conn.close()
            return False, "Access denied: You are not assigned to this grievance.", None, 403

        # State integrity & duplicate prevention
        if grievance['status'] == 'ACCEPTED':
            conn.close()
            return False, "Assignment has already been accepted.", None, 400

        if grievance['status'] == 'IN_PROGRESS':
            conn.close()
            return False, "Assignment is already in progress.", None, 400

        if grievance['status'] != 'ASSIGNED':
            conn.close()
            return False, f"Cannot accept grievance in '{grievance['status']}' state.", None, 400

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update grievance to ACCEPTED
        cursor.execute('''
        UPDATE grievances
        SET status = 'ACCEPTED', updated_at = ?
        WHERE id = ?
        ''', (now_str, grievance_id))

        # Update worker_assignments record
        cursor.execute('''
        UPDATE worker_assignments
        SET assignment_status = 'ACCEPTED', accepted_at = ?
        WHERE grievance_id = ? AND worker_id = ? AND assignment_status = 'ASSIGNED'
        ''', (now_str, grievance_id, worker_id))

        # Record audit history
        record_status_history(
            cursor=cursor,
            grievance_id=grievance_id,
            from_status='ASSIGNED',
            to_status='ACCEPTED',
            remarks='Worker accepted remediation assignment.',
            user_id=worker_user_id,
            user_role='worker',
            created_at=now_str
        )

        # Notify citizen and supervising officer
        send_notification(
            cursor, grievance['citizen_id'], grievance_id,
            'Work Scheduled',
            f"Field technician has accepted grievance {grievance['tracking_id']} and scheduled site remediation.", now_str
        )

        if grievance.get('assigned_officer_id'):
            cursor.execute("SELECT user_id FROM officers WHERE id = ?", (grievance['assigned_officer_id'],))
            off_u = cursor.fetchone()
            if off_u:
                send_notification(
                    cursor, off_u['user_id'], grievance_id,
                    'Assignment Accepted by Worker',
                    f"Technician accepted work for {grievance['tracking_id']}.", now_str
                )

        conn.commit()
        conn.close()

        return True, "Assignment accepted successfully. The task is now in your active work list.", {
            'grievance_id': grievance_id,
            'status': 'ACCEPTED',
            'accepted_at': now_str
        }, 200

def worker_reject_assignment(
    grievance_id: int,
    worker_user_id: int,
    rejection_reason: str
) -> Tuple[bool, str, Optional[Dict[str, Any]], int]:
    """
    Worker rejects an assigned task.
    Requires mandatory rejection reason, releases grievance back to SUBMITTED for reassignment,
    notifies admins, and deducts the configurable rejection penalty (-5 points) exactly once.
    """
    clean_reason = (rejection_reason or "").strip()
    if not clean_reason:
        return False, "A mandatory reason is required to reject an assignment.", None, 400

    with _assignment_lock:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Find worker record
        cursor.execute('''
        SELECT w.id, w.badge_id, COALESCE(w.loyalty_points, 100) as loyalty_points, u.full_name
        FROM workers w
        JOIN users u ON w.user_id = u.id
        WHERE w.user_id = ?
        ''', (worker_user_id,))
        w_row = cursor.fetchone()
        if not w_row:
            conn.close()
            return False, "Worker profile not found for authenticated user.", None, 403
        worker = dict(w_row)
        worker_id = worker['id']

        # Find grievance
        cursor.execute("SELECT * FROM grievances WHERE id = ?", (grievance_id,))
        g_row = cursor.fetchone()
        if not g_row:
            conn.close()
            return False, f"Grievance (ID: {grievance_id}) not found.", None, 404
        grievance = dict(g_row)

        # Security check: must be assigned to this worker
        if grievance.get('assigned_worker_id') != worker_id:
            conn.close()
            return False, "Access denied: You are not assigned to this grievance.", None, 403

        # State integrity & double-rejection prevention
        if grievance['status'] != 'ASSIGNED':
            conn.close()
            return False, f"Cannot reject grievance in '{grievance['status']}' state (Already processed or released).", None, 400

        # Verify active assignment record exists
        cursor.execute('''
        SELECT id FROM worker_assignments
        WHERE grievance_id = ? AND worker_id = ? AND assignment_status = 'ASSIGNED'
        ''', (grievance_id, worker_id))
        assignment_row = cursor.fetchone()
        if not assignment_row:
            conn.close()
            return False, "No active pending assignment record found to reject.", None, 400

        assignment_id = assignment_row['id']
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Update worker_assignments: mark as REJECTED with reason and timestamp
        cursor.execute('''
        UPDATE worker_assignments
        SET assignment_status = 'REJECTED',
            rejection_reason = ?,
            rejected_at = ?
        WHERE id = ?
        ''', (clean_reason, now_str, assignment_id))

        # 2. Release grievance: set assigned_worker_id to NULL and return status to SUBMITTED
        cursor.execute('''
        UPDATE grievances
        SET status = 'SUBMITTED',
            assigned_worker_id = NULL,
            updated_at = ?
        WHERE id = ?
        ''', (now_str, grievance_id))

        # 3. Record status audit trail in grievance_updates
        record_status_history(
            cursor=cursor,
            grievance_id=grievance_id,
            from_status='ASSIGNED',
            to_status='SUBMITTED',
            remarks=f"Assignment rejected by {worker['full_name']} ({worker['badge_id']}). Reason: {clean_reason}",
            user_id=worker_user_id,
            user_role='worker',
            created_at=now_str
        )

        # 4. Notify Administrators and Supervising Officers
        notify_admins(
            cursor, grievance_id,
            'Assignment Rejected by Field Worker',
            f"Worker {worker['full_name']} ({worker['badge_id']}) rejected grievance {grievance['tracking_id']}. Reason: {clean_reason}. Grievance released for reassignment.",
            now_str
        )

        conn.commit()
        conn.close()

        # 5. Deduct configurable loyalty points penalty (-5 points) exactly once
        ok, msg, tx = deduct_rejected_assignment_points(
            worker_id=worker_id,
            grievance_tracking_id=grievance['tracking_id'],
            actor_source="SYSTEM"
        )

        new_balance = tx['new_balance'] if tx else worker['loyalty_points'] + REJECTED_ASSIGNMENT_PENALTY_POINTS

        return True, (
            f"Assignment rejected. Grievance has been released for reassignment and "
            f"{abs(REJECTED_ASSIGNMENT_PENALTY_POINTS)} loyalty points have been deducted."
        ), {
            'grievance_id': grievance_id,
            'status': 'SUBMITTED',
            'points_deducted': REJECTED_ASSIGNMENT_PENALTY_POINTS,
            'new_loyalty_balance': new_balance,
            'rejection_reason': clean_reason
        }, 200
