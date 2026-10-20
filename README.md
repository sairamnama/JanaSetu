# GramSeva (గ్రామసేవ)
### Web-Based Grievance Management System for Rural Panchayats
**Community Service Project (CSP) • e-Governance Civic Technology**

---

## 1. Project Overview
**GramSeva** is an e-Governance civic redressal platform engineered specifically for Rural Gram Panchayats. It bridges the gap between rural citizens and Panchayat administration by enabling citizens to submit, track, and rate civic complaints (drinking water, streetlighting, sanitation, roads, public health) while empowering Panchayat Secretaries, Sarpanches, Field Officers, and Workers to verify, remediate, audit, and close grievances transparently.

Structured following enterprise-grade AI repository standards (inspired by modern developer vaults and workspace architectures):
- Clean separation of concerns: `core/`, `services/`, `routes/`, `agent/`, `docs/`, `scripts/`.
- 100% preservation of UI civic design tokens, CSS theme, and templates.
- Strict enforcement of the 6-stage grievance lifecycle machine and security RBAC invariants.

---

## 2. Clean Modular Project Architecture

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
│   ├── ARCHITECTURE.md             # Full system design, component models & directory breakdown
│   ├── API_REFERENCE.md            # Detailed OpenAPI / REST API contract for all 34 endpoints
│   ├── BRAND_GUIDELINES.md         # Panchayat civic design tokens, typography, and color palette
│   └── WORKFLOW_GUIDE.md           # End-to-end user journeys for citizens, workers, and officials
│
├── scripts/                        # Automation & Testing Utilities
│   ├── seed_db.py                  # Standalone CLI tool to re-initialize and seed the database
│   └── test_suite.py               # End-to-end automated regression test verifying all routes & RBAC
│
├── static/                         # Frontend Static Assets (CSS Theme & JS Controllers)
├── templates/                      # Jinja2 HTML Templates (6 Portals & Dashboards)
├── uploads/                        # Protected storage directory for evidence images & resolution proofs
├── app.py                          # Application factory entry point & runner
├── database.py                     # Backward-compatibility layer for database operations
├── verification_service.py         # Backward-compatibility layer for telephony verification
├── requirements.txt                # Python dependencies
└── run.bat                         # 1-Click Windows startup script
```

---

## 3. Complete 20-Module Implementation Breakdown

| Module | Name | Implementation Detail |
| :---: | :--- | :--- |
| **M1** | **User Authentication & RBAC** | Citizen, Worker, Officer, Admin roles with hashed passwords (`werkzeug.security`) and role-gated routes. |
| **M2** | **Citizen Dashboard** | Summary metric counters, quick actions, recent complaints, and announcements feed. |
| **M3** | **Grievance Submission** | Category selection, ward dropdown (1-20), landmark, priority, description, and image proof upload. |
| **M4** | **Grievance ID & Tracking** | Unique format `GRV-YYYY-XXXXX`, public search without login, interactive 6-step visual stepper. |
| **M5** | **My Grievances** | Filter by status/category, search bar, full detail view, and official audit history. |
| **M6** | **Admin / Official Dashboard**| High-priority alert queue, operational metrics, and department workload monitoring. |
| **M7** | **Grievance Management** | Verification, accept/reject, department/officer dispatch, official remarks, and status transitions. |
| **M8** | **Department & Officer Management**| Department rosters (Water, Power, Sanitation, Roads, Health, Education), officer & worker ticket loads. |
| **M9** | **Priority & Categorization Engine**| High/Medium/Low priority flags with animated pulsing warning indicators on urgent tickets. |
| **M10**| **Notification Center** | In-app notification alerts for submission, assignment, progress updates, and resolution. |
| **M11**| **Feedback & Rating System** | 5-Star interactive rating, satisfaction pill (Satisfied / Partial / Unsatisfied), and citizen review. |
| **M12**| **Analytics & Reports** | Chart.js visual dashboard: Category doughnut, Ward bar chart, Status pie, and SLA turnaround. |
| **M13**| **Search & Filtering** | Multi-faceted search across tracking IDs, keywords, wards, categories, and priority levels. |
| **M14**| **Profile Management** | Role profiles, contact details, ward allocations, and badge identifiers. |
| **M15**| **Panchayat Announcements** | Emergency alerts and scheduled maintenance notices (water cuts, power repair, Gram Sabha). |
| **M16**| **Database Architecture** | Relational schema in SQLite (`gramseva.db`) with foreign key constraints, 13 tables, and auto-migration. |
| **M17**| **Backend / RESTful API** | Modular Python + Flask Blueprints serving structured JSON responses and responsive HTML templates. |
| **M18**| **Security & Validation** | Password hashing, parameterized SQL queries, file extension validation, and XSS sanitization. |
| **M19**| **UI/UX Design & Accessibility**| Vanilla CSS design system, responsive down to mobile viewports, high contrast, bilingual toggle. |
| **M20**| **Testing & Demonstration** | Instant one-click persona switcher (Citizen, Worker, Officer, Admin) and automated regression test suite. |

---

## 4. Pre-Seeded Demonstration Personas

For seamless evaluation, testing, and demonstrations, click the **Demo Switch** pills on the topbar or use the credentials below:

| Role | Username | Password | Full Name & Designation |
| :--- | :--- | :--- | :--- |
| **Citizen** | `citizen_ramesh` | `citizen123` | Sri Ramesh Naidu (Ward 4 Resident) |
| **Worker** | `worker_shiva` | `worker123` | Sri Shiva Kumar (Pipe Fitter & Plumber) |
| **Officer** | `officer_water` | `officer123` | Sri Ramesh Varma (AE, Rural Water Supply) |
| **Admin** | `admin` | `admin123` | Sri K. Venkat Rao (Panchayat Secretary) |

---

## 5. How to Run the Application

### Option A: 1-Click Startup (Windows)
Double-click [`run.bat`](file:///d:/csp/run.bat) in the project root. It starts the server and opens your default browser at `http://127.0.0.1:5000`.

### Option B: Terminal Command
```powershell
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

### Option C: Run Full Automated Test Suite
```powershell
python scripts/test_suite.py
```

### Option D: Re-Seed Database
```powershell
python scripts/seed_db.py --reset
```

---

## 6. Technology Stack
- **Backend:** Python 3 + Flask (Modular Blueprints)
- **Database:** SQLite (`gramseva.db`) with PRAGMA foreign keys
- **Frontend:** Vanilla HTML5, Modern CSS3 (Civic tokens, Glassmorphism, Responsive Grid)
- **Charts & Visualizations:** Chart.js 4.4
- **Typography:** Google Fonts (*Plus Jakarta Sans*, *Inter*, *Noto Sans Telugu*)
- **Icons:** Native Unicode & Custom SVG Panchayat Crest
- **Testing:** Python `unittest` Automated Regression Suite
