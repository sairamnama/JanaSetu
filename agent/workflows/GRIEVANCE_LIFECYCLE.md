# GramSeva Grievance Lifecycle & Verification Workflow

## Overview
GramSeva enforces a multi-tier, verifiable lifecycle for civic grievances. It bridges citizens, field workers, supervising officers, and the Panchayat administration to guarantee genuine issue remediation.

---

## 1. Visual State Transition Machine

```
[SUBMITTED] 
    │
    ├───(Invalid / Out of Scope)────────► [REJECTED] (Mandatory reason)
    │
    ▼ (Panchayat Verification)
[UNDER_REVIEW]
    │
    ▼ (Route to Department & Dispatch Officer/Worker)
[ASSIGNED]
    │
    ▼ (Field Work Started)
[IN_PROGRESS]
    │
    ▼ (Worker Uploads Photographic Proof & Notes)
[WORK_COMPLETED]
    │
    ├───(Officer Rejection)──────────────► [REWORK_REQUIRED] ──┐
    │                                          ▲               │
    ▼ (Officer Approves Proof)                 │               │
[CITIZEN_VERIFICATION]                         │ (Partially)   ▼
    │                                          │          (Re-assigned)
    ├───(Citizen: PARTIALLY) ──────────────────┘          [IN_PROGRESS]
    ├───(Citizen: NO) ─────────────────────────► [REOPENED] ───┘
    ├───(Citizen: UNABLE / NO_ANSWER) ─────────► [CITIZEN_VERIFICATION] (Retry)
    │
    ▼ (Citizen: YES / Verified)
[VERIFIED]
    │
    ▼ (Official Closeout Summary Notes)
[RESOLVED]
    │
    ▼ (5-Star Citizen Rating & Feedback)
[CLOSED]
```

---

## 2. Transition Invariants & Guardrails

1. **Worker Guardrail**: Field workers can update tasks to `IN_PROGRESS` and `WORK_COMPLETED` with proof attachments. Workers are **strictly forbidden** from marking tickets as `RESOLVED`, `CLOSED`, or `VERIFIED`.
2. **Mandatory Audit Trail**: Every status transition permanently appends an entry into `grievance_updates` recording:
   - `from_status`
   - `to_status`
   - `remarks` (minimum requirement)
   - `updated_by_user_id`
   - `timestamp`
3. **Telephony Outcome Invariant**: A phone call outcome of `NO_ANSWER`, `BUSY`, or `FAILED` is **NEVER** interpreted as a negative response (`NO`). The ticket remains in `CITIZEN_VERIFICATION` for automated retry.
4. **Permanent Proof Archive**: All uploaded field completion photos (`resolution_proofs`) and officer decisions (`officer_verifications`) are preserved historically in the database to prevent overwrites or data loss.
5. **Post-Resolution Citizen Feedback**: 5-Star feedback and satisfaction ratings can **only** be submitted once the grievance reaches `RESOLVED` or `CLOSED`.
