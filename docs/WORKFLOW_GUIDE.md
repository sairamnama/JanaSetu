# GramSeva Persona & Workflow Guide
### Step-by-Step Demonstration Journeys for Rural Civic Redressal

---

## 1. Pre-Configured Personas

| Role | Username | Password | Full Name & Designation | Primary Function |
| :--- | :--- | :--- | :--- | :--- |
| **Citizen** | `citizen_ramesh` | `citizen123` | Sri Ramesh Naidu (Ward 4 Resident) | Lodges complaints, monitors status, verifies resolution, submits ratings. |
| **Worker** | `worker_shiva` | `worker123` | Sri Shiva Kumar (Pipe Fitter & Plumber) | Receives field tasks, conducts on-site remediation, uploads photo proof. |
| **Officer** | `officer_water` | `officer123` | Sri Ramesh Varma (AE, Water Supply) | Supervises department tickets, audits worker proofs, triggers telephony calls. |
| **Admin** | `admin` | `admin123` | Sri K. Venkat Rao (Panchayat Secretary) | Reviews new tickets, routes departments, assigns staff, publishes notices. |

---

## 2. End-to-End User Journey (Complaint Redressal Cycle)

### Step 1: Complaint Registration (Citizen)
1. Log in as `citizen_ramesh`.
2. Click **Submit Grievance** on the citizen portal.
3. Select Category: *Drinking Water & Supply*, Ward: *4*, Priority: *High*.
4. Input details: *"Major pipeline burst near temple"*, attach optional evidence photo.
5. Submit. System generates unique sequential ID: `GRV-2026-00101` in status `SUBMITTED`.

### Step 2: Verification & Assignment (Admin)
1. Switch to `admin` persona.
2. Review ticket under **Pending Review**.
3. Verify authenticity and assign Department: *Rural Water Supply*, Supervising Officer: *Sri Ramesh Varma*, Field Worker: *Sri Shiva Kumar*.
4. Status transitions to `ASSIGNED`. Automated in-app notifications dispatched to worker, officer, and citizen.

### Step 3: Field Remediation & Photo Proof (Worker)
1. Switch to `worker_shiva`.
2. Open assigned task on **Worker Portal**.
3. Click **Start Work** (Status -> `IN_PROGRESS`).
4. Upon completing repair on-site, click **Upload Completion Proof**.
5. Attach repair photo, input notes: *"Replaced 4-inch PVC joint and restored water pressure."*
6. Submit. Status transitions to `WORK_COMPLETED`. (Worker cannot mark resolved).

### Step 4: Quality Audit (Supervising Officer)
1. Switch to `officer_water`.
2. Review worker's photographic proof and notes under **Verification Queue**.
3. Officer verifies standards and clicks **Approve Proof** (or requests rework if flawed).
4. Status transitions to `CITIZEN_VERIFICATION`.

### Step 5: Automated Verification (Citizen or Automated Telephony)
1. Click **Trigger Telephony Verification** or citizen verifies directly on portal.
2. Automated IVR call is simulated: Citizen presses **1 (YES - Problem Solved)**.
3. Status advances to `VERIFIED`.

### Step 6: Final Resolution & Citizen Rating
1. Official confirms ticket as `RESOLVED` with final summary.
2. Citizen Ramesh receives notification: *"Grievance Resolved! Please rate our service"*.
3. Citizen submits 5-star rating and satisfaction review.
4. Ticket automatically closes (`CLOSED`) and feeds into the Gram Sabha Analytics report.
