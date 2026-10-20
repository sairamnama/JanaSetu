# SYSTEM RULES: WEB-BASED GRIEVANCE MANAGEMENT SYSTEM FOR RURAL PANCHAYATS
**Project Reference:** Community Service Project (CSP) — Panchayat Civic Technology  
**Version:** 1.0.0  
**Effective Date:** October 2026  
**Status:** Approved Architecture Specification  

---

## 1. System Vision & Objective
The Web-Based Grievance Management System (GramSeva) is an e-Governance platform tailored for Rural Gram Panchayats. Its primary mission is to democratize civic grievance redressal for rural citizens by providing an accessible, transparent, and auditable system for registering, assigning, tracking, resolving, and analyzing civic complaints across village wards.

---

## 2. Core Architectural Principles
1. **Zero-Exclusion Accessibility:** The interface must be straightforward and usable by rural citizens with low digital literacy. Forms must feature visual icons, plain language, and bilingual/local script support.
2. **Transparent Audit Trail:** Every action (submission, verification, assignment, status change, remark, resolution, rating) is permanently recorded in an immutable history log.
3. **Role-Based Separation of Duties:** Distinct privileges for Citizens, Panchayat Field Officers, and Admin/Panchayat Secretaries.
4. **Data Integrity & Resiliency:** All transactions enforce relational integrity, strict input validation, and sanitization against injection attacks.
5. **Demonstration Readiness:** Built with zero-friction portability—runs natively with lightweight dependencies (Python Flask + SQLite/MySQL compatible schema).

---

## 3. Role-Based Access Control (RBAC) Matrix

| Feature / Action | Citizen | Panchayat Officer | Admin / Sarpanch / Secretary | Public / Guest |
| :--- | :---: | :---: | :---: | :---: |
| View Public Landing & Notices | Yes | Yes | Yes | Yes |
| Track Grievance by ID | Yes | Yes | Yes | Yes |
| Register Citizen Account | Yes | No | No | Yes |
| Submit New Grievance | Yes | No | No | No |
| View Personal Grievances | Yes (Own) | No | No | No |
| Rate & Provide Feedback | Yes (Own, Resolved) | No | No | No |
| View Admin/Official Dashboard | No | Yes (Dept View) | Yes (Global View) | No |
| Verify & Accept/Reject Grievances| No | No | Yes | No |
| Assign Department & Officer | No | No | Yes | No |
| Update Status & Add Field Remarks | No | Yes (Assigned) | Yes (All) | No |
| Manage Departments & Officers | No | No | Yes | No |
| Publish Announcements | No | No | Yes | No |
| Access Analytics & Reports | No | Limited | Full | No |

---

## 4. Grievance Lifecycle & Status Transition Rules

### 4.1 Status Definitions
- `SUBMITTED`: Registered by the citizen; awaiting Panchayat administrative review.
- `UNDER_REVIEW`: Panchayat Secretary/Admin has opened and verified the legitimacy of the complaint.
- `ASSIGNED`: Routed to the designated department (e.g., Water Supply, Sanitation) and assigned to a responsible field officer.
- `IN_PROGRESS`: Officer has acknowledged the issue and on-site remediation has begun.
- `RESOLVED`: Field work is concluded; officer provides resolution proof and notes.
- `CLOSED`: Citizen has confirmed satisfaction or 14 days elapsed after resolution with no escalation.
- `REJECTED`: Declared duplicate, out of Panchayat jurisdiction, or invalid with mandatory stated reasoning.

### 4.2 State Transition Machine
```
[SUBMITTED] 
    │
    ├───(Invalid/Duplicate)───────► [REJECTED] (Requires remarks)
    │
    ▼
[UNDER_REVIEW]
    │
    ▼ (Assign Dept & Officer)
[ASSIGNED]
    │
    ▼ (Field Work Started)
[IN_PROGRESS]
    │
    ▼ (Work Completed)
[RESOLVED] ──────(Citizen Feedback / Auto-Archive)──────► [CLOSED]
```

### 4.3 Transition Invariants
1. A grievance **CANNOT** move to `IN_PROGRESS` or `RESOLVED` without an assigned department and officer.
2. Every status transition **MUST** generate an entry in the `grievance_updates` table containing timestamp, updater ID, previous status, new status, and official comments.
3. Every status transition **MUST** trigger an automated in-app notification to the submitting citizen.
4. When moving to `REJECTED`, an administrative reason of at least 10 characters is mandatory.
5. Citizen feedback and star rating can **ONLY** be submitted when the grievance status is `RESOLVED` or `CLOSED`.

---

## 5. Unique Grievance ID Specification
Every grievance registered in the system is assigned a human-readable, sequential identifier formatted as:
```
GRV-{YYYY}-{5-DIGIT-SEQUENCE}
Example: GRV-2026-00101
```
- Prefix: `GRV-`
- Year: 4-digit submission year (e.g., `2026`)
- Sequence: Zero-padded integer incrementing per year.

---

## 6. Priority & Escalation Engine

### 6.1 Priority Levels
- **HIGH / URGENT:** Imminent hazard to public health/safety (e.g., collapsed live wire, contaminated main drinking pipeline, open sewer hazard). Target resolution: **24–48 hours**.
- **MEDIUM:** Significant civic disruption affecting daily activities (e.g., non-functional streetlights in main street, blocked community drainage, uncollected market garbage). Target resolution: **3–5 days**.
- **LOW:** General maintenance, non-emergency civil repairs (e.g., roadside weed clearing, park bench repair, signpost repaint). Target resolution: **7–14 days**.

