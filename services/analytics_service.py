"""
GramSeva - Analytics & Reporting Service
Aggregates civic grievance statistics, ward distribution, department performance,
SLA turnaround times, and citizen satisfaction ratings.
All metrics are calculated from actual database records.
"""

from core.database import get_db_connection


def get_analytics_data():
    """Calculates and returns full analytics metrics dictionary."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # -- Status counts (single query) --
    cursor.execute('''
    SELECT status, COUNT(*) as cnt
    FROM grievances
    GROUP BY status
    ''')
    status_counts = {row['status']: row['cnt'] for row in cursor.fetchall()}
    total = sum(status_counts.values())

    submitted = status_counts.get('SUBMITTED', 0)
    under_review = status_counts.get('UNDER_REVIEW', 0)
    assigned = status_counts.get('ASSIGNED', 0)
    in_progress = status_counts.get('IN_PROGRESS', 0)
    work_completed = status_counts.get('WORK_COMPLETED', 0)
    officer_verification = status_counts.get('OFFICER_VERIFICATION', 0)
    citizen_verification = status_counts.get('CITIZEN_VERIFICATION', 0)
    verified = status_counts.get('VERIFIED', 0)
    resolved = status_counts.get('RESOLVED', 0)
    closed = status_counts.get('CLOSED', 0)
    rework = status_counts.get('REWORK_REQUIRED', 0)
    reopened = status_counts.get('REOPENED', 0)
    escalated = status_counts.get('ESCALATED', 0)
    rejected = status_counts.get('REJECTED', 0)

    cursor.execute("SELECT COUNT(*) FROM grievances WHERE priority = 'High' AND status NOT IN ('RESOLVED', 'CLOSED', 'REJECTED')")
    high_priority_active = cursor.fetchone()[0]

    # -- Category breakdown --
    cursor.execute('''
    SELECT category, COUNT(*) as count
    FROM grievances
    GROUP BY category
    ORDER BY count DESC
    ''')
    by_category = [dict(row) for row in cursor.fetchall()]

    # -- Ward breakdown --
    cursor.execute('''
    SELECT ward_number, COUNT(*) as count,
           SUM(CASE WHEN status IN ('RESOLVED', 'CLOSED') THEN 1 ELSE 0 END) as resolved_count
    FROM grievances
    GROUP BY ward_number
    ORDER BY ward_number ASC
    ''')
    by_ward = [dict(row) for row in cursor.fetchall()]

    # -- Priority breakdown --
    cursor.execute('''
    SELECT priority, COUNT(*) as count
    FROM grievances
    GROUP BY priority
    ''')
    by_priority = [dict(row) for row in cursor.fetchall()]

    # -- Feedback --
    cursor.execute("SELECT AVG(star_rating), COUNT(*) FROM feedback")
    fb_row = cursor.fetchone()
    avg_rating = round(fb_row[0], 2) if fb_row[0] else None
    total_ratings = fb_row[1]

    # -- Department performance --
    cursor.execute('''
    SELECT d.name, d.code,
           COUNT(g.id) as total_tickets,
           SUM(CASE WHEN g.status IN ('ASSIGNED', 'IN_PROGRESS', 'WORK_COMPLETED', 'CITIZEN_VERIFICATION') THEN 1 ELSE 0 END) as active_tickets,
           SUM(CASE WHEN g.status IN ('RESOLVED', 'CLOSED') THEN 1 ELSE 0 END) as resolved_tickets
    FROM departments d
    LEFT JOIN grievances g ON d.id = g.department_id
    GROUP BY d.id
    ORDER BY total_tickets DESC
    ''')
    dept_performance = [dict(row) for row in cursor.fetchall()]

    # -- Average resolution time (days) from actual timestamps --
    # A grievance is "resolved" when it reaches RESOLVED or CLOSED.
    # Time = updated_at (when resolved) - created_at (when submitted).
    cursor.execute('''
    SELECT AVG(JULIANDAY(updated_at) - JULIANDAY(created_at)) as avg_days
    FROM grievances
    WHERE status IN ('RESOLVED', 'CLOSED')
      AND updated_at IS NOT NULL AND created_at IS NOT NULL
    ''')
    avg_row = cursor.fetchone()
    avg_resolution_days = round(avg_row['avg_days'], 1) if avg_row and avg_row['avg_days'] else None

    # -- Worker Completion vs Citizen Confirmation --
    # Workers marked completed = distinct grievances that ever reached WORK_COMPLETED
    cursor.execute('''
    SELECT COUNT(DISTINCT grievance_id) FROM grievance_updates
    WHERE to_status = 'WORK_COMPLETED'
    ''')
    workers_marked_completed = cursor.fetchone()[0]

    # Citizens confirmed resolved = distinct grievances where citizen responded YES
    cursor.execute('''
    SELECT COUNT(DISTINCT grievance_id) FROM citizen_verifications
    WHERE response = 'YES'
    ''')
    citizens_confirmed_resolved = cursor.fetchone()[0]

    # -- Verification Failure Rate --
    # Total citizen verification responses
    cursor.execute("SELECT COUNT(*) FROM citizen_verifications")
    total_citizen_responses = cursor.fetchone()[0]

    # Failed = PARTIALLY or NO
    cursor.execute("SELECT COUNT(*) FROM citizen_verifications WHERE response IN ('PARTIALLY', 'NO')")
    failed_citizen_responses = cursor.fetchone()[0]

    if total_citizen_responses > 0:
        verification_failure_rate = round((failed_citizen_responses / total_citizen_responses) * 100, 1)
    else:
        verification_failure_rate = None

    # -- Rework Rate --
    # Rework grievances = distinct grievances that ever entered REWORK_REQUIRED
    cursor.execute('''
    SELECT COUNT(DISTINCT grievance_id) FROM grievance_updates
    WHERE to_status = 'REWORK_REQUIRED'
    ''')
    rework_grievances = cursor.fetchone()[0]

    # Total completed = workers_marked_completed (already calculated)
    if workers_marked_completed > 0:
        rework_rate = round((rework_grievances / workers_marked_completed) * 100, 1)
    else:
        rework_rate = None

    conn.close()

    return {
        'summary': {
            'total': total,
            'submitted': submitted,
            'under_review': under_review,
            'assigned': assigned,
            'in_progress': in_progress,
            'work_completed': work_completed,
            'officer_verification': officer_verification,
            'citizen_verification': citizen_verification,
            'under_verification': officer_verification + citizen_verification,
            'verified': verified,
            'resolved': resolved + closed,
            'closed': closed,
            'rework': rework,
            'reopened': reopened,
            'escalated': escalated,
            'rejected': rejected,
            'high_priority_active': high_priority_active,
            'avg_rating': avg_rating,
            'total_ratings': total_ratings,
            'avg_resolution_days': avg_resolution_days
        },
        'verification': {
            'workers_marked_completed': workers_marked_completed,
            'citizens_confirmed_resolved': citizens_confirmed_resolved,
            'total_citizen_responses': total_citizen_responses,
            'failed_citizen_responses': failed_citizen_responses,
            'verification_failure_rate': verification_failure_rate,
            'rework_grievances': rework_grievances,
            'rework_rate': rework_rate
        },
        'by_category': by_category,
        'by_ward': by_ward,
        'by_priority': by_priority,
        'dept_performance': dept_performance
    }
