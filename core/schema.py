"""
GramSeva - Database Schema & Migration Definitions
Creates and updates all 13 core relational tables and audit tables.
"""

from core.database import get_db_connection
from core.config import INITIAL_WORKER_POINTS

def init_db():
    """Initializes the database schema and creates all tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table (Includes citizen, worker, officer, admin)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        role VARCHAR(20) NOT NULL CHECK(role IN ('citizen', 'worker', 'officer', 'admin')),
        mobile VARCHAR(15) NOT NULL,
        email VARCHAR(100),
        ward_number INTEGER DEFAULT 1,
        village VARCHAR(100) DEFAULT 'Ananthapur Gram Panchayat',
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 2. Departments Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL,
        code VARCHAR(20) UNIQUE NOT NULL,
        description TEXT,
        head_officer_name VARCHAR(100)
    )
    ''')

    # 3. Officers Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS officers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
        designation VARCHAR(100) NOT NULL,
        badge_id VARCHAR(50) UNIQUE NOT NULL,
        active_tickets_count INTEGER DEFAULT 0
    )
    ''')

    # 4. Workers Table (Distinct WORKER Role Entity)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS workers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
        skill_trade VARCHAR(100) NOT NULL,
        badge_id VARCHAR(50) UNIQUE NOT NULL,
        active_tickets_count INTEGER DEFAULT 0,
        loyalty_points INTEGER DEFAULT 100
    )
    ''')

    # Migration for workers loyalty_points and is_active columns
    cursor.execute("PRAGMA table_info(workers)")
    w_columns = [col[1] for col in cursor.fetchall()]
    if 'loyalty_points' not in w_columns:
        cursor.execute(f"ALTER TABLE workers ADD COLUMN loyalty_points INTEGER DEFAULT {INITIAL_WORKER_POINTS}")
        cursor.execute(f"UPDATE workers SET loyalty_points = {INITIAL_WORKER_POINTS} WHERE loyalty_points IS NULL")
    if 'is_active' not in w_columns:
        cursor.execute("ALTER TABLE workers ADD COLUMN is_active INTEGER DEFAULT 1")
        cursor.execute("UPDATE workers SET is_active = 1 WHERE is_active IS NULL")

    # 5. Grievances Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS grievances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_id VARCHAR(30) UNIQUE NOT NULL,
        citizen_id INTEGER NOT NULL REFERENCES users(id),
        category VARCHAR(50) NOT NULL,
        title VARCHAR(200) NOT NULL,
        description TEXT NOT NULL,
        ward_number INTEGER NOT NULL,
        location_landmark VARCHAR(255) NOT NULL,
        priority VARCHAR(20) DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High')),
        status VARCHAR(30) DEFAULT 'SUBMITTED' CHECK(status IN (
            'SUBMITTED', 'UNDER_REVIEW', 'ACCEPTED', 'ASSIGNED', 'IN_PROGRESS',
            'WORK_COMPLETED', 'OFFICER_VERIFICATION', 'CITIZEN_VERIFICATION',
            'VERIFIED', 'RESOLVED', 'CLOSED',
            'REWORK_REQUIRED', 'REOPENED', 'ESCALATED', 'REJECTED'
        )),
        department_id INTEGER REFERENCES departments(id),
        assigned_officer_id INTEGER REFERENCES officers(id),
        assigned_worker_id INTEGER REFERENCES workers(id),
        evidence_image VARCHAR(255),
        resolution_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Ensure assigned_worker_id column exists if table existed previously
    cursor.execute("PRAGMA table_info(grievances)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'assigned_worker_id' not in columns:
        cursor.execute("ALTER TABLE grievances ADD COLUMN assigned_worker_id INTEGER REFERENCES workers(id)")

    # Backward compatibility migration: Update CHECK constraint to support 'ACCEPTED' if table pre-dated it
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='grievances'")
    tbl_row = cursor.fetchone()
    if tbl_row and 'ACCEPTED' not in tbl_row[0]:
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute('''
        CREATE TABLE grievances_migration_tmp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_id VARCHAR(30) UNIQUE NOT NULL,
            citizen_id INTEGER NOT NULL REFERENCES users(id),
            category VARCHAR(50) NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT NOT NULL,
            ward_number INTEGER NOT NULL,
            location_landmark VARCHAR(255) NOT NULL,
            priority VARCHAR(20) DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High')),
            status VARCHAR(30) DEFAULT 'SUBMITTED' CHECK(status IN (
                'SUBMITTED', 'UNDER_REVIEW', 'ACCEPTED', 'ASSIGNED', 'IN_PROGRESS',
                'WORK_COMPLETED', 'OFFICER_VERIFICATION', 'CITIZEN_VERIFICATION',
                'VERIFIED', 'RESOLVED', 'CLOSED',
                'REWORK_REQUIRED', 'REOPENED', 'ESCALATED', 'REJECTED'
            )),
            department_id INTEGER REFERENCES departments(id),
            assigned_officer_id INTEGER REFERENCES officers(id),
            assigned_worker_id INTEGER REFERENCES workers(id),
            evidence_image VARCHAR(255),
            resolution_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        cursor.execute('''
        INSERT INTO grievances_migration_tmp (
            id, tracking_id, citizen_id, category, title, description,
            ward_number, location_landmark, priority, status, department_id,
            assigned_officer_id, assigned_worker_id, evidence_image,
            resolution_notes, created_at, updated_at
        )
        SELECT 
            id, tracking_id, citizen_id, category, title, description,
            ward_number, location_landmark, priority, status, department_id,
            assigned_officer_id, assigned_worker_id, evidence_image,
            resolution_notes, created_at, updated_at
        FROM grievances
        ''')
        cursor.execute("DROP TABLE grievances")
        cursor.execute("ALTER TABLE grievances_migration_tmp RENAME TO grievances")
        cursor.execute("PRAGMA foreign_keys=ON")

    # 6. Grievance Status History Table (Audit Trail)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS grievance_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grievance_id INTEGER NOT NULL REFERENCES grievances(id) ON DELETE CASCADE,
        from_status VARCHAR(30),
        to_status VARCHAR(30) NOT NULL,
        remarks TEXT NOT NULL,
        updated_by_user_id INTEGER NOT NULL REFERENCES users(id),
        user_role VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Ensure user_role column exists and backfill historical records
    cursor.execute("PRAGMA table_info(grievance_updates)")
    gu_columns = [col[1] for col in cursor.fetchall()]
    if 'user_role' not in gu_columns:
        cursor.execute("ALTER TABLE grievance_updates ADD COLUMN user_role VARCHAR(20)")

    cursor.execute('''
    UPDATE grievance_updates
    SET user_role = (
        SELECT role FROM users WHERE users.id = grievance_updates.updated_by_user_id
    )
    WHERE user_role IS NULL
    ''')

    # 7. Resolution Proofs Table (Preserves historical proofs submitted by workers)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS resolution_proofs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grievance_id INTEGER NOT NULL REFERENCES grievances(id) ON DELETE CASCADE,
        worker_id INTEGER REFERENCES users(id),
        proof_file VARCHAR(255) NOT NULL,
        completion_notes TEXT NOT NULL,
        remarks TEXT,
        location_coords VARCHAR(255),
        additional_evidence VARCHAR(255),
        metadata TEXT,
        proof_version INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Migration for resolution_proofs table to support step 4 fields
    cursor.execute("PRAGMA table_info(resolution_proofs)")
    rp_columns = [col[1] for col in cursor.fetchall()]
    if 'remarks' not in rp_columns:
        cursor.execute("ALTER TABLE resolution_proofs ADD COLUMN remarks TEXT")
    if 'location_coords' not in rp_columns:
        cursor.execute("ALTER TABLE resolution_proofs ADD COLUMN location_coords VARCHAR(255)")
    if 'additional_evidence' not in rp_columns:
        cursor.execute("ALTER TABLE resolution_proofs ADD COLUMN additional_evidence VARCHAR(255)")
    if 'metadata' not in rp_columns:
        cursor.execute("ALTER TABLE resolution_proofs ADD COLUMN metadata TEXT")
    if 'proof_version' not in rp_columns:
        cursor.execute("ALTER TABLE resolution_proofs ADD COLUMN proof_version INTEGER DEFAULT 1")


    # 8. Officer Verifications Table (Preserves historical officer decisions)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS officer_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grievance_id INTEGER NOT NULL REFERENCES grievances(id) ON DELETE CASCADE,
        proof_id INTEGER REFERENCES resolution_proofs(id),
        officer_id INTEGER NOT NULL REFERENCES users(id),
        decision VARCHAR(30) NOT NULL CHECK(decision IN ('APPROVED', 'REWORK_REQUESTED', 'REJECTED')),
        remarks TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 9. Citizen Verifications Table (Preserves citizen problem-solved responses)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS citizen_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grievance_id INTEGER NOT NULL REFERENCES grievances(id) ON DELETE CASCADE,
        citizen_id INTEGER NOT NULL REFERENCES users(id),
        attempt_number INTEGER NOT NULL DEFAULT 1,
        method VARCHAR(50) DEFAULT 'PORTAL',
        verification_method VARCHAR(50) DEFAULT 'PORTAL',
        response VARCHAR(30) NOT NULL CHECK(response IN ('YES', 'PARTIALLY', 'NO', 'UNABLE_TO_VERIFY')),
        call_outcome VARCHAR(30) NOT NULL DEFAULT 'ANSWERED' CHECK(call_outcome IN ('ANSWERED', 'NO_ANSWER', 'BUSY', 'INVALID_NUMBER', 'FAILED')),
        remarks TEXT,
        requested_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        response_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        verification_status VARCHAR(30) DEFAULT 'CONFIRMED',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Migration for citizen_verifications table to support Step 6 fields
    cursor.execute("PRAGMA table_info(citizen_verifications)")
    cv_columns = [col[1] for col in cursor.fetchall()]
    if 'attempt_number' not in cv_columns:
        cursor.execute("ALTER TABLE citizen_verifications ADD COLUMN attempt_number INTEGER DEFAULT 1")
    if 'method' not in cv_columns:
        cursor.execute("ALTER TABLE citizen_verifications ADD COLUMN method VARCHAR(50) DEFAULT 'PORTAL'")
    if 'requested_timestamp' not in cv_columns:
        cursor.execute("ALTER TABLE citizen_verifications ADD COLUMN requested_timestamp TIMESTAMP")
    if 'response_timestamp' not in cv_columns:
        cursor.execute("ALTER TABLE citizen_verifications ADD COLUMN response_timestamp TIMESTAMP")
    if 'verification_status' not in cv_columns:
        cursor.execute("ALTER TABLE citizen_verifications ADD COLUMN verification_status VARCHAR(30) DEFAULT 'CONFIRMED'")


    # 10. Verification Attempts Table (Preserves every contact/telephony attempt)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS verification_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grievance_id INTEGER NOT NULL REFERENCES grievances(id) ON DELETE CASCADE,
        citizen_id INTEGER REFERENCES users(id),
        phone_number_ref VARCHAR(30),
        phone_ref VARCHAR(30),
        attempt_number INTEGER NOT NULL,
        contact_number VARCHAR(20),
        method VARCHAR(50) NOT NULL DEFAULT 'IVR',
        call_outcome VARCHAR(30) NOT NULL CHECK(call_outcome IN ('ANSWERED', 'NO_ANSWER', 'BUSY', 'INVALID_NUMBER', 'FAILED')),
        citizen_response VARCHAR(30) CHECK(citizen_response IN ('YES', 'PARTIALLY', 'NO', 'UNABLE_TO_VERIFY', NULL)),
        requested_time TIMESTAMP,
        response_time TIMESTAMP,
        provider_ref VARCHAR(100),
        status VARCHAR(30) DEFAULT 'COMPLETED',
        remarks TEXT,
        attempted_by_user_id INTEGER REFERENCES users(id),
        attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Migration for verification_attempts table to support Step 9 phone verification requests
    cursor.execute("PRAGMA table_info(verification_attempts)")
    va_columns = [col[1] for col in cursor.fetchall()]
    if 'citizen_id' not in va_columns:
        cursor.execute("ALTER TABLE verification_attempts ADD COLUMN citizen_id INTEGER REFERENCES users(id)")
    if 'phone_number_ref' not in va_columns:
        cursor.execute("ALTER TABLE verification_attempts ADD COLUMN phone_number_ref VARCHAR(30)")
    if 'phone_ref' not in va_columns:
        cursor.execute("ALTER TABLE verification_attempts ADD COLUMN phone_ref VARCHAR(30)")
    if 'requested_time' not in va_columns:
        cursor.execute("ALTER TABLE verification_attempts ADD COLUMN requested_time TIMESTAMP")
    if 'response_time' not in va_columns:
        cursor.execute("ALTER TABLE verification_attempts ADD COLUMN response_time TIMESTAMP")
    if 'provider_ref' not in va_columns:
        cursor.execute("ALTER TABLE verification_attempts ADD COLUMN provider_ref VARCHAR(100)")
    if 'status' not in va_columns:
        cursor.execute("ALTER TABLE verification_attempts ADD COLUMN status VARCHAR(30) DEFAULT 'COMPLETED'")

    # Backfill missing citizen_id from grievances
    cursor.execute('''
    UPDATE verification_attempts
    SET citizen_id = (SELECT citizen_id FROM grievances WHERE grievances.id = verification_attempts.grievance_id)
    WHERE citizen_id IS NULL
    ''')

    # Backfill masked phone reference to prevent exposing citizen PII
    cursor.execute('''
    UPDATE verification_attempts
    SET phone_number_ref = '******' || SUBSTR(contact_number, -4),
        phone_ref = '******' || SUBSTR(contact_number, -4)
    WHERE (phone_number_ref IS NULL OR phone_ref IS NULL) AND contact_number IS NOT NULL AND LENGTH(contact_number) >= 4
    ''')

    # Backfill requested_time and response_time
    cursor.execute('''
    UPDATE verification_attempts
    SET requested_time = attempted_at,
        response_time = attempted_at
    WHERE requested_time IS NULL
    ''')

    # Backfill provider_ref
    cursor.execute('''
    UPDATE verification_attempts
    SET provider_ref = 'MOCK-ATTEMPT-' || id
    WHERE provider_ref IS NULL
    ''')

    # Backfill status
    cursor.execute('''
    UPDATE verification_attempts
    SET status = CASE 
        WHEN call_outcome = 'ANSWERED' THEN 'COMPLETED'
        WHEN call_outcome IN ('NO_ANSWER', 'BUSY') THEN 'PENDING_RETRY'
        ELSE 'FAILED'
    END
    WHERE status IS NULL
    ''')

    # 11. Citizen Feedback Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grievance_id INTEGER UNIQUE NOT NULL REFERENCES grievances(id) ON DELETE CASCADE,
        citizen_id INTEGER NOT NULL REFERENCES users(id),
        star_rating INTEGER NOT NULL CHECK(star_rating BETWEEN 1 AND 5),
        satisfaction VARCHAR(30) NOT NULL CHECK(satisfaction IN ('Satisfied', 'Partially Satisfied', 'Unsatisfied')),
        comments TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 12. Notifications Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        grievance_id INTEGER REFERENCES grievances(id) ON DELETE SET NULL,
        title VARCHAR(150) NOT NULL,
        message TEXT NOT NULL,
        is_read BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 13. Announcements Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(200) NOT NULL,
        category VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        is_emergency BOOLEAN DEFAULT 0,
        published_by INTEGER NOT NULL REFERENCES users(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 14. Worker Assignments Table (Tracks worker assignments, status & department allocations)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS worker_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grievance_id INTEGER NOT NULL REFERENCES grievances(id) ON DELETE CASCADE,
        worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
        department_id INTEGER NOT NULL REFERENCES departments(id),
        assigned_by_user_id INTEGER NOT NULL REFERENCES users(id),
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        assignment_status VARCHAR(30) DEFAULT 'ASSIGNED' CHECK(assignment_status IN ('ASSIGNED', 'ACCEPTED', 'REJECTED', 'IN_PROGRESS', 'COMPLETED', 'REWORK_REQUIRED', 'CANCELLED', 'REASSIGNED')),
        rejection_reason TEXT,
        accepted_at TIMESTAMP,
        rejected_at TIMESTAMP
    )
    ''')

    # Migration for worker_assignments table
    cursor.execute("PRAGMA table_info(worker_assignments)")
    wa_cols = [c[1] for c in cursor.fetchall()]
    if 'rejection_reason' not in wa_cols:
        cursor.execute("ALTER TABLE worker_assignments ADD COLUMN rejection_reason TEXT")
    if 'accepted_at' not in wa_cols:
        cursor.execute("ALTER TABLE worker_assignments ADD COLUMN accepted_at TIMESTAMP")
    if 'rejected_at' not in wa_cols:
        cursor.execute("ALTER TABLE worker_assignments ADD COLUMN rejected_at TIMESTAMP")

    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='worker_assignments'")
    wa_tbl = cursor.fetchone()
    if wa_tbl and 'ACCEPTED' not in wa_tbl[0]:
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute('''
        CREATE TABLE worker_assignments_tmp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grievance_id INTEGER NOT NULL REFERENCES grievances(id) ON DELETE CASCADE,
            worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
            department_id INTEGER NOT NULL REFERENCES departments(id),
            assigned_by_user_id INTEGER NOT NULL REFERENCES users(id),
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            assignment_status VARCHAR(30) DEFAULT 'ASSIGNED' CHECK(assignment_status IN ('ASSIGNED', 'ACCEPTED', 'REJECTED', 'IN_PROGRESS', 'COMPLETED', 'REWORK_REQUIRED', 'CANCELLED', 'REASSIGNED')),
            rejection_reason TEXT,
            accepted_at TIMESTAMP,
            rejected_at TIMESTAMP
        )
        ''')
        cursor.execute('''
        INSERT INTO worker_assignments_tmp (
            id, grievance_id, worker_id, department_id, assigned_by_user_id, assigned_at, assignment_status, rejection_reason, accepted_at, rejected_at
        )
        SELECT id, grievance_id, worker_id, department_id, assigned_by_user_id, assigned_at, assignment_status, rejection_reason, accepted_at, rejected_at
        FROM worker_assignments
        ''')
        cursor.execute("DROP TABLE worker_assignments")
        cursor.execute("ALTER TABLE worker_assignments_tmp RENAME TO worker_assignments")
        cursor.execute("PRAGMA foreign_keys=ON")

    # 15. Worker Point Transactions Table (Audit trail of every loyalty point adjustment)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS worker_point_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
        previous_balance INTEGER NOT NULL,
        points_changed INTEGER NOT NULL,
        new_balance INTEGER NOT NULL,
        reason TEXT NOT NULL,
        actor_id INTEGER REFERENCES users(id),
        actor_source VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_point_tx_worker ON worker_point_transactions(worker_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_worker_point_tx_created ON worker_point_transactions(created_at)")

    # Backfill initial onboarding transaction for workers without transaction history
    cursor.execute('''
    INSERT INTO worker_point_transactions (worker_id, previous_balance, points_changed, new_balance, reason, actor_source)
    SELECT id, 0, COALESCE(loyalty_points, ?), COALESCE(loyalty_points, ?), 'Initial onboarding balance', 'SYSTEM'
    FROM workers
    WHERE id NOT IN (SELECT DISTINCT worker_id FROM worker_point_transactions)
    ''', (INITIAL_WORKER_POINTS, INITIAL_WORKER_POINTS))

    conn.commit()
    conn.close()

