# GramSeva REST API Reference Guide

All API endpoints reside under `/api/` and return standardized JSON contracts:
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": { ... }
}
```

---

## 1. Authentication & Session APIs (`routes/auth.py`)

### `POST /api/register`
- **Description:** Registers a new rural citizen account.
- **Request Body (JSON or Form):** `username`, `password`, `full_name`, `mobile`, `email`, `ward_number`, `address`
- **Response (200):** `{'success': True, 'message': 'Citizen account created successfully.', 'user': {...}}`

### `POST /api/login`
- **Description:** Authenticates any persona (`citizen`, `worker`, `officer`, `admin`).
- **Request Body (JSON or Form):** `username`, `password`
- **Response (200):** `{'success': True, 'user': {'id': 1, 'username': 'admin', 'role': 'admin', ...}}`

### `POST /api/logout`
- **Description:** Clears the active user session.
- **Response (200):** `{'success': True, 'message': 'Logged out successfully.'}`

### `GET /api/current-user`
- **Description:** Checks active session and returns authenticated user profile.
- **Response (200):** `{'logged_in': True, 'user': {...}}`

### `POST /api/demo-switch-user`
- **Description:** Instantly switches session to pre-seeded demo persona (citizen_ramesh, worker_shiva, officer_water, admin).
- **Request Body (JSON):** `{'role': 'citizen' | 'worker' | 'officer' | 'admin'}`
- **Response (200):** `{'success': True, 'user': {...}}`

---

## 2. Public Feeds & File Serving (`routes/grievances.py`, `routes/uploads.py`)

### `GET /api/public-feed`
- **Description:** Returns the 6 most recent civic grievances with masked PII for public landing page.
- **Response (200):** `{'success': True, 'feed': [...]}`

### `GET /api/uploads/<path:filename>`
- **Description:** Securely serves uploaded evidence photos. Role-gated to ticket complainant, assigned officer, assigned worker, or admin.
- **Response:** File stream (HTTP 200) or HTTP 403 Forbidden.

---

## 3. Grievance Management APIs (`routes/grievances.py`)

### `GET /api/grievances`
- **Query Parameters:** `status`, `category`, `ward`, `priority`, `search`, `scope` (`my` | `all`)
- **Access:** Authenticated. Automatically scopes results according to role.
- **Response (200):** `{'success': True, 'grievances': [...], 'count': 6}`

### `POST /api/grievances`
- **Description:** Registers a new civic complaint.
- **Access:** Role: `citizen`.
- **Form Data:** `title`, `category`, `description`, `ward_number`, `location_landmark`, `priority`, `evidence_image` (file)
- **Response (200):** `{'success': True, 'tracking_id': 'GRV-2026-00107', 'grievance_id': 7}`

### `GET /api/grievances/<id_or_tracking>`
- **Description:** Full grievance record, timeline history, resolution proofs, and verification logs. Citizen PII is automatically masked for non-privileged viewers.
- **Response (200):** `{'success': True, 'grievance': {...}}`

### `PUT /api/grievances/<int:grievance_id>/status`
- **Description:** Advances status through state machine transitions.
- **Access:** Role: `admin`, `officer`, `worker` (worker restricted from RESOLVED/CLOSED).
- **Request Body:** `{'status': 'IN_PROGRESS', 'remarks': '...', 'resolution_notes': '...'}`
- **Response (200):** `{'success': True, 'from_status': 'ASSIGNED', 'to_status': 'IN_PROGRESS'}`

### `PUT /api/grievances/<int:grievance_id>/assign`
- **Description:** Assigns department, supervising officer, and field technician.
- **Access:** Role: `admin`.
- **Request Body:** `{'department_id': 1, 'assigned_officer_id': 1, 'assigned_worker_id': 1, 'remarks': '...'}`
- **Response (200):** `{'success': True, 'message': 'Grievance assignment updated successfully.'}`

### `PUT /api/grievances/<int:grievance_id>/priority`
- **Description:** Updates urgency level (`Low`, `Medium`, `High`).
- **Access:** Role: `admin`.
- **Request Body:** `{'priority': 'High'}`

---

## 4. Remediation & Verification APIs (`routes/worker.py`, `routes/verification.py`)

### `POST /api/grievances/<int:grievance_id>/complete-work`
- **Description:** Worker submits formal work-completion report with evidence. Validates file magic bytes and size (max 5MB). Transitions status `IN_PROGRESS -> WORK_COMPLETED` (never `RESOLVED`). Increments `proof_version` and stores persistent audit metadata.
- **Access:** Role: `worker` (assigned), `officer`, `admin`.
- **Form Data:**
  - `proof_file` (file, required): After-work photograph or PDF evidence.
  - `completion_notes` / `description` (text, required): Formal work completion description.
  - `remarks` (text, optional): Resolution remarks.
  - `completion_timestamp` (datetime string, optional): Work completion timestamp.
  - `location_coords` (text, optional): Optional GPS coordinates / landmark.
  - `additional_evidence` (file, optional): Secondary supporting document or photo.
- **Response:** `{'success': True, 'message': '...', 'proof_id': 1, 'proof_version': 1, 'status': 'WORK_COMPLETED'}`

### `POST /api/grievances/<int:grievance_id>/officer-verify`
- **Description:** Supervising officer inspects worker completion proof and issues decision.
- **Access:** Role: `officer`, `admin`.
- **Request Body:** `{'decision': 'APPROVED' | 'REWORK_REQUESTED' | 'REJECTED', 'remarks': '...', 'proof_id': 1}`

### `POST /api/grievances/<int:grievance_id>/citizen-verify`
- **Description:** Citizen confirms whether civic issue is solved.
- **Access:** Complainant citizen or official recording on citizen's behalf.
- **Request Body:** `{'response': 'YES' | 'PARTIALLY' | 'NO' | 'UNABLE_TO_VERIFY', 'call_outcome': 'ANSWERED', 'remarks': '...'}`

### `POST /api/grievances/<int:grievance_id>/trigger-verification-call`
- **Description:** Triggers automated outbound phone/IVR voice verification call to citizen via `VerificationService` (labeled: Development / Mock Verification in local development).
- **Access:** Role: `officer`, `admin`.
- **Request Body:** `{'simulated_outcome': 'ANSWERED' | 'NO_ANSWER' | 'BUSY' | 'INVALID_NUMBER' | 'FAILED', 'simulated_response': 'YES' | 'PARTIALLY' | 'NO' | 'UNABLE_TO_VERIFY', 'remarks': '...'}`

### `GET /api/grievances/<int:grievance_id>/verification-requests`
- **Description:** Retrieves complete historical log of telephony verification requests for a grievance. Citizen phone numbers are masked (`******XXXX`) to protect PII.
- **Access:** Complainant citizen, `officer`, `admin`.
- **Response:** `{'success': True, 'verification_requests': [...], 'count': N, 'provider_label': 'Development / Mock Verification'}`

---

## 5. Feedback, Notices & Rosters (`routes/feedback.py`, `routes/announcements.py`, `routes/departments.py`)

### `POST /api/feedback`
- **Description:** Citizen provides 1-5 star rating and satisfaction feedback, moving ticket to `CLOSED`.
- **Access:** Complainant citizen on `RESOLVED` grievance.
- **Request Body:** `{'grievance_id': 4, 'star_rating': 5, 'satisfaction': 'Satisfied', 'comments': '...'}`

### `GET /api/announcements` & `POST /api/announcements`
- **GET:** Public retrieval of all notices.
- **POST:** Admin broadcast creation with `is_emergency` flag.

### `GET /api/departments`, `GET /api/officers`, `GET /api/workers`
- **Description:** Rosters of departments, supervising engineers, and skilled field workers.

---

## 6. Notifications & Analytics (`routes/notifications.py`, `routes/analytics.py`)

### `GET /api/notifications`, `POST /api/notifications/<id>/read`, `POST /api/notifications/read-all`
- **Description:** User in-app notifications and read status updates.

### `GET /api/analytics`
- **Description:** Aggregated metrics (total, pending, verified, resolved), category distribution, ward distribution, department turnaround, and average citizen satisfaction rating.
