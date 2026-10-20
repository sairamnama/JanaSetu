---
name: rural-grievance-triage
description: Categorizes and scores civic grievances filed by rural citizens, assigning appropriate Panchayat departments and priority SLA targets.
version: 1.0.0
author: GramSeva AI Architecture Team
category: civic-technology/e-governance
inputs:
  - grievance_title: string
  - grievance_description: string
  - ward_number: integer (1-20)
  - citizen_suggested_priority: enum (Low, Medium, High)
outputs:
  - department_code: enum (WAT, ELEC, SAN, ROAD, HLTH, EDU, GEN)
  - verified_priority: enum (Low, Medium, High)
  - sla_hours: integer
  - rationale: string
---

# Rural Grievance Triage Skill

## Context
Rural Gram Panchayats receive civic complaints spanning drinking water borewells, power supply lines, rural sanitation, concrete roads, and primary healthcare. Citizens often use colloquial terms or mixed Telugu/English. This skill structures and prioritizes those submissions according to GramSeva system rules.

## Priority & SLA Rules
1. **Urgent Hazard (High - 24 to 48 Hours)**:
   - Fallen or live power cables, sparking transformers (`ELEC`)
   - Main drinking water trunk line leaks causing total ward outage (`WAT`)
   - Cholera / dengue fever cluster outbreaks or contaminated wells (`HLTH`)
2. **Major Disruption (Medium - 3 to 5 Days)**:
   - Blocked arterial stormwater drains with overflow (`ROAD`)
   - Uncollected public market garbage accumulated for > 3 days (`SAN`)
   - Streetlights dark across an entire transit route (`ELEC`)
3. **General Maintenance (Low - 7 to 14 Days)**:
   - Single streetlight bulb replacement (`ELEC`)
   - Berm clearing or roadside weed cutting (`ROAD`)
   - Non-critical administrative requests (`GEN`)

## Execution Procedure
1. Parse the text for key infrastructure tokens (`pipeline`, `transformer`, `drain`, `fogging`, `pothole`).
2. Map to canonical Panchayat department code.
3. Compute affected population size based on location landmark (e.g. `Rythu Bazaar` or `Primary School` indicates high traffic).
4. Return verified priority and SLA target window.
