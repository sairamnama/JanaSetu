"""
GramSeva - System Constants & Invariants
Defines the authoritative Grievance Lifecycle Status Machine,
Allowed State Transitions, and Verification Constants.
"""

# ==========================================
# STATUS MACHINE SPECIFICATIONS & RULES
# ==========================================
VALID_STATUSES = [
    'SUBMITTED', 'UNDER_REVIEW', 'ACCEPTED', 'ASSIGNED', 'IN_PROGRESS',
    'WORK_COMPLETED', 'OFFICER_VERIFICATION', 'CITIZEN_VERIFICATION',
    'VERIFIED', 'RESOLVED', 'CLOSED',
    'REWORK_REQUIRED', 'REOPENED', 'ESCALATED', 'REJECTED'
]

VALID_TRANSITIONS = {
    'SUBMITTED': ['UNDER_REVIEW', 'ACCEPTED', 'ASSIGNED'],
    'UNDER_REVIEW': ['ACCEPTED', 'ASSIGNED', 'REJECTED'],
    'ACCEPTED': ['ASSIGNED', 'IN_PROGRESS', 'ESCALATED', 'REJECTED'],
    'ASSIGNED': ['ACCEPTED', 'IN_PROGRESS', 'SUBMITTED', 'ESCALATED', 'REJECTED'],
    'IN_PROGRESS': ['WORK_COMPLETED', 'ESCALATED', 'REWORK_REQUIRED'],
    'WORK_COMPLETED': ['OFFICER_VERIFICATION', 'REWORK_REQUIRED', 'ESCALATED'],
    'OFFICER_VERIFICATION': ['CITIZEN_VERIFICATION', 'REWORK_REQUIRED', 'REJECTED', 'ESCALATED'],
    'CITIZEN_VERIFICATION': ['VERIFIED', 'REWORK_REQUIRED', 'REOPENED', 'ESCALATED'],
    'VERIFIED': ['RESOLVED', 'REWORK_REQUIRED', 'REOPENED'],
    'RESOLVED': ['CLOSED', 'REOPENED'],
    'CLOSED': ['REOPENED'],
    'REWORK_REQUIRED': ['ASSIGNED', 'IN_PROGRESS', 'WORK_COMPLETED', 'ESCALATED'],
    'REOPENED': ['UNDER_REVIEW', 'ASSIGNED', 'IN_PROGRESS', 'WORK_COMPLETED', 'ESCALATED'],
    'ESCALATED': ['ASSIGNED', 'IN_PROGRESS', 'OFFICER_VERIFICATION', 'REWORK_REQUIRED', 'WORK_COMPLETED'],
    'REJECTED': ['REOPENED']
}

# ==========================================
# ESCALATION CONFIGURATION & THRESHOLDS
# ==========================================
# Verification failure escalation threshold:
# When a grievance experiences repeated failed verifications (Officer REWORK_REQUESTED/REJECTED
# or Citizen PARTIALLY/NO), it is automatically flagged and transitioned to ESCALATED for senior
# Panchayat administrative oversight.
#
# Configurable via environment variable: GRAMSEVA_ESCALATION_THRESHOLD (or ESCALATION_THRESHOLD).
# Default: 2 (1st failed verification -> REWORK_REQUIRED / REOPENED;
#             2nd and subsequent failed verifications -> ESCALATED).
DEFAULT_ESCALATION_THRESHOLD = 2

def get_escalation_threshold():
    """Returns the configurable verification failure escalation threshold."""
    import os
    raw = os.getenv('GRAMSEVA_ESCALATION_THRESHOLD') or os.getenv('ESCALATION_THRESHOLD')
    if raw:
        try:
            return max(1, int(raw))
        except (ValueError, TypeError):
            pass
    return DEFAULT_ESCALATION_THRESHOLD