### 6.2 Priority Calculation Rules
Citizen can recommend an initial priority during submission, but the system and admin verify based on:
1. **Affected Population:** Individual household (Low) vs. Entire Ward / School / Hospital perimeter (High).
2. **Category Urgency Weight:** Electricity Hazard (Weight 3) > Water Contamination (Weight 3) > Road Pothole (Weight 2) > General Sanitation (Weight 1).
3. Admin reserves final override authority with logged rationale.

---

## 7. Civic Categories & Department Mapping

| Category Code | Category Name | Default Assigned Department | SLA Target |
| :--- | :--- | :--- | :--- |
| `ELEC` | Electricity & Streetlights | Electrical Maintenance Dept | 24 Hours |
| `WAT` | Drinking Water & Supply | Rural Water Supply (RWS) | 48 Hours |
| `SAN` | Waste Management & Sanitation | Village Sanitation & Health | 48 Hours |
| `ROAD` | Roads & Drainage Systems | Panchayat Engineering & Roads | 5 Days |
| `HLTH` | Public Health & Vector Control | Health & Primary Care | 3 Days |
| `EDU` | Anganwadi & School Civic Issues | Education & Child Welfare | 7 Days |
| `HOUS` | Rural Housing & Infrastructure | Housing & Civil Infrastructure | 10 Days |
| `OTHER`| Other Civic & Community Issues | General Panchayat Administration| 7 Days |

---

## 8. Database Schema Specifications

### 8.1 Users Table (`users`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `username` VARCHAR(50) UNIQUE NOT NULL
- `password_hash` VARCHAR(255) NOT NULL
- `full_name` VARCHAR(100) NOT NULL
- `role` ENUM('citizen', 'officer', 'admin') NOT NULL
- `mobile` VARCHAR(15) NOT NULL
- `email` VARCHAR(100)
- `ward_number` INTEGER (1 to 20)
- `village` VARCHAR(100) DEFAULT 'Gram Panchayat'
- `address` TEXT
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 8.2 Departments Table (`departments`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `name` VARCHAR(100) NOT NULL
- `code` VARCHAR(20) UNIQUE NOT NULL
- `description` TEXT
- `head_officer_id` INTEGER NULL

### 8.3 Officers Table (`officers`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id` INTEGER NOT NULL REFERENCES `users(id)`
- `department_id` INTEGER NOT NULL REFERENCES `departments(id)`
- `designation` VARCHAR(100) NOT NULL
- `badge_id` VARCHAR(50) UNIQUE
- `active_tickets_count` INTEGER DEFAULT 0

### 8.4 Grievances Table (`grievances`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `tracking_id` VARCHAR(30) UNIQUE NOT NULL
- `citizen_id` INTEGER NOT NULL REFERENCES `users(id)`
- `category` VARCHAR(50) NOT NULL
- `title` VARCHAR(200) NOT NULL
- `description` TEXT NOT NULL
- `ward_number` INTEGER NOT NULL
- `location_landmark` VARCHAR(255) NOT NULL
- `priority` ENUM('Low', 'Medium', 'High') DEFAULT 'Medium'
- `status` ENUM('SUBMITTED', 'UNDER_REVIEW', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', 'REJECTED') DEFAULT 'SUBMITTED'
- `department_id` INTEGER NULL REFERENCES `departments(id)`
- `assigned_officer_id` INTEGER NULL REFERENCES `officers(id)`
- `evidence_image` VARCHAR(255) NULL
- `resolution_notes` TEXT NULL
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 8.5 Grievance Status History (`grievance_updates`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `grievance_id` INTEGER NOT NULL REFERENCES `grievances(id)`
- `from_status` VARCHAR(30)
- `to_status` VARCHAR(30) NOT NULL
- `remarks` TEXT NOT NULL
- `updated_by_user_id` INTEGER NOT NULL REFERENCES `users(id)`
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 8.6 Citizen Feedback Table (`feedback`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `grievance_id` INTEGER UNIQUE NOT NULL REFERENCES `grievances(id)`
- `citizen_id` INTEGER NOT NULL REFERENCES `users(id)`
- `star_rating` INTEGER CHECK(star_rating BETWEEN 1 AND 5)
- `satisfaction` ENUM('Satisfied', 'Partially Satisfied', 'Unsatisfied') NOT NULL
- `comments` TEXT
- `submitted_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 8.7 Notifications Table (`notifications`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id` INTEGER NOT NULL REFERENCES `users(id)`
- `grievance_id` INTEGER NULL REFERENCES `grievances(id)`
- `title` VARCHAR(150) NOT NULL
- `message` TEXT NOT NULL
- `is_read` BOOLEAN DEFAULT 0
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 8.8 Announcements Table (`announcements`)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `title` VARCHAR(200) NOT NULL
- `category` VARCHAR(50) NOT NULL
- `content` TEXT NOT NULL
- `is_emergency` BOOLEAN DEFAULT 0
- `published_by` INTEGER NOT NULL REFERENCES `users(id)`
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

---

## 9. Security & Validation Rules
1. **Password Storage:** All passwords must be salted and hashed using `werkzeug.security` (`generate_password_hash` with scrypt or pbkdf2:sha256).
2. **Session Security:** Session tokens are cryptographically secured; session role must be validated on every state-altering HTTP route.
3. **Input Sanitization:** HTML escaping on all rendered fields to prevent Stored XSS.
4. **File Upload Policy:**
   - Allowed extensions: `.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf`.
   - Max file size: 5MB.
   - Uploads sanitized via `secure_filename()` and stored outside the public execution root.
5. **SQL Injection Prevention:** Enforced via parameterized queries (`?` placeholders in SQLite / DB-API).

---

## 10. API Contract Guidelines

All JSON responses follow a uniform contract:
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": { ... }
}
```

Error responses return appropriate HTTP status codes (400, 401, 403, 404, 500):
```json
{
  "success": false,
  "error": "Detailed validation or permission message"
}
```
