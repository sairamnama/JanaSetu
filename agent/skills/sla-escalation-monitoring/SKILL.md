---
name: sla-escalation-monitoring
description: Continuously monitors unresolved civic tickets against statutory Panchayat SLA targets and automatically flags or escalates breach risks.
version: 1.0.0
author: GramSeva AI Architecture Team
category: operations/sla-monitoring
inputs:
  - grievance_records: array of grievance objects
  - current_timestamp: string
outputs:
  - breached_tickets: array
  - at_risk_tickets: array
  - escalation_notifications: array
---

# SLA Escalation Monitoring Skill

## Objective
Ensures zero citizen complaint falls through the cracks by continuously auditing elapsed time since registration against department-level SLA targets.

## Statutory Panchayat SLA Standards
- `ELEC` (Electricity): **24 Hours** max turnaround.
- `WAT` (Drinking Water): **48 Hours** max turnaround.
- `SAN` (Sanitation): **48 Hours** max turnaround.
- `ROAD` (Roads & Drainage): **5 Days** max turnaround.
- `HLTH` (Public Health): **3 Days** max turnaround.
- `EDU` (School Infrastructure): **7 Days** max turnaround.
- `GEN` (General Administration): **7 Days** max turnaround.

## Escalation Triggers
1. If elapsed time >= 75% of SLA window and status is still `SUBMITTED` or `ASSIGNED` -> Emit Amber Alert to Department Officer.
2. If elapsed time > 100% of SLA window -> Update status to `ESCALATED` and notify Panchayat Secretary & Sarpanch directly with high-priority flag.