# ==========================================
# ROLE-BASED TRANSITION MATRIX
# ==========================================
ROLE_ALLOWED_TRANSITIONS = {
    'admin': None,
    'officer': {
        ('SUBMITTED', 'UNDER_REVIEW'),
        ('SUBMITTED', 'ASSIGNED'),
        ('UNDER_REVIEW', 'ACCEPTED'),
        ('UNDER_REVIEW', 'ASSIGNED'),
        ('UNDER_REVIEW', 'REJECTED'),
        ('UNDER_REVIEW', 'ESCALATED'),
        ('ACCEPTED', 'ASSIGNED'),
        ('ACCEPTED', 'IN_PROGRESS'),
        ('ACCEPTED', 'ESCALATED'),
        ('ACCEPTED', 'REJECTED'),
        ('ASSIGNED', 'ACCEPTED'),
        ('ASSIGNED', 'ESCALATED'),
        ('ASSIGNED', 'REJECTED'),
        ('IN_PROGRESS', 'WORK_COMPLETED'),
        ('IN_PROGRESS', 'ESCALATED'),
        ('WORK_COMPLETED', 'OFFICER_VERIFICATION'),
        ('WORK_COMPLETED', 'REWORK_REQUIRED'),
        ('WORK_COMPLETED', 'ESCALATED'),
        ('OFFICER_VERIFICATION', 'CITIZEN_VERIFICATION'),
        ('OFFICER_VERIFICATION', 'REWORK_REQUIRED'),
        ('OFFICER_VERIFICATION', 'REJECTED'),
        ('OFFICER_VERIFICATION', 'ESCALATED'),
        ('CITIZEN_VERIFICATION', 'VERIFIED'),
        ('CITIZEN_VERIFICATION', 'REWORK_REQUIRED'),
        ('CITIZEN_VERIFICATION', 'REOPENED'),
        ('CITIZEN_VERIFICATION', 'ESCALATED'),
        ('VERIFIED', 'RESOLVED'),
        ('REWORK_REQUIRED', 'ASSIGNED'),
        ('REWORK_REQUIRED', 'IN_PROGRESS'),
        ('REWORK_REQUIRED', 'ESCALATED'),
        ('REOPENED', 'UNDER_REVIEW'),
        ('REOPENED', 'ASSIGNED'),
        ('REOPENED', 'IN_PROGRESS'),
        ('REOPENED', 'ESCALATED'),
        ('ESCALATED', 'ASSIGNED'),
        ('ESCALATED', 'IN_PROGRESS'),
        ('ESCALATED', 'OFFICER_VERIFICATION'),
        ('ESCALATED', 'REWORK_REQUIRED'),
        ('ESCALATED', 'WORK_COMPLETED'),
        ('REJECTED', 'REOPENED'),
        ('RESOLVED', 'REOPENED'),
        ('CLOSED', 'REOPENED'),
    },
    'worker': {
        ('ASSIGNED', 'ACCEPTED'),
        ('ASSIGNED', 'SUBMITTED'),
        ('ASSIGNED', 'IN_PROGRESS'),
        ('ACCEPTED', 'IN_PROGRESS'),
        ('ACCEPTED', 'ACCEPTED'),
        ('IN_PROGRESS', 'IN_PROGRESS'),
        ('IN_PROGRESS', 'WORK_COMPLETED'),
        ('REWORK_REQUIRED', 'IN_PROGRESS'),
        ('REWORK_REQUIRED', 'WORK_COMPLETED'),
        ('REOPENED', 'IN_PROGRESS'),
        ('REOPENED', 'WORK_COMPLETED'),
        ('ESCALATED', 'IN_PROGRESS'),
        ('ESCALATED', 'WORK_COMPLETED'),
    },
    'citizen': {
        ('CITIZEN_VERIFICATION', 'VERIFIED'),
        ('CITIZEN_VERIFICATION', 'REWORK_REQUIRED'),
        ('CITIZEN_VERIFICATION', 'REOPENED'),
        ('CITIZEN_VERIFICATION', 'ESCALATED'),
        ('RESOLVED', 'CLOSED'),
        ('RESOLVED', 'REOPENED'),
        ('CLOSED', 'REOPENED'),
        ('REJECTED', 'REOPENED'),
    }
}


