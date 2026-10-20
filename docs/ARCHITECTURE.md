# GramSeva Architecture & System Design
### Web-Based Grievance Management System for Rural Panchayats
**Community Service Project (CSP) • e-Governance Civic Technology**

---

## 1. Architectural Philosophy
GramSeva is engineered as a robust, modular, and audit-compliant civic grievance redressal platform. Inspired by modern AI developer repositories and intelligence vaults, the codebase follows strict separation of concerns, decoupling configuration, persistent data layers, domain business services, and transport/HTTP routing.

---

## 2. Directory & Component Structure

```
d:\csp\
├── core/                           # Application Foundation & Security Invariants
│   ├── config.py                   # Environment settings, secret keys, upload path definitions
│   ├── constants.py                # Status machine, allowed transitions, verification enums
│   ├── database.py                 # Thread-safe SQLite connection factory with PRAGMA foreign keys
│   ├── schema.py                   # 13 core relational tables and schema migration definitions
│   └── security.py                 # login_required, role_required decorators, and citizen PII masking
│
├── services/                       # Decoupled Business Logic & Domain Abstractions
│   ├── grievance_service.py        # Grievance registration, tracking ID sequence generation
│   ├── verification_service.py     # IVR telephony abstraction with Mock & Production provider connectors
│   ├── notification_service.py     # Automated multi-role in-app notification dispatcher
│   ├── analytics_service.py        # Real-time statistics aggregation, ward & category metrics
│   └── seed_service.py             # Realistic rural Panchayat demonstration dataset seeder
│
├── routes/                         # Modular Flask Blueprints (Zero Monolith)
│   ├── pages.py                    # Frontend HTML views (/, /citizen, /admin, /worker, /track, /analytics)
│   ├── auth.py                     # Authentication, citizen registration, session, demo persona switcher
│   ├── grievances.py               # Public feed, citizen filing, tracking, assignment, status machine
│   ├── worker.py                   # Field technician task handling and completion proof uploads
│   ├── verification.py             # Higher officer verification, citizen verification, IVR trigger
│   ├── feedback.py                 # Citizen 5-star ratings and resolution feedback
│   ├── announcements.py            # Panchayat public notices and emergency broadcasts
│   ├── departments.py              # Department roster, supervising officers, skilled technicians
│   ├── notifications.py            # User notification retrieval and read acknowledgments
│   ├── analytics.py                # Metrics summary and visual chart endpoints
│   └── uploads.py                  # Protected, role-gated evidence file serving
│
├── agent/                          # AI Intelligence Vault & System Governance
│   ├── rules/
│   │   ├── SYSTEM_RULES.md         # Authoritative Panchayat architecture specifications
│   │   └── DEVELOPER_RULES.md      # Code standards, zero theme change, and invariant policies
│   ├── prompts/
│   │   ├── triage_agent.md         # Prompt for vernacular civic complaint classification & priority
│   │   ├── ivr_telephony.md        # Bilingual (Telugu/English) voice agent prompt scripts
│   │   └── resolution_auditor.md   # Prompt for evaluating photographic completion proof
│   ├── skills/
│   │   ├── rural-grievance-triage/ # Structured YAML skill for Panchayat category & SLA routing
│   │   ├── telephony-verification/ # Structured YAML skill for outbound citizen confirmation calls
│   │   └── sla-escalation-monitoring/# Structured YAML skill for proactive SLA breach escalations
│   └── workflows/
│       └── GRIEVANCE_LIFECYCLE.md  # Formal state machine, guardrails, and audit rules
│
├── docs/                           # Comprehensive Engineering Documentation
│   ├── ARCHITECTURE.md             # This document: full system design & directory breakdown
│   ├── API_REFERENCE.md            # Detailed OpenAPI / REST API contract for all 34 endpoints
│   ├── BRAND_GUIDELINES.md         # Panchayat civic design tokens, typography, and color palette
│   └── WORKFLOW_GUIDE.md           # End-to-end user journeys for citizens, workers, and officials
│
├── scripts/                        # Automation & Testing Utilities
│   ├── seed_db.py                  # Standalone CLI tool to re-initialize and seed the database
│   └── test_suite.py               # End-to-end automated regression test verifying all routes & RBAC
│
├── static/                         # Frontend Static Assets (PRESERVED - ZERO THEME CHANGES)
│   ├── css/style.css               # Civic CSS tokens, glassmorphism cards, responsive layouts
│   ├── js/                         # Frontend application controllers (app, citizen, worker, admin, charts)
│   └── img/                        # SVG Panchayat crest seal and civic emblems
│
├── templates/                      # Jinja2 HTML Templates (PRESERVED - ZERO THEME CHANGES)
│   ├── base.html                   # Global layout shell, bilingual switcher, demo persona bar
│   ├── index.html                  # Public landing portal and emergency notice board
│   ├── citizen_portal.html         # Citizen complaint filing, my tickets, and tracking modal
│   ├── admin_portal.html           # Secretary dashboard, ticket assignment, officer roster
│   ├── worker_portal.html          # Field technician task queue and proof upload modal
│   ├── track.html                  # Public tracking page with 6-stage visual timeline stepper
│   └── analytics.html              # Chart.js dashboards for Gram Sabha performance reporting
│
├── uploads/                        # Protected storage directory for evidence images & resolution proofs
├── app.py                          # Application factory entry point & runner
├── database.py                     # Backward-compatibility layer for database operations
├── verification_service.py         # Backward-compatibility layer for telephony verification
├── requirements.txt                # Python dependencies
└── README.md                       # Master project overview and execution guide
```

---

## 3. Database Relational Model
GramSeva runs on a high-speed relational schema in SQLite (`gramseva.db`) with foreign key enforcement enabled:
- **`users`**: Base credentials and demographic profiles (`citizen`, `worker`, `officer`, `admin`).
- **`departments`**: Administrative civic wings (`WAT`, `ELEC`, `SAN`, `ROAD`, `HLTH`, `EDU`, `GEN`).
- **`officers`**: Supervising Panchayat engineers and health inspectors linked to `users` and `departments`.
- **`workers`**: Skilled field technicians (plumbers, linemen, sanitation crew) linked to `users`.
- **`grievances`**: Master complaint record with sequential identifier `GRV-YYYY-XXXXX`.
- **`grievance_updates`**: Immutable audit log of every status transition and remark.
- **`resolution_proofs`**: Historical archive of field completion photos and worker notes.
- **`officer_verifications`**: Formal approval or rework orders issued by supervising officers.
- **`citizen_verifications`**: Verifiable confirmation responses from citizens.
- **`verification_attempts`**: Phone/IVR verification requests storing grievance ID, citizen ID, masked phone reference, attempt number, requested time, call outcome, citizen response, response time, provider reference, and request status.
- **`feedback`**: Post-resolution 5-star ratings and citizen comments.
- **`notifications`**: Real-time in-app alerts dispatched across all personas.
- **`announcements`**: Public broadcasts and Gram Sabha meeting notices.
