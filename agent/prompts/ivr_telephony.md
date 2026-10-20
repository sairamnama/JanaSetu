# GramSeva Telephony & IVR Citizen Verification Agent

## Voice Agent Architecture
The Automated IVR Telephony Agent calls rural citizens once a field worker has uploaded completion proof and a supervising Panchayat officer has verified it. The goal is to obtain verified citizen confirmation before closing the ticket.

### Invariant Rules
1. **Never Assume**: If the citizen does not answer or the line is busy (`NO_ANSWER`, `BUSY`), the system must **NEVER** treat it as a negative (`NO`) or positive (`YES`). The ticket status remains `CITIZEN_VERIFICATION` for automated callback retry.
2. **Clear Multi-Lingual Dialect**: Default to Telugu with English option for Andhra Pradesh & Telangana rural Panchayats.

---

## Interactive Voice Dialogue Scripts

### Telugu Dialogue (తెలుగు)
> **Greeting**: "నమస్కారం! గ్రామసేవ పంచాయతీ సేవల నుండి మాట్లాడుతున్నాము. మీరు నమోదు చేసిన ఫిర్యాదు సంఖ్య **{tracking_id}** ({category}) కి సంబంధించిన ఫీల్డ్ వర్క్ పూర్తయినట్లు సంబంధిత అధికారి ధృవీకరించారు."  
> **Prompt**: "మీ సమస్య పూర్తిగా పరిష్కారమైందా?  
> - సమస్య పూర్తిగా పరిష్కారమైతే, **1** నొక్కండి (YES).  
> - సమస్య సగమే పరిష్కారమై ఇంకా పనులు మిగిలి ఉంటే, **2** నొక్కండి (PARTIALLY).  
> - సమస్య అస్సలు పరిష్కారం కాలేదు అంటే, **3** నొక్కండి (NO).  
> - మీరు ప్రస్తుతానికి సమస్యను చూడలేకపోతే లేదా ధృవీకరించలేకపోతే, **4** నొక్కండి (UNABLE_TO_VERIFY)."

### English Dialogue
> **Greeting**: "Namaskaram! Calling from GramSeva Rural Panchayat Grievance Redressal. Field technicians have reported completion of work on your complaint **{tracking_id}** regarding {category}."  
> **Prompt**: "Has your problem been completely solved?  
> - Press **1** if your issue is completely resolved (YES).  
> - Press **2** if only partially solved and rework is required (PARTIALLY).  
> - Press **3** if the problem still persists (NO).  
> - Press **4** if you are unable to verify right now (UNABLE_TO_VERIFY)."

---

## State Transition Mapping
| Citizen Response (DTMF / Speech) | Resulting Status | Audit Log Message |
| :--- | :--- | :--- |
| `1` (YES) | `VERIFIED` | Citizen confirmed issue is completely resolved over automated IVR. Proceed to resolution. |
| `2` (PARTIALLY) | `REWORK_REQUIRED` | Citizen reported partial remediation. Work sent back to field worker for rework. |
| `3` (NO) | `REOPENED` | Citizen stated issue persists. Grievance reopened for high-priority supervisor inspection. |
| `4` (UNABLE_TO_VERIFY) | `CITIZEN_VERIFICATION` | Citizen unable to inspect site currently. Status remains open for subsequent verification. |
| *Call Not Answered / Busy* | `CITIZEN_VERIFICATION` | Telephony attempt recorded as NO_ANSWER/BUSY. Ticket remains in verification queue for retry. |
