"""
GramSeva - Worker Loyalty Points Service
Handles loyalty points adjustments, balance integrity, transaction audit trails,
and concurrency-safe atomic persistence.
"""

import threading
from typing import Tuple, Dict, Any, List, Optional
from core.database import get_db_connection
from core.config import (
    INITIAL_WORKER_POINTS,
    MIN_WORKER_POINTS,
    LOYALTY_POINTS_CONFIG,
    REJECTED_ASSIGNMENT_PENALTY_POINTS
)

# Concurrency lock to serialize points adjustments within process
_points_lock = threading.Lock()

def get_worker_points_summary(worker_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves current loyalty points balance and profile information for a worker.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT w.id as worker_id, w.badge_id, w.skill_trade, w.loyalty_points,
               u.id as user_id, u.full_name, u.mobile,
               d.name as department_name, d.code as department_code
        FROM workers w
        JOIN users u ON w.user_id = u.id
        LEFT JOIN departments d ON w.department_id = d.id
        WHERE w.id = ?
    ''', (worker_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def get_worker_transactions(worker_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves complete points transaction history for a specific worker.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.id, t.worker_id, t.previous_balance, t.points_changed, t.new_balance,
               t.reason, t.actor_id, t.actor_source, t.created_at,
               u.full_name as actor_name
        FROM worker_point_transactions t
        LEFT JOIN users u ON t.actor_id = u.id
        WHERE t.worker_id = ?
        ORDER BY t.created_at DESC, t.id DESC
        LIMIT ?
    ''', (worker_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_points_transactions(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves complete points transaction history across all workers for administrative audit.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.id, t.worker_id, t.previous_balance, t.points_changed, t.new_balance,
               t.reason, t.actor_id, t.actor_source, t.created_at,
               w.badge_id as worker_badge,
               wu.full_name as worker_name,
               d.name as department_name,
               au.full_name as actor_name
        FROM worker_point_transactions t
        JOIN workers w ON t.worker_id = w.id
        JOIN users wu ON w.user_id = wu.id
        LEFT JOIN departments d ON w.department_id = d.id
        LEFT JOIN users au ON t.actor_id = au.id
        ORDER BY t.created_at DESC, t.id DESC
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def adjust_worker_points(
    worker_id: int,
    points_delta: int,
    reason: str,
    actor_id: Optional[int] = None,
    actor_source: str = "Admin"
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Atomically adjusts a worker's loyalty points and records a transaction history item.
    Enforces minimum balance, valid delta, non-empty reason, and concurrency safety.
    """
    # 1. Input Validation
    if not isinstance(points_delta, int):
        try:
            points_delta = int(points_delta)
        except (ValueError, TypeError):
            return False, "Points adjustment must be a valid integer number.", None

    if points_delta == 0:
        return False, "Points adjustment amount cannot be zero.", None

    clean_reason = (reason or "").strip()
    if not clean_reason:
        return False, "A mandatory reason must be provided for adjusting loyalty points.", None

    allow_negative = LOYALTY_POINTS_CONFIG.get('ALLOW_NEGATIVE', False)
    min_points = LOYALTY_POINTS_CONFIG.get('MIN_POINTS', 0)

    # 2. Concurrency Lock & Database Transaction
    with _points_lock:
        conn = get_db_connection()
        try:
            # Begin immediate write lock transaction
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            # Fetch current balance
            cursor.execute("SELECT id, loyalty_points FROM workers WHERE id = ?", (worker_id,))
            worker = cursor.fetchone()
            if not worker:
                conn.rollback()
                return False, f"Worker record (ID: {worker_id}) not found.", None

            previous_balance = worker['loyalty_points']
            if previous_balance is None:
                previous_balance = INITIAL_WORKER_POINTS

            new_balance = previous_balance + points_delta

            # 3. Balance Integrity Guardrail
            if not allow_negative and new_balance < min_points:
                conn.rollback()
                return False, (
                    f"Insufficient points balance: cannot reduce below minimum limit of {min_points} points. "
                    f"Current balance is {previous_balance}, requested adjustment was {points_delta}."
                ), None

            # 4. Atomic Updates
            cursor.execute("UPDATE workers SET loyalty_points = ? WHERE id = ?", (new_balance, worker_id))
            cursor.execute('''
                INSERT INTO worker_point_transactions 
                (worker_id, previous_balance, points_changed, new_balance, reason, actor_id, actor_source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (worker_id, previous_balance, points_delta, new_balance, clean_reason, actor_id, actor_source))

            tx_id = cursor.lastrowid
            conn.commit()

            tx_record = {
                'id': tx_id,
                'worker_id': worker_id,
                'previous_balance': previous_balance,
                'points_changed': points_delta,
                'new_balance': new_balance,
                'reason': clean_reason,
                'actor_id': actor_id,
                'actor_source': actor_source
            }
            return True, "Points adjusted successfully.", tx_record

        except Exception as e:
            conn.rollback()
            return False, f"Database transaction error: {str(e)}", None
        finally:
            conn.close()

def deduct_rejected_assignment_points(
    worker_id: int,
    grievance_tracking_id: Optional[str] = None,
    actor_source: str = "SYSTEM"
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Prepared support for configurable penalty deduction for rejected assignments.
    # ponytail: helper configured with REJECTED_ASSIGNMENT_PENALTY; do not trigger automatically yet.
    """
    penalty = REJECTED_ASSIGNMENT_PENALTY_POINTS
    reason = (
        f"Configured penalty for rejected assignment ({grievance_tracking_id})"
        if grievance_tracking_id else "Configured penalty for rejected assignment"
    )
    return adjust_worker_points(
        worker_id=worker_id,
        points_delta=penalty,
        reason=reason,
        actor_id=None,
        actor_source=actor_source
    )
