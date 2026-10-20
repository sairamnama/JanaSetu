"""
Worker Loyalty Points System Verification & Self-Check Suite
Tests points management, balance integrity, transaction history, persistence,
unauthorized access restrictions, and configurable penalty rules.
"""

import os
import sys

# Add workspace root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from core.database import get_db_connection
from core.config import (
    INITIAL_WORKER_POINTS,
    MIN_WORKER_POINTS,
    LOYALTY_POINTS_CONFIG,
    REJECTED_ASSIGNMENT_PENALTY_POINTS
)
from services.points_service import (
    get_worker_points_summary,
    get_worker_transactions,
    get_all_points_transactions,
    adjust_worker_points,
    deduct_rejected_assignment_points
)

def run_tests():
    print("=" * 70)
    print("  Worker Loyalty Points System - Automated Verification")
    print("=" * 70)

    app.config['TESTING'] = True
    app.config['DEMO_MODE'] = True
    client = app.test_client()

    # ----------------------------------------------------
    # 0. Setup: Identify a test worker
    # ----------------------------------------------------
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, loyalty_points, badge_id FROM workers LIMIT 1")
    w = cursor.fetchone()
    assert w is not None, "No worker found in database for testing"
    test_worker_id = w['id']
    test_worker_uid = w['user_id']
    init_pts = w['loyalty_points'] or INITIAL_WORKER_POINTS
    conn.close()

    print(f"[*] Target Worker: ID={test_worker_id}, Badge={w['badge_id']}, Initial Points={init_pts}")

    # ----------------------------------------------------
    # 1. Configurable Points Verification
    # ----------------------------------------------------
    assert 'INITIAL_POINTS' in LOYALTY_POINTS_CONFIG, "Missing INITIAL_POINTS in config"
    assert 'MIN_POINTS' in LOYALTY_POINTS_CONFIG, "Missing MIN_POINTS in config"
    assert 'REJECTED_ASSIGNMENT_PENALTY' in LOYALTY_POINTS_CONFIG, "Missing REJECTED_ASSIGNMENT_PENALTY in config"
    assert REJECTED_ASSIGNMENT_PENALTY_POINTS == -5, f"Expected default -5 penalty, got {REJECTED_ASSIGNMENT_PENALTY_POINTS}"
    print(f" [PASS] 1. Configurable rules verified (Initial={INITIAL_WORKER_POINTS}, Min={MIN_WORKER_POINTS}, Penalty={REJECTED_ASSIGNMENT_PENALTY_POINTS})")

    # ----------------------------------------------------
    # 2. Add Points Manually (Admin API)
    # ----------------------------------------------------
    # Authenticate as Admin
    res = client.post('/api/demo-switch-user', json={'role': 'admin'})
    assert res.status_code == 200, "Admin login failed"

    add_res = client.post(f'/api/admin/workers/{test_worker_id}/adjust-points', json={
        'action': 'add',
        'points': 15,
        'reason': 'Exemplary drainage de-silting completion'
    })
    assert add_res.status_code == 200, f"Expected 200, got {add_res.status_code}: {add_res.get_data(as_text=True)}"
    add_data = add_res.get_json()
    assert add_data['success'] is True
    assert add_data['new_balance'] == init_pts + 15
    assert add_data['transaction']['points_changed'] == 15
    assert add_data['transaction']['previous_balance'] == init_pts
    assert 'Exemplary drainage' in add_data['transaction']['reason']
    print(f" [PASS] 2. Add points manually succeeded (Balance: {init_pts} -> {add_data['new_balance']})")

    # ----------------------------------------------------
    # 3. Deduct Points Manually (Admin API)
    # ----------------------------------------------------
    cur_bal = add_data['new_balance']
    deduct_res = client.post(f'/api/admin/workers/{test_worker_id}/adjust-points', json={
        'action': 'deduct',
        'points': 10,
        'reason': 'Unannounced delay in site inspection reporting'
    })
    assert deduct_res.status_code == 200, f"Expected 200, got {deduct_res.status_code}: {deduct_res.get_data(as_text=True)}"
    deduct_data = deduct_res.get_json()
    assert deduct_data['success'] is True
    assert deduct_data['new_balance'] == cur_bal - 10
    assert deduct_data['transaction']['points_changed'] == -10
    assert deduct_data['transaction']['previous_balance'] == cur_bal
    print(f" [PASS] 3. Deduct points manually succeeded (Balance: {cur_bal} -> {deduct_data['new_balance']})")

    # ----------------------------------------------------
    # 4. Reject Invalid Adjustments
    # ----------------------------------------------------
    # 4a. Zero points
    res_zero = client.post(f'/api/admin/workers/{test_worker_id}/adjust-points', json={
        'points': 0,
        'reason': 'Zero points check'
    })
    assert res_zero.status_code == 400, "Zero points adjustment should return HTTP 400"

    # 4b. Non-integer points
    res_invalid_type = client.post(f'/api/admin/workers/{test_worker_id}/adjust-points', json={
        'points': 'not_a_number',
        'reason': 'Invalid type check'
    })
    assert res_invalid_type.status_code == 400, "Non-integer points should return HTTP 400"

    # 4c. Missing / whitespace-only reason
    res_no_reason = client.post(f'/api/admin/workers/{test_worker_id}/adjust-points', json={
        'points': 5,
        'reason': '   '
    })
    assert res_no_reason.status_code == 400, "Missing reason should return HTTP 400"

    # 4d. Non-existent worker ID
    res_bad_worker = client.post('/api/admin/workers/999999/adjust-points', json={
        'points': 5,
        'reason': 'Non-existent worker test'
    })
    assert res_bad_worker.status_code in (400, 404), "Non-existent worker should be rejected"
    print(" [PASS] 4. Invalid adjustments rejected (zero points, non-integer, missing reason, invalid worker)")

    # ----------------------------------------------------
    # 5. Prevent Invalid Balance (Negative Balance Guardrail)
    # ----------------------------------------------------
    current_pts = deduct_data['new_balance']
    excessive_deduction = current_pts + 50
    res_excess = client.post(f'/api/admin/workers/{test_worker_id}/adjust-points', json={
        'action': 'deduct',
        'points': excessive_deduction,
        'reason': 'Excessive deduction test to check floor balance'
    })
    assert res_excess.status_code == 400, "Deduction exceeding balance should return HTTP 400"
    assert 'cannot reduce below minimum limit' in res_excess.get_json()['error']
    print(f" [PASS] 5. Negative balance prevention verified (Rejected deduction of {excessive_deduction} against {current_pts})")

    # ----------------------------------------------------
    # 6. Transaction History Verification
    # ----------------------------------------------------
    hist_res = client.get(f'/api/admin/workers/{test_worker_id}/points')
    assert hist_res.status_code == 200, "Admin worker points history fetch failed"
    hist_data = hist_res.get_json()
    assert hist_data['success'] is True
    txs = hist_data['transactions']
    assert len(txs) >= 2, f"Expected at least 2 transactions, got {len(txs)}"

    # Check top transaction structure
    latest_tx = txs[0]
    for field in ['id', 'worker_id', 'previous_balance', 'points_changed', 'new_balance', 'reason', 'actor_source', 'created_at']:
        assert field in latest_tx, f"Transaction missing required field: {field}"
        assert latest_tx[field] is not None, f"Field {field} is None"

    assert latest_tx['worker_id'] == test_worker_id
    assert latest_tx['new_balance'] == current_pts
    print(" [PASS] 6. Complete transaction history fields verified (worker_id, balances, delta, reason, timestamp, actor)")

    # ----------------------------------------------------
    # 7. Persistence After Database Refresh
    # ----------------------------------------------------
    # Open a fresh database connection directly
    fresh_conn = get_db_connection()
    fresh_cursor = fresh_conn.cursor()
    fresh_cursor.execute("SELECT loyalty_points FROM workers WHERE id = ?", (test_worker_id,))
    persisted_pts = fresh_cursor.fetchone()[0]
    fresh_cursor.execute("SELECT COUNT(*) FROM worker_point_transactions WHERE worker_id = ?", (test_worker_id,))
    persisted_tx_count = fresh_cursor.fetchone()[0]
    fresh_conn.close()

    assert persisted_pts == current_pts, f"Points mismatch after direct DB check: expected {current_pts}, got {persisted_pts}"
    assert persisted_tx_count >= 2, f"Transactions not persisted in SQLite table: count={persisted_tx_count}"
    print(f" [PASS] 7. Persistence verified after independent DB connection refresh (Points={persisted_pts}, Transactions={persisted_tx_count})")

    # ----------------------------------------------------
    # 8. Security & Unauthorized Access Checks
    # ----------------------------------------------------
    # 8a. Unauthenticated access blocked
    unauth_client = app.test_client()
    res_unauth = unauth_client.post(f'/api/admin/workers/{test_worker_id}/adjust-points', json={
        'points': 10,
        'reason': 'Unauthenticated attempt'
    })
    assert res_unauth.status_code == 401, f"Expected 401 for unauthenticated adjustment, got {res_unauth.status_code}"

    # 8b. Citizen attempting to adjust points blocked (403)
    client.post('/api/demo-switch-user', json={'role': 'citizen'})
    res_citizen = client.post(f'/api/admin/workers/{test_worker_id}/adjust-points', json={
        'points': 10,
        'reason': 'Citizen tamper attempt'
    })
    assert res_citizen.status_code == 403, f"Expected 403 for citizen adjustment attempt, got {res_citizen.status_code}"

    # 8c. Worker attempting to adjust points blocked (403)
    client.post('/api/demo-switch-user', json={'role': 'worker'})
    res_worker_tamper = client.post(f'/api/admin/workers/{test_worker_id}/adjust-points', json={
        'points': 50,
        'reason': 'Worker self-award attempt'
    })
    assert res_worker_tamper.status_code == 403, f"Expected 403 for worker adjustment attempt, got {res_worker_tamper.status_code}"

    # 8d. Worker accessing own points via worker endpoint
    res_worker_pts = client.get('/api/worker/loyalty-points')
    assert res_worker_pts.status_code == 200, f"Expected 200 for worker points view, got {res_worker_pts.status_code}"
    w_pts_data = res_worker_pts.get_json()
    assert w_pts_data['success'] is True
    assert 'worker' in w_pts_data and 'transactions' in w_pts_data
    print(" [PASS] 8. Security verified: Unauthenticated=401, Citizen=403, Worker tamper=403, Worker self-view=200")

    # ----------------------------------------------------
    # 9. Prepared Support for -5 Deduction on Rejected Assignment
    # ----------------------------------------------------
    ok, msg, rej_tx = deduct_rejected_assignment_points(test_worker_id, grievance_tracking_id="GRV-TEST-999")
    assert ok is True, f"Prepared helper failed: {msg}"
    assert rej_tx['points_changed'] == -5
    assert "Configured penalty for rejected assignment (GRV-TEST-999)" in rej_tx['reason']
    assert rej_tx['actor_source'] == "SYSTEM"
    print(" [PASS] 9. Prepared support for configurable -5 deduction on rejected assignments verified in isolation")

    # ----------------------------------------------------
    # 10. System-Wide Points Audit Trail Endpoint
    # ----------------------------------------------------
    client.post('/api/demo-switch-user', json={'role': 'admin'})
    all_res = client.get('/api/admin/points-transactions')
    assert all_res.status_code == 200, "System-wide transactions endpoint failed"
    all_data = all_res.get_json()
    assert all_data['success'] is True
    assert len(all_data['transactions']) >= 3, "Expected system audit trail to contain transactions"
    print(f" [PASS] 10. System-wide audit trail endpoint verified ({len(all_data['transactions'])} transactions listed)")

    print("=" * 70)
    print("  ALL 10 TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == '__main__':
    run_tests()
