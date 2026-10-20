"""
GramSeva - Verification & Telephony IVR Routes
Handles higher officer resolution proof audits, citizen problem-solved confirmations,
and automated outbound telephony IVR verification calls.
"""

import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from core.database import get_db_connection
from core.security import login_required, role_required, mask_phone
from core.constants import (
    CALL_OUTCOMES, CITIZEN_RESPONSES,
    validate_transition, record_status_history, apply_status_transition,
    get_escalation_threshold
)
from services.verification_service import get_verification_service
from services.notification_service import send_notification, notify_admins

verification_bp = Blueprint('verification', __name__, url_prefix='/api')
verification_service = get_verification_service()

def count_failed_verifications(cursor, grievance_id: int) -> int:
    """
    Counts cumulative verification failures on a grievance:
    - Officer audits resulting in REWORK_REQUESTED or REJECTED
    - Citizen verifications resulting in PARTIALLY or NO
    """
    cursor.execute("""
        SELECT COUNT(*) FROM officer_verifications 
        WHERE grievance_id = ? AND decision IN ('REWORK_REQUESTED', 'REJECTED')
    """, (grievance_id,))
    officer_failures = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM citizen_verifications 
        WHERE grievance_id = ? AND response IN ('PARTIALLY', 'NO')
    """, (grievance_id,))
    citizen_failures = cursor.fetchone()[0]

    return officer_failures + citizen_failures

@verification_bp.route('/grievances/<int:grievance_id>/officer-verify', methods=['POST'])
@login_required
@role_required(['officer', 'admin'])
def officer_verify(grievance_id):
    """
    Higher Panchayat Officer reviews resolution proof:
    - APPROVED -> moves to CITIZEN_VERIFICATION
    - REWORK_REQUESTED -> moves to REWORK_REQUIRED
    - REJECTED -> moves to REWORK_REQUIRED with rejection notes
    """
    data = request.json or {}
    decision = data.get('decision')
    remarks = data.get('remarks', '').strip()
    proof_id = data.get('proof_id')

    if decision not in ('APPROVED', 'REWORK_REQUESTED', 'REJECTED'):
        return jsonify({'success': False, 'error': "Decision must be one of: 'APPROVED', 'REWORK_REQUESTED', 'REJECTED'"}), 400

    if not remarks:
        return jsonify({'success': False, 'error': 'Officer verification remarks are mandatory.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM grievances WHERE id = ?", (grievance_id,))
    grievance = cursor.fetchone()

    if not grievance:
        conn.close()
        return jsonify({'success': False, 'error': 'Grievance not found'}), 404

    if grievance['status'] not in ('OFFICER_VERIFICATION', 'WORK_COMPLETED'):
        conn.close()
        return jsonify({
            'success': False,
            'error': f"Officer verification can only be performed when status is WORK_COMPLETED or OFFICER_VERIFICATION (Current: {grievance['status']})."
        }), 400

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    old_status = grievance['status']

    # Auto-resolve latest proof_id if not explicitly provided
    if not proof_id:
        cursor.execute("SELECT id FROM resolution_proofs WHERE grievance_id = ? ORDER BY proof_version DESC, created_at DESC LIMIT 1", (grievance_id,))
        p_row = cursor.fetchone()
        if p_row:
            proof_id = p_row['id']

    # Record officer verification decision (permanent audit record)
    cursor.execute('''
    INSERT INTO officer_verifications (grievance_id, proof_id, officer_id, decision, remarks, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (grievance_id, proof_id, session['user_id'], decision, remarks, now_str))

    # If transitioning from WORK_COMPLETED on approval, step through OFFICER_VERIFICATION
    if old_status == 'WORK_COMPLETED' and decision == 'APPROVED':
        apply_status_transition(
            cursor=cursor,
            grievance_id=grievance_id,
            from_status='WORK_COMPLETED',
            to_status='OFFICER_VERIFICATION',
            remarks=f"Panchayat Officer initiated resolution proof review.",
            user_id=session['user_id'],
            user_role=session.get('role', 'officer'),
            now_str=now_str
        )
        old_status = 'OFFICER_VERIFICATION'

    if decision == 'APPROVED':
        new_status = 'CITIZEN_VERIFICATION'
        audit_msg = f"Officer approved resolution proof: {remarks}. Initiating citizen verification."
        send_notification(
            cursor, grievance['citizen_id'], grievance_id,
            'Resolution Verification Required',
            f"Field work for {grievance['tracking_id']} is reported complete. Please verify if your issue is resolved.", now_str
        )
    elif decision == 'REWORK_REQUESTED':
        total_failures = count_failed_verifications(cursor, grievance_id)
        threshold = get_escalation_threshold()

        if total_failures >= threshold:
            new_status = 'ESCALATED'
            audit_msg = f"Repeated verification failure (#{total_failures}, threshold: {threshold}). Grievance automatically ESCALATED for senior Panchayat administrative oversight. Officer remarks: '{remarks}'."
            notify_admins(
                cursor, grievance_id,
                'Grievance ESCALATED',
                f"Grievance {grievance['tracking_id']} ESCALATED after {total_failures} verification failures. Remarks: {remarks}", now_str
            )
        else:
            new_status = 'REWORK_REQUIRED'
            audit_msg = f"Officer requested rework on proof: {remarks}."

        cursor.execute('''
        UPDATE worker_assignments
        SET assignment_status = 'REWORK_REQUIRED'
        WHERE grievance_id = ? AND assignment_status IN ('COMPLETED', 'ASSIGNED', 'IN_PROGRESS')
        ''', (grievance_id,))
        if grievance['assigned_worker_id']:
            cursor.execute("SELECT user_id FROM workers WHERE id = ?", (grievance['assigned_worker_id'],))
            w_row = cursor.fetchone()
            if w_row:
                send_notification(
                    cursor, w_row['user_id'], grievance_id,
                    'Rework Required on Grievance' if new_status == 'REWORK_REQUIRED' else 'Grievance ESCALATED',
                    f"{'Rework requested' if new_status == 'REWORK_REQUIRED' else 'Escalated'} on {grievance['tracking_id']}: {remarks}", now_str
                )
    else:  # REJECTED
        new_status = 'REJECTED'
        audit_msg = f"Officer rejected resolution proof: {remarks}."

    is_valid, err_msg, status_code = validate_transition(
        current_status=old_status,
        new_status=new_status,
        user_role=session.get('role', 'officer'),
        remarks=audit_msg
    )
    if not is_valid:
        conn.close()
        return jsonify({'success': False, 'error': err_msg}), status_code

    apply_status_transition(
        cursor=cursor,
        grievance_id=grievance_id,
        from_status=old_status,
        to_status=new_status,
        remarks=audit_msg,
        user_id=session['user_id'],
        user_role=session.get('role', 'officer'),
        now_str=now_str
    )

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f'Officer verification recorded. Status updated to {new_status}.',
        'decision': decision,
        'status': new_status
    })

@verification_bp.route('/grievances/<int:grievance_id>/citizen-verify', methods=['POST'])
@login_required
def citizen_verify(grievance_id):
    """
    Submitting citizen verifies whether the actual civic issue is resolved:
    Responses: YES | PARTIALLY | NO | UNABLE_TO_VERIFY
    Call outcomes: ANSWERED | NO_ANSWER | BUSY | INVALID_NUMBER | FAILED
    Rules:
    - NO_ANSWER must never be interpreted as NO.
    - YES transitions status to VERIFIED.
    - PARTIALLY / NO triggers REWORK_REQUIRED or REOPENED.
    - UNABLE_TO_VERIFY remains pending in CITIZEN_VERIFICATION.
    - Every verification attempt is permanently recorded.
    """
    data = request.json or {}
    response = data.get('response')
    call_outcome = data.get('call_outcome', 'ANSWERED')
    method = data.get('verification_method', 'PORTAL')
    remarks = data.get('remarks', '').strip()

    if call_outcome not in CALL_OUTCOMES:
        return jsonify({'success': False, 'error': f'Invalid call outcome. Allowed: {CALL_OUTCOMES}'}), 400

    if call_outcome == 'ANSWERED' and response not in CITIZEN_RESPONSES:
        return jsonify({'success': False, 'error': f'Invalid citizen response. Allowed: {CITIZEN_RESPONSES}'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT g.*, u.mobile as citizen_mobile
    FROM grievances g
    JOIN users u ON g.citizen_id = u.id
    WHERE g.id = ?
    ''', (grievance_id,))
    grievance = cursor.fetchone()

    if not grievance:
        conn.close()
        return jsonify({'success': False, 'error': 'Grievance not found'}), 404

    current_uid = session.get('user_id')
    current_role = session.get('role')
    is_authorized = (current_uid == grievance['citizen_id'] or current_role in ('officer', 'admin'))
    if not is_authorized:
        conn.close()
        return jsonify({'success': False, 'error': 'Only the complainant citizen or verifying Panchayat official can submit verification.'}), 403

    if grievance['status'] != 'CITIZEN_VERIFICATION':
        conn.close()
        return jsonify({'success': False, 'error': f"Citizen verification can only be executed in CITIZEN_VERIFICATION state (Current: {grievance['status']})."}), 400

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT COUNT(*) FROM citizen_verifications WHERE grievance_id = ?", (grievance_id,))
    attempt_num = cursor.fetchone()[0] + 1

    contact_num = grievance['citizen_mobile'] or 'N/A'
    effective_response = response if call_outcome == 'ANSWERED' else None
    
    # Accurate requested_timestamp from grievance_updates when transitioned to CITIZEN_VERIFICATION
    cursor.execute('''
        SELECT created_at FROM grievance_updates 
        WHERE grievance_id = ? AND to_status = 'CITIZEN_VERIFICATION' 
        ORDER BY created_at DESC LIMIT 1
    ''', (grievance_id,))
    req_row = cursor.fetchone()
    requested_timestamp = req_row['created_at'] if req_row else (grievance['updated_at'] or grievance['created_at'])

    # Map verification status label
    verif_status_map = {
        'YES': 'CONFIRMED_SOLVED',
        'PARTIALLY': 'PARTIALLY_SOLVED',
        'NO': 'PROBLEM_PERSISTS',
        'UNABLE_TO_VERIFY': 'PENDING_RETRY'
    }
    verif_status = verif_status_map.get(response, 'COMPLETED')

    # 1. Record in verification_attempts table
    masked_phone = mask_phone(contact_num)
    attempt_status = 'COMPLETED' if call_outcome == 'ANSWERED' else ('PENDING_RETRY' if call_outcome in ('NO_ANSWER', 'BUSY') else 'FAILED')
    portal_prov_ref = f"PORTAL-VERIF-{uuid.uuid4().hex[:8].upper()}"

    cursor.execute('''
    INSERT INTO verification_attempts (
        grievance_id, citizen_id, phone_number_ref, phone_ref, attempt_number,
        contact_number, method, call_outcome, citizen_response, requested_time,
        response_time, provider_ref, status, remarks, attempted_by_user_id, attempted_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        grievance_id, grievance['citizen_id'], masked_phone, masked_phone, attempt_num,
        masked_phone, method, call_outcome, effective_response, requested_timestamp,
        now_str, portal_prov_ref, attempt_status, remarks, current_uid, now_str
    ))

    old_status = grievance['status']
    new_status = old_status

    if call_outcome != 'ANSWERED':
        audit_note = f"Verification Attempt #{attempt_num} ({method}): Outcome '{call_outcome}'. Grievance remains pending verification."
    else:
        cursor.execute('''
        INSERT INTO citizen_verifications (
            grievance_id, citizen_id, attempt_number, method, verification_method,
            response, remarks, requested_timestamp, response_timestamp,
            verification_status, call_outcome, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            grievance_id, grievance['citizen_id'], attempt_num, method, method,
            response, remarks, requested_timestamp, now_str,
            verif_status, call_outcome, now_str
        ))

        if response == 'YES':
            new_status = 'VERIFIED'
            audit_note = f"Citizen verified resolution: YES - Problem completely solved. Remarks: '{remarks}'."
            # Notify officer that citizen confirmed problem is solved
            if grievance['assigned_officer_id']:
                cursor.execute("SELECT user_id FROM officers WHERE id = ?", (grievance['assigned_officer_id'],))
                o_row = cursor.fetchone()
                if o_row:
                    send_notification(
                        cursor, o_row['user_id'], grievance_id,
                        'Citizen Resolution Confirmed',
                        f"Citizen confirmed resolution for {grievance['tracking_id']}. Issue is VERIFIED and ready for final administrative resolution.", now_str
                    )
        elif response in ('PARTIALLY', 'NO'):
            total_failures = count_failed_verifications(cursor, grievance_id)
            threshold = get_escalation_threshold()

            cursor.execute('''
            UPDATE worker_assignments
            SET assignment_status = 'REWORK_REQUIRED'
            WHERE grievance_id = ?
            ''', (grievance_id,))

            if total_failures >= threshold:
                new_status = 'ESCALATED'
                audit_note = f"Citizen verification failed ({response}): Repeated failure threshold reached ({total_failures}/{threshold}). Grievance automatically ESCALATED for senior administrative oversight. Remarks: '{remarks}'."
                notify_admins(
                    cursor, grievance_id,
                    'Grievance ESCALATED',
                    f"Grievance {grievance['tracking_id']} ESCALATED: Citizen reported '{response}' (Failure #{total_failures}/{threshold}). Remarks: {remarks}", now_str
                )
                send_notification(
                    cursor, grievance['citizen_id'], grievance_id,
                    'Grievance Escalated to Senior Authority',
                    f"Your grievance {grievance['tracking_id']} has been ESCALATED to higher Panchayat authority for priority resolution.", now_str
                )
                if grievance['assigned_worker_id']:
                    cursor.execute("SELECT user_id FROM workers WHERE id = ?", (grievance['assigned_worker_id'],))
                    w_row = cursor.fetchone()
                    if w_row:
                        send_notification(
                            cursor, w_row['user_id'], grievance_id,
                            'Grievance ESCALATED',
                            f"Grievance {grievance['tracking_id']} ESCALATED after citizen reported '{response}': {remarks}", now_str
                        )
            else:
                if response == 'PARTIALLY':
                    new_status = 'REWORK_REQUIRED'
                    audit_note = f"Citizen verification: PARTIALLY solved. Rework required. Remarks: '{remarks}'."
                    if grievance['assigned_worker_id']:
                        cursor.execute("SELECT user_id FROM workers WHERE id = ?", (grievance['assigned_worker_id'],))
                        w_row = cursor.fetchone()
                        if w_row:
                            send_notification(
                                cursor, w_row['user_id'], grievance_id,
                                'Citizen Verification: Partial Fix',
                                f"Citizen reported problem is only PARTIALLY solved on {grievance['tracking_id']}: {remarks}", now_str
                            )
                else:  # NO
                    desired_status = data.get('desired_status')
                    new_status = 'REWORK_REQUIRED' if desired_status == 'REWORK_REQUIRED' else 'REOPENED'
                    audit_note = f"Citizen verification: NO - Problem still exists. Status updated to {new_status}. Remarks: '{remarks}'."
                    if grievance['assigned_worker_id']:
                        cursor.execute("SELECT user_id FROM workers WHERE id = ?", (grievance['assigned_worker_id'],))
                        w_row = cursor.fetchone()
                        if w_row:
                            send_notification(
                                cursor, w_row['user_id'], grievance_id,
                                'Citizen Verification: Problem Persists',
                                f"Citizen reported problem STILL EXISTS on {grievance['tracking_id']}: {remarks}", now_str
                            )
        else:  # UNABLE_TO_VERIFY
            new_status = 'CITIZEN_VERIFICATION'
            audit_note = f"Citizen verification: UNABLE_TO_VERIFY. Status remains pending further verification. Remarks: '{remarks}'."

    if new_status != old_status:
        apply_status_transition(
            cursor=cursor,
            grievance_id=grievance_id,
            from_status=old_status,
            to_status=new_status,
            remarks=audit_note,
            user_id=current_uid,
            user_role=current_role,
            now_str=now_str
        )
    else:
        cursor.execute("UPDATE grievances SET updated_at = ? WHERE id = ?", (now_str, grievance_id))
        record_status_history(
            cursor=cursor,
            grievance_id=grievance_id,
            from_status=old_status,
            to_status=new_status,
            remarks=audit_note,
            user_id=current_uid,
            user_role=current_role,
            created_at=now_str
        )

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f"Verification recorded. Call outcome: {call_outcome}, Response: {effective_response or 'None'}. New Status: {new_status}",
        'status': new_status,
        'call_outcome': call_outcome,
        'citizen_response': effective_response
    })

@verification_bp.route('/grievances/<int:grievance_id>/trigger-verification-call', methods=['POST'])
@login_required
@role_required(['officer', 'admin'])
def trigger_verification_call(grievance_id):
    """
    Officer triggers outbound automated verification call via verification service abstraction.
    Clearly labeled: Development / Mock Verification
    Supports simulated telephony outcomes in development without external carrier charges.
    Never interprets NO_ANSWER as NO.
    Stores complete verification request metadata without exposing citizen PII.
    """
    data = request.json or {}
    simulated_outcome = data.get('simulated_outcome')
    simulated_response = data.get('simulated_response')
    remarks = data.get('remarks', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT g.*, u.mobile as citizen_mobile
    FROM grievances g
    JOIN users u ON g.citizen_id = u.id
    WHERE g.id = ?
    ''', (grievance_id,))
    grievance = cursor.fetchone()

    if not grievance:
        conn.close()
        return jsonify({'success': False, 'error': 'Grievance not found'}), 404

    if grievance['status'] != 'CITIZEN_VERIFICATION':
        conn.close()
        return jsonify({'success': False, 'error': f"Telephony verification requires CITIZEN_VERIFICATION status (Current: {grievance['status']})."}), 400

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT COUNT(*) FROM verification_attempts WHERE grievance_id = ?", (grievance_id,))
    attempt_num = cursor.fetchone()[0] + 1

    # Accurate requested timestamp from when ticket entered CITIZEN_VERIFICATION
    cursor.execute('''
        SELECT created_at FROM grievance_updates 
        WHERE grievance_id = ? AND to_status = 'CITIZEN_VERIFICATION' 
        ORDER BY created_at DESC LIMIT 1
    ''', (grievance_id,))
    req_row = cursor.fetchone()
    requested_ts = req_row['created_at'] if req_row else (grievance['updated_at'] or grievance['created_at'])

    call_result = verification_service.trigger_citizen_verification_call(
        grievance_id=grievance_id,
        contact_number=grievance['citizen_mobile'],
        citizen_id=grievance['citizen_id'],
        attempt_number=attempt_num,
        requested_time=requested_ts,
        simulated_outcome=simulated_outcome,
        simulated_response=simulated_response,
        remarks=remarks
    )

    masked_phone = mask_phone(grievance['citizen_mobile'])

    cursor.execute('''
    INSERT INTO verification_attempts (
        grievance_id, citizen_id, phone_number_ref, phone_ref, attempt_number,
        contact_number, method, call_outcome, citizen_response, requested_time,
        response_time, provider_ref, status, remarks, attempted_by_user_id, attempted_at
    ) VALUES (?, ?, ?, ?, ?, ?, 'IVR', ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        grievance_id, grievance['citizen_id'], masked_phone, masked_phone, attempt_num,
        masked_phone, call_result.call_outcome, call_result.citizen_response,
        call_result.requested_time, call_result.response_time, call_result.provider_ref,
        call_result.status, call_result.remarks, session['user_id'], now_str
    ))

    old_status = grievance['status']
    new_status = old_status

    if call_result.call_outcome == 'ANSWERED':
        cursor.execute("SELECT COUNT(*) FROM citizen_verifications WHERE grievance_id = ?", (grievance_id,))
        ivr_attempt_num = cursor.fetchone()[0] + 1
        ivr_status_map = {
            'YES': 'CONFIRMED_SOLVED',
            'PARTIALLY': 'PARTIALLY_SOLVED',
            'NO': 'PROBLEM_PERSISTS',
            'UNABLE_TO_VERIFY': 'PENDING_RETRY'
        }
        ivr_verif_status = ivr_status_map.get(call_result.citizen_response, 'COMPLETED')

        cursor.execute('''
        INSERT INTO citizen_verifications (
            grievance_id, citizen_id, attempt_number, method, verification_method,
            response, remarks, requested_timestamp, response_timestamp,
            verification_status, call_outcome, created_at
        ) VALUES (?, ?, ?, 'IVR', 'IVR', ?, ?, ?, ?, ?, 'ANSWERED', ?)
        ''', (
            grievance_id, grievance['citizen_id'], ivr_attempt_num,
            call_result.citizen_response, call_result.remarks,
            requested_ts, now_str, ivr_verif_status, now_str
        ))

        if call_result.citizen_response == 'YES':
            new_status = 'VERIFIED'
        elif call_result.citizen_response in ('PARTIALLY', 'NO'):
            ivr_failures = count_failed_verifications(cursor, grievance_id)
            ivr_threshold = get_escalation_threshold()
            if ivr_failures >= ivr_threshold:
                new_status = 'ESCALATED'
            elif call_result.citizen_response == 'PARTIALLY':
                new_status = 'REWORK_REQUIRED'
            else:
                new_status = 'REOPENED'
        else:
            new_status = 'CITIZEN_VERIFICATION'

    if new_status != old_status:
        apply_status_transition(
            cursor=cursor,
            grievance_id=grievance_id,
            from_status=old_status,
            to_status=new_status,
            remarks=f"[Telephony IVR] {call_result.remarks}",
            user_id=session['user_id'],
            user_role=session.get('role', 'officer'),
            now_str=now_str
        )
    else:
        cursor.execute("UPDATE grievances SET updated_at = ? WHERE id = ?", (now_str, grievance_id))
        record_status_history(
            cursor=cursor,
            grievance_id=grievance_id,
            from_status=old_status,
            to_status=new_status,
            remarks=f"[Telephony IVR] {call_result.remarks}",
            user_id=session['user_id'],
            user_role=session.get('role', 'officer'),
            created_at=now_str
        )

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f"Telephony call concluded. Outcome: {call_result.call_outcome}. New Status: {new_status}",
        'call_result': call_result.to_dict(),
        'verification_request': call_result.to_dict(),
        'status': new_status,
        'provider_label': 'Development / Mock Verification'
    })


@verification_bp.route('/grievances/<int:grievance_id>/verification-requests', methods=['GET'])
@login_required
def get_verification_requests(grievance_id):
    """
    Retrieves all phone/IVR verification requests for a grievance.
    Stores & returns:
    - grievance ID
    - citizen ID
    - phone number reference (masked)
    - attempt number
    - requested time
    - call outcome
    - citizen response
    - response time
    - provider reference
    - status
    Masks citizen contact numbers to protect citizen privacy.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT citizen_id FROM grievances WHERE id = ?", (grievance_id,))
    grow = cursor.fetchone()
    if not grow:
        conn.close()
        return jsonify({'success': False, 'error': 'Grievance not found'}), 404

    current_uid = session.get('user_id')
    current_role = session.get('role')
    if current_role == 'citizen' and current_uid != grow['citizen_id']:
        conn.close()
        return jsonify({'success': False, 'error': 'Unauthorized to view verification requests for this grievance.'}), 403

    cursor.execute('''
    SELECT 
        id, grievance_id, citizen_id, 
        COALESCE(phone_number_ref, phone_ref, contact_number) as phone_number_ref,
        attempt_number, requested_time, call_outcome, citizen_response, 
        response_time, provider_ref, status, remarks, attempted_at
    FROM verification_attempts
    WHERE grievance_id = ?
    ORDER BY attempt_number DESC, id DESC
    ''', (grievance_id,))
    
    requests_list = []
    for r in cursor.fetchall():
        r_dict = dict(r)
        r_dict['phone_number_ref'] = mask_phone(r_dict.get('phone_number_ref') or '')
        r_dict['phone_ref'] = r_dict['phone_number_ref']
        requests_list.append(r_dict)
        
    conn.close()
    return jsonify({
        'success': True, 
        'verification_requests': requests_list,
        'count': len(requests_list),
        'provider_label': 'Development / Mock Verification'
    })
