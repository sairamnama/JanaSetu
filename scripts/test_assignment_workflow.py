"""
Grievance Assignment Workflow Verification Suite
Validates the complete end-to-end assignment lifecycle:
1. Configurable minimum points (60) and rejection penalty (-5).
2. Admin review of eligible vs ineligible workers (points, skills, active status, workload).
3. Assignment dispatch with role permissions and duplicate active assignment prevention.
4. Worker portal acceptance flow (ASSIGNED -> ACCEPTED -> IN_PROGRESS).
5. Worker portal rejection flow with mandatory reason, assignment release back to SUBMITTED,
   admin notification, exactly-once penalty deduction (-5 pts), and audit ledger integrity.
6. Successful reassignment of released grievance.
7. Cross-role security constraints and database persistence.
"""

import os
import sys

# Add workspace root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from core.database import get_db_connection
from core.config import (
    MIN_ASSIGNMENT_LOYALTY_POINTS,
    REJECTED_ASSIGNMENT_PENALTY_POINTS,
    LOYALTY_POINTS_CONFIG
)
from services.points_service import get_worker_points_summary, get_worker_transactions
from services.assignment_service import get_eligible_workers, assign_worker_to_grievance


def run_tests():
    print("=" * 75)
    print("  Grievance Assignment Workflow - Automated End-to-End Verification")
    print("=" * 75)

    app.config['TESTING'] = True
    app.config['DEMO_MODE'] = True
    client = app.test_client()

    conn = get_db_connection()
    cursor = conn.cursor()

    # ----------------------------------------------------
    # 1. Configurable Thresholds & Penalties Verification
    # ----------------------------------------------------
    assert MIN_ASSIGNMENT_LOYALTY_POINTS == 60, f"Expected min points 60, got {MIN_ASSIGNMENT_LOYALTY_POINTS}"
    assert REJECTED_ASSIGNMENT_PENALTY_POINTS == -5, f"Expected penalty -5, got {REJECTED_ASSIGNMENT_PENALTY_POINTS}"
    assert LOYALTY_POINTS_CONFIG['MIN_ASSIGNMENT_LOYALTY_POINTS'] == 60
    assert LOYALTY_POINTS_CONFIG['REJECTED_ASSIGNMENT_PENALTY'] == -5
    print(f" [PASS] 1. Configurable rules verified (Min Points={MIN_ASSIGNMENT_LOYALTY_POINTS}, Penalty={REJECTED_ASSIGNMENT_PENALTY_POINTS})")

    # ----------------------------------------------------
    # 2. Setup Test Data (Workers & Grievances)
    # ----------------------------------------------------
    # Pick a department
    cursor.execute("SELECT id, name FROM departments WHERE code = 'WS' OR id = 1 LIMIT 1")
    dept = cursor.fetchone()
    dept_id = dept['id']

    # Get an eligible worker (Water Supply / Sanitation or similar)
    cursor.execute("""
        SELECT w.id, w.user_id, w.loyalty_points, u.full_name, w.department_id, w.skill_trade
        FROM workers w
        JOIN users u ON w.user_id = u.id
        WHERE w.department_id = ? AND w.is_active = 1 AND w.loyalty_points >= 60
        LIMIT 1
    """, (dept_id,))
    worker1 = cursor.fetchone()
    assert worker1 is not None, "Need at least one eligible active worker with >=60 points"
    w1_id = worker1['id']
    w1_uid = worker1['user_id']
    w1_init_pts = worker1['loyalty_points']

    # Get a second worker for reassignment/forbidden acceptance tests
    cursor.execute("""
        SELECT w.id, w.user_id, w.loyalty_points, u.full_name, w.department_id, w.skill_trade
        FROM workers w
        JOIN users u ON w.user_id = u.id
        WHERE w.id != ? AND w.is_active = 1
        LIMIT 1
    """, (w1_id,))
    worker2 = cursor.fetchone()
    assert worker2 is not None, "Need a second worker for tests"
    w2_id = worker2['id']
    w2_uid = worker2['user_id']

    # Create a test grievance in SUBMITTED state
    cursor.execute("SELECT id FROM users WHERE role = 'citizen' LIMIT 1")
    cit = cursor.fetchone()
    citizen_uid = cit['id']

    import time
    tracking_1 = f"GRV-TEST-{int(time.time())}-1"
    cursor.execute("""
        INSERT INTO grievances (
            tracking_id, citizen_id, category, title, description,
            ward_number, location_landmark, priority, status, department_id
        ) VALUES (?, ?, 'Water Supply', 'Broken Pipeline Valve Test 1', 'Main pipe leaking water', 2, 'Main Square', 'High', 'SUBMITTED', ?)
    """, (tracking_1, citizen_uid, dept_id))
    g1_id = cursor.lastrowid

    tracking_2 = f"GRV-TEST-{int(time.time())}-2"
    cursor.execute("""
        INSERT INTO grievances (
            tracking_id, citizen_id, category, title, description,
            ward_number, location_landmark, priority, status, department_id
        ) VALUES (?, ?, 'Water Supply', 'Broken Pipeline Valve Test 2', 'Drainage overflow near pump', 2, 'Pump Station', 'Medium', 'SUBMITTED', ?)
    """, (tracking_2, citizen_uid, dept_id))
    g2_id = cursor.lastrowid

    conn.commit()
    conn.close()

    print(f" [*] Test Grievance 1: ID={g1_id}, Tracking={tracking_1}")
    print(f" [*] Test Grievance 2: ID={g2_id}, Tracking={tracking_2}")
    print(f" [*] Worker 1: ID={w1_id}, UserID={w1_uid}, Pts={w1_init_pts}")
    print(f" [*] Worker 2: ID={w2_id}, UserID={w2_uid}")

    # ----------------------------------------------------
    # 3. Eligible Workers API & Eligibility Evaluation
    # ----------------------------------------------------
    # Admin logs in
    client.post('/api/demo-switch-user', json={'role': 'admin'})

    elig_res = client.get(f'/api/grievances/{g1_id}/eligible-workers?department_id={dept_id}')
    assert elig_res.status_code == 200, f"Eligible workers failed: {elig_res.get_data(as_text=True)}"
    elig_data = elig_res.get_json()
    assert elig_data['success'] is True
    assert elig_data['min_points_required'] == 60
    workers_list = elig_data['workers']
    assert len(workers_list) > 0

    # Verify w1 is listed and eligible
    target_w1 = next((w for w in workers_list if w['id'] == w1_id), None)
    assert target_w1 is not None
    assert target_w1['loyalty_points'] >= 60
    assert target_w1['is_eligible'] is True
    assert 'active_workload' in target_w1
    print(f" [PASS] 2. Eligible workers endpoint verified (Found {len(workers_list)} workers, Worker 1 eligible with {target_w1['loyalty_points']} pts, Workload: {target_w1['active_workload']})")

    # ----------------------------------------------------
    # 4. Ineligible Worker Assignment Prevention
    # ----------------------------------------------------
    # Create or temporarily set a worker with < 60 points
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE workers SET loyalty_points = 45 WHERE id = ?", (w2_id,))
    conn.commit()
    conn.close()

    bad_assign_res = client.put(f'/api/grievances/{g1_id}/assign', json={
        'department_id': dept_id,
        'assigned_worker_id': w2_id,
        'remarks': 'Assigning ineligible worker with 45 points'
    })
    assert bad_assign_res.status_code == 400, f"Expected 400 for ineligible worker, got {bad_assign_res.status_code}"
    bad_err = bad_assign_res.get_json().get('error', '')
    assert 'ineligible' in bad_err.lower() or 'loyalty points' in bad_err.lower()
    print(f" [PASS] 3. Assignment to ineligible worker (<60 pts) correctly blocked with 400: '{bad_err}'")

    # Restore w2 points
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE workers SET loyalty_points = 80 WHERE id = ?", (w2_id,))
    # Test inactive worker
    c.execute("UPDATE workers SET is_active = 0 WHERE id = ?", (w2_id,))
    conn.commit()
    conn.close()

    inactive_assign_res = client.put(f'/api/grievances/{g1_id}/assign', json={
        'department_id': dept_id,
        'assigned_worker_id': w2_id,
        'remarks': 'Assigning inactive worker'
    })
    assert inactive_assign_res.status_code == 400, f"Expected 400 for inactive worker, got {inactive_assign_res.status_code}"
    inactive_err = inactive_assign_res.get_json().get('error', '')
    assert 'inactive' in inactive_err.lower()
    print(f" [PASS] 3b. Assignment to inactive worker correctly blocked with 400: '{inactive_err}'")

    # Restore w2 active status
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE workers SET is_active = 1 WHERE id = ?", (w2_id,))
    conn.commit()
    conn.close()

    # ----------------------------------------------------
    # 5. Role Permission Checks for Assignment
    # ----------------------------------------------------
    # Citizen attempts to assign
    client.post('/api/demo-switch-user', json={'role': 'citizen'})
    cit_assign_res = client.put(f'/api/grievances/{g1_id}/assign', json={
        'department_id': dept_id,
        'assigned_worker_id': w1_id,
        'remarks': 'Citizen assignment attempt'
    })
    assert cit_assign_res.status_code == 403, f"Citizen should be forbidden, got {cit_assign_res.status_code}"

    # Worker attempts to assign
    client.post('/api/demo-switch-user', json={'role': 'worker'})
    w_assign_res = client.put(f'/api/grievances/{g1_id}/assign', json={
        'department_id': dept_id,
        'assigned_worker_id': w1_id,
        'remarks': 'Worker assignment attempt'
    })
    assert w_assign_res.status_code == 403, f"Worker should be forbidden from assigning, got {w_assign_res.status_code}"
    print(" [PASS] 4. Role permissions enforced: citizen & worker forbidden from assigning grievances (HTTP 403)")

    # ----------------------------------------------------
    # 6. Admin Assigns Grievance to Eligible Worker 1
    # ----------------------------------------------------
    client.post('/api/demo-switch-user', json={'role': 'admin'})
    assign_res = client.put(f'/api/grievances/{g1_id}/assign', json={
        'department_id': dept_id,
        'assigned_worker_id': w1_id,
        'remarks': 'Assigned by Panchayat Administrator for urgent repair'
    })
    assert assign_res.status_code == 200, f"Admin assignment failed: {assign_res.get_data(as_text=True)}"
    assign_data = assign_res.get_json()
    assert assign_data['success'] is True

    # Check database state
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT status, assigned_worker_id FROM grievances WHERE id = ?", (g1_id,))
    g_row = c.fetchone()
    assert g_row['status'] == 'ASSIGNED', f"Expected ASSIGNED, got {g_row['status']}"
    assert g_row['assigned_worker_id'] == w1_id

    # Check worker_assignments row
    c.execute("""
        SELECT id, worker_id, assignment_status, assigned_at
        FROM worker_assignments
        WHERE grievance_id = ? AND assignment_status = 'ASSIGNED'
    """, (g1_id,))
    wa_row = c.fetchone()
    assert wa_row is not None, "Missing worker_assignments record"
    assert wa_row['worker_id'] == w1_id
    assert wa_row['assigned_at'] is not None
    conn.close()
    print(f" [PASS] 5. Assignment succeeded: status is ASSIGNED, worker_assignments recorded (wa_id={wa_row['id']})")

    # ----------------------------------------------------
    # 7. Prevent Duplicate Active Assignment
    # ----------------------------------------------------
    dup_assign_res = client.put(f'/api/grievances/{g1_id}/assign', json={
        'department_id': dept_id,
        'assigned_worker_id': w1_id,
        'remarks': 'Duplicate assignment attempt'
    })
    assert dup_assign_res.status_code == 400, f"Expected 400 for duplicate assignment, got {dup_assign_res.status_code}"
    dup_err = dup_assign_res.get_json().get('error', '')
    assert 'already' in dup_err.lower() or 'duplicate' in dup_err.lower() or 'active assignment' in dup_err.lower()
    print(f" [PASS] 6. Duplicate active assignment prevented: '{dup_err}'")

    # ----------------------------------------------------
    # 8. Worker Portal Acceptance Flow (ASSIGNED -> ACCEPTED -> IN_PROGRESS)
    # ----------------------------------------------------
    # Authenticate as Worker 1
    with client.session_transaction() as sess:
        sess['user_id'] = w1_uid
        sess['role'] = 'worker'
        sess['username'] = 'worker1'
        sess['full_name'] = worker1['full_name']

    # Worker checks their assigned tasks via /api/grievances
    w_tasks_res = client.get('/api/grievances')
    assert w_tasks_res.status_code == 200
    w_tasks = w_tasks_res.get_json().get('grievances', [])
    assert any(g['id'] == g1_id for g in w_tasks), "Assigned grievance must appear in worker's queue"

    # Worker 2 attempts to accept Worker 1's assignment (should fail 403)
    with client.session_transaction() as sess:
        sess['user_id'] = w2_uid
        sess['role'] = 'worker'
    bad_accept_res = client.post(f'/api/worker/grievances/{g1_id}/accept')
    assert bad_accept_res.status_code == 403, f"Unauthorized worker should get 403, got {bad_accept_res.status_code}"

    # Worker 1 accepts the assignment
    with client.session_transaction() as sess:
        sess['user_id'] = w1_uid
        sess['role'] = 'worker'

    accept_res = client.post(f'/api/worker/grievances/{g1_id}/accept')
    assert accept_res.status_code == 200, f"Accept failed: {accept_res.get_data(as_text=True)}"
    accept_data = accept_res.get_json()
    assert accept_data['success'] is True

    # Verify status changed to ACCEPTED in DB
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT status, assigned_worker_id FROM grievances WHERE id = ?", (g1_id,))
    g_acc = c.fetchone()
    assert g_acc['status'] == 'ACCEPTED', f"Expected ACCEPTED, got {g_acc['status']}"
    assert g_acc['assigned_worker_id'] == w1_id

    # Verify worker_assignments table updated
    c.execute("""
        SELECT assignment_status, accepted_at
        FROM worker_assignments
        WHERE grievance_id = ? AND worker_id = ?
    """, (g1_id, w1_id))
    wa_acc = c.fetchone()
    assert wa_acc['assignment_status'] == 'ACCEPTED'
    assert wa_acc['accepted_at'] is not None
    conn.close()
    print(f" [PASS] 7. Worker acceptance succeeded: status is ACCEPTED, accepted_at timestamp recorded ({wa_acc['accepted_at']})")

    # Repeat accept guard (idempotent / non-ASSIGNED)
    repeat_accept = client.post(f'/api/worker/grievances/{g1_id}/accept')
    assert repeat_accept.status_code == 400

    # Worker starts work (ACCEPTED -> IN_PROGRESS)
    start_work_res = client.put(f'/api/grievances/{g1_id}/status', json={
        'status': 'IN_PROGRESS',
        'remarks': 'Worker commenced excavation on site.'
    })
    assert start_work_res.status_code == 200, f"Start work failed: {start_work_res.get_data(as_text=True)}"
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT status FROM grievances WHERE id = ?", (g1_id,))
    assert c.fetchone()['status'] == 'IN_PROGRESS'
    conn.close()
    print(" [PASS] 8. Transition from ACCEPTED to IN_PROGRESS succeeded on site commencement")

    # ----------------------------------------------------
    # 9. Worker Portal Rejection Flow & Penalty Deductions
    # ----------------------------------------------------
    # Assign grievance 2 to Worker 1
    client.post('/api/demo-switch-user', json={'role': 'admin'})
    assign_res2 = client.put(f'/api/grievances/{g2_id}/assign', json={
        'department_id': dept_id,
        'assigned_worker_id': w1_id,
        'remarks': 'Assigned drainage repair to Worker 1'
    })
    assert assign_res2.status_code == 200

    # Check worker 1 points prior to rejection
    pts_before_rejection = get_worker_points_summary(w1_id)['loyalty_points']

    # Worker 1 session
    with client.session_transaction() as sess:
        sess['user_id'] = w1_uid
        sess['role'] = 'worker'

    # Rejection without reason must fail (HTTP 400)
    no_reason_res = client.post(f'/api/worker/grievances/{g2_id}/reject', json={
        'reason': ''
    })
    assert no_reason_res.status_code == 400, "Rejection without reason should return 400"

    # Rejection by wrong worker must fail (HTTP 403)
    with client.session_transaction() as sess:
        sess['user_id'] = w2_uid
        sess['role'] = 'worker'
    wrong_worker_res = client.post(f'/api/worker/grievances/{g2_id}/reject', json={
        'reason': 'Not my ward'
    })
    assert wrong_worker_res.status_code == 403

    # Valid rejection by Worker 1
    with client.session_transaction() as sess:
        sess['user_id'] = w1_uid
        sess['role'] = 'worker'

    reject_reason = "Specialized valve crimping tool unavailable today, urgent repair needed"
    reject_res = client.post(f'/api/worker/grievances/{g2_id}/reject', json={
        'reason': reject_reason
    })
    assert reject_res.status_code == 200, f"Reject failed: {reject_res.get_data(as_text=True)}"
    reject_data = reject_res.get_json()
    assert reject_data['success'] is True

    # Verify grievance status released back to SUBMITTED and assigned_worker_id is NULL
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT status, assigned_worker_id FROM grievances WHERE id = ?", (g2_id,))
    g_rej = c.fetchone()
    assert g_rej['status'] == 'SUBMITTED', f"Expected released status SUBMITTED, got {g_rej['status']}"
    assert g_rej['assigned_worker_id'] is None, f"Expected assigned_worker_id to be None, got {g_rej['assigned_worker_id']}"

    # Verify worker_assignments updated with REJECTED, reason, rejected_at
    c.execute("""
        SELECT assignment_status, rejection_reason, rejected_at
        FROM worker_assignments
        WHERE grievance_id = ? AND worker_id = ?
        ORDER BY id DESC LIMIT 1
    """, (g2_id, w1_id))
    wa_rej = c.fetchone()
    assert wa_rej['assignment_status'] == 'REJECTED'
    assert wa_rej['rejection_reason'] == reject_reason
    assert wa_rej['rejected_at'] is not None

    # Verify admin notification was created
    c.execute("""
        SELECT title, message FROM notifications
        WHERE grievance_id = ?
        ORDER BY id DESC LIMIT 1
    """, (g2_id,))
    admin_notif = c.fetchone()
    assert admin_notif is not None
    assert 'rejected' in admin_notif['title'].lower() or 'rejection' in admin_notif['message'].lower()
    conn.close()

    # Verify exact -5 point deduction in points system
    pts_after_rejection = get_worker_points_summary(w1_id)['loyalty_points']
    assert pts_after_rejection == pts_before_rejection - 5, f"Expected {pts_before_rejection - 5}, got {pts_after_rejection}"

    # Verify transaction ledger entry
    w1_txs = get_worker_transactions(w1_id)
    assert len(w1_txs) > 0
    latest_tx = w1_txs[0]
    assert latest_tx['points_changed'] == -5
    assert latest_tx['previous_balance'] == pts_before_rejection
    assert latest_tx['new_balance'] == pts_after_rejection
    assert 'rejected assignment' in latest_tx['reason'].lower()
    assert tracking_2 in latest_tx['reason']

    print(f" [PASS] 9. Rejection succeeded: released to SUBMITTED, assigned_worker_id cleared, admin notified, -5 points deducted ({pts_before_rejection} -> {pts_after_rejection}) with ledger audit entry")

    # ----------------------------------------------------
    # 10. Prevent Duplicate Rejection / Duplicate Deduction
    # ----------------------------------------------------
    dup_reject_res = client.post(f'/api/worker/grievances/{g2_id}/reject', json={
        'reason': 'Second click rejection'
    })
    # Since grievance is now SUBMITTED and assigned_worker_id is NULL, cannot reject again
    assert dup_reject_res.status_code in (400, 403), f"Expected 400 or 403 on duplicate reject, got {dup_reject_res.status_code}"
    # Ensure points were NOT deducted a second time
    pts_after_dup_attempt = get_worker_points_summary(w1_id)['loyalty_points']
    assert pts_after_dup_attempt == pts_after_rejection, "Duplicate deduction must be strictly prevented!"
    print(f" [PASS] 10. Duplicate rejection blocked and duplicate point deductions strictly prevented (Balance remained {pts_after_dup_attempt})")

    # ----------------------------------------------------
    # 11. Reassign Released Grievance to Another Worker
    # ----------------------------------------------------
    client.post('/api/demo-switch-user', json={'role': 'admin'})
    reassign_res = client.put(f'/api/grievances/{g2_id}/assign', json={
        'department_id': dept_id,
        'assigned_worker_id': w2_id,
        'remarks': 'Reassigning released grievance to Worker 2'
    })
    assert reassign_res.status_code == 200, f"Reassignment failed: {reassign_res.get_data(as_text=True)}"

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT status, assigned_worker_id FROM grievances WHERE id = ?", (g2_id,))
    g_reassigned = c.fetchone()
    assert g_reassigned['status'] == 'ASSIGNED'
    assert g_reassigned['assigned_worker_id'] == w2_id

    # Verify worker_assignments contains both the rejected assignment and the new assignment
    c.execute("SELECT worker_id, assignment_status FROM worker_assignments WHERE grievance_id = ? ORDER BY id ASC", (g2_id,))
    history = c.fetchall()
    assert len(history) >= 2
    assert history[0]['assignment_status'] == 'REJECTED'
    assert history[0]['worker_id'] == w1_id
    assert history[-1]['assignment_status'] == 'ASSIGNED'
    assert history[-1]['worker_id'] == w2_id
    conn.close()
    print(" [PASS] 11. Released grievance successfully reassigned to new worker; full assignment history preserved")

    # ----------------------------------------------------
    # 12. Database Persistence Check
    # ----------------------------------------------------
    # Fresh connection verification
    verify_conn = get_db_connection()
    vc = verify_conn.cursor()
    vc.execute("SELECT status, assigned_worker_id FROM grievances WHERE id = ?", (g1_id,))
    final_g1 = vc.fetchone()
    assert final_g1['status'] == 'IN_PROGRESS'
    assert final_g1['assigned_worker_id'] == w1_id

    vc.execute("SELECT status, assigned_worker_id FROM grievances WHERE id = ?", (g2_id,))
    final_g2 = vc.fetchone()
    assert final_g2['status'] == 'ASSIGNED'
    assert final_g2['assigned_worker_id'] == w2_id
    verify_conn.close()
    print(" [PASS] 12. Database persistence verified across all grievance states and audit tables")

    print("\n" + "=" * 75)
    print("  ALL 12 ASSIGNMENT WORKFLOW CHECKS PASSED PERFECTLY!")
    print("=" * 75)


if __name__ == '__main__':
    run_tests()