def validate_transition(current_status, new_status, user_role=None, remarks=None, resolution_notes=None):
    """Validates whether a grievance can transition from current_status to new_status."""
    if new_status not in VALID_STATUSES:
        return False, f"Invalid status '{new_status}'. Allowed statuses: {VALID_STATUSES}", 400

    if not remarks or not str(remarks).strip():
        return False, "Remarks are mandatory for all status transitions.", 400

    if user_role == 'worker' and new_status in ('RESOLVED', 'CLOSED', 'VERIFIED', 'UNDER_REVIEW', 'OFFICER_VERIFICATION'):
        return False, "Workers are strictly forbidden from marking grievances as RESOLVED, CLOSED, or VERIFIED.", 403

    if user_role == 'citizen' and new_status in ('RESOLVED', 'ACCEPTED', 'ASSIGNED', 'IN_PROGRESS', 'WORK_COMPLETED', 'OFFICER_VERIFICATION'):
        return False, "Citizens are strictly forbidden from resolving grievances or making administrative status changes.", 403

    # Allow worker progress updates when already IN_PROGRESS
    if current_status == new_status:
        if user_role == 'worker' and current_status == 'IN_PROGRESS':
            return True, None, 200
        return False, f"Grievance is already in '{current_status}' status.", 400

    allowed_next = VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed_next:
        return False, f"Invalid status transition from '{current_status}' to '{new_status}'. Allowed transitions from '{current_status}': {allowed_next}", 400

    if user_role and user_role in ROLE_ALLOWED_TRANSITIONS:
        allowed_pairs = ROLE_ALLOWED_TRANSITIONS[user_role]
        if allowed_pairs is not None and (current_status, new_status) not in allowed_pairs:
            return False, f"Role '{user_role}' is not authorized to transition grievance from '{current_status}' to '{new_status}'.", 403


    if new_status == 'RESOLVED' and (not resolution_notes or not str(resolution_notes).strip()):
        return False, "Resolution summary notes are mandatory when marking grievance as RESOLVED.", 400

    return True, None, 200


def record_status_history(cursor, grievance_id, from_status, to_status, remarks, user_id, user_role=None, created_at=None):
    """Records an immutable audit trail entry in grievance_updates."""
    from datetime import datetime
    if created_at is None:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
    INSERT INTO grievance_updates (
        grievance_id, from_status, to_status, remarks,
        updated_by_user_id, user_role, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (grievance_id, from_status, to_status, remarks.strip(), user_id, user_role, created_at))


def apply_status_transition(cursor, grievance_id, from_status, to_status, remarks, user_id, user_role, resolution_notes=None, now_str=None):
    """Applies the validated status transition and appends to status history."""
    from datetime import datetime
    if now_str is None:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if to_status == 'RESOLVED' and resolution_notes:
        cursor.execute('''
        UPDATE grievances
        SET status = ?, resolution_notes = ?, updated_at = ?
        WHERE id = ?
        ''', (to_status, resolution_notes.strip(), now_str, grievance_id))
    else:
        cursor.execute('''
        UPDATE grievances
        SET status = ?, updated_at = ?
        WHERE id = ?
        ''', (to_status, now_str, grievance_id))

    record_status_history(
        cursor=cursor,
        grievance_id=grievance_id,
        from_status=from_status,
        to_status=to_status,
        remarks=remarks,
        user_id=user_id,
        user_role=user_role,
        created_at=now_str
    )

# ==========================================
# VERIFICATION ENUMS & OUTCOMES
# ==========================================
CALL_OUTCOMES = ['ANSWERED', 'NO_ANSWER', 'BUSY', 'INVALID_NUMBER', 'FAILED']
CITIZEN_RESPONSES = ['YES', 'PARTIALLY', 'NO', 'UNABLE_TO_VERIFY']
VERIFICATION_METHODS = ['PORTAL', 'IVR', 'PHONE_CALL', 'IN_PERSON']

# ==========================================
# CATEGORY TO DEPARTMENT CODE MAPPING
# ==========================================
CATEGORY_DEPARTMENT_MAP = {
    'Drinking Water & Supply': 'WAT',
    'Electricity & Streetlights': 'ELEC',
    'Waste Management & Sanitation': 'SAN',
    'Roads & Drainage Systems': 'ROAD',
    'Public Health & Vector Control': 'HLTH',
    'Anganwadi & School Civic Issues': 'EDU',
    'Rural Housing & Infrastructure': 'GEN',
    'Other Civic & Community Issues': 'GEN'
}

# Allowed system roles
SYSTEM_ROLES = ['citizen', 'worker', 'officer', 'admin']
