---
name: telephony-verification
description: Orchestrates automated outbound IVR voice verification calls to rural citizens to confirm resolution of civic complaints before final closure.
version: 1.0.0
author: GramSeva AI Architecture Team
category: telephony/ivr-automation
inputs:
  - grievance_id: integer
  - tracking_id: string
  - citizen_phone: string
  - category: string
  - resolution_notes: string
outputs:
  - call_outcome: enum (ANSWERED, NO_ANSWER, BUSY, INVALID_NUMBER, FAILED)
  - citizen_response: enum (YES, PARTIALLY, NO, UNABLE_TO_VERIFY)
  - next_status: enum (VERIFIED, REWORK_REQUIRED, REOPENED, CITIZEN_VERIFICATION)
  - audit_log: string
---

# Telephony Verification Skill

## Principle & Invariant
No civic complaint can be marked as `RESOLVED` in GramSeva without verifiable citizen confirmation. Telephony IVR calls bridge the digital divide for citizens without smartphones or active internet access.

## Call Handling Logic
1. **Outbound Call Initiation**:
   - Transmit grievance summary (`tracking_id`, category, completed repair notes).
   - Play bilingual IVR prompt in Telugu and English.
2. **Outcome Parsing**:
   - `NO_ANSWER / BUSY`: Do NOT treat as NO. Do not alter grievance state negatively. Log attempt in `verification_attempts` and reschedule automated retry.
   - `INVALID_NUMBER`: Flag ticket for manual physical verification by Ward Sachivalayam volunteer.
   - `ANSWERED`: Record DTMF tone or voice intent:
     - `1 / YES`: Problem solved -> Status transitions to `VERIFIED`.
     - `2 / PARTIALLY`: Rework needed -> Status transitions to `REWORK_REQUIRED`.
     - `3 / NO`: Problem unsolved -> Status transitions to `REOPENED`.
     - `4 / UNABLE`: Cannot verify -> Status stays `CITIZEN_VERIFICATION`.
