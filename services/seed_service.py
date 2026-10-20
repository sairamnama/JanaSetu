"""
GramSeva - Sample Data Seeder Service
Seeds realistic rural Panchayat datasets including departments, field officers,
registered citizens, field workers, civic grievances across all lifecycle stages,
resolution proofs, verification attempts, feedback, and notices.
"""

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from core.database import get_db_connection

def seed_sample_data():
    """Seeds the database with demonstration data if it hasn't been seeded yet."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        # Check if workers are seeded
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'worker'")
        if cursor.fetchone()[0] == 0:
            seed_workers_and_links(conn, cursor)
        # Ensure worker_assignments are populated for existing assigned grievances
        cursor.execute("SELECT COUNT(*) FROM worker_assignments")
        if cursor.fetchone()[0] == 0:
            seed_worker_assignments_helper(conn, cursor)
        conn.close()
        return

    # Seed Departments
    departments = [
        ('Rural Water Supply & Sanitation', 'WAT', 'Maintenance of drinking water borewells, overhead tanks, and pipelines', 'Sri Ramesh Varma (AE, RWS)'),
        ('Electricity & Streetlighting', 'ELEC', 'Repairs of village electrical lines, transformers, and LED streetlights', 'Sri Suresh Reddy (Line Inspector)'),
        ('Village Sanitation & Solid Waste', 'SAN', 'Street sweeping, door-to-door waste collection, and drainage de-silting', 'Smt. Lakshmi Devi (Sanitary Supervisor)'),
        ('Panchayat Roads & Infrastructure', 'ROAD', 'Internal CC roads, drainage construction, and culvert maintenance', 'Sri Anil Kumar (Panchayat Engineer)'),
        ('Public Health & Primary Care', 'HLTH', 'Mosquito fogging, drinking water chlorination, and health camp coordination', 'Dr. Radhika Sen (PHC Medical Officer)'),
        ('Anganwadi & School Infrastructure', 'EDU', 'School sanitation, drinking water, and safe playground maintenance', 'Smt. Saraswathi M. (CDPO)'),
        ('General Panchayat Administration', 'GEN', 'Certificates, ward boundary issues, village market, and civic welfare', 'Sri K. Venkat Rao (Panchayat Secretary)')
    ]
    cursor.executemany(
        "INSERT INTO departments (name, code, description, head_officer_name) VALUES (?, ?, ?, ?)",
        departments
    )

    # Seed Users (1 Admin, 4 Officers, 2 Workers, 3 Citizens)
    users = [
        # Admin / Secretary
        ('admin', generate_password_hash('admin123'), 'Sri K. Venkat Rao', 'admin', '9848011223', 'secretary@gramseva.gov.in', 1, 'Ananthapur Gram Panchayat', 'Panchayat Office, Main Road'),
        # Officers
        ('officer_water', generate_password_hash('officer123'), 'Sri Ramesh Varma', 'officer', '9848022334', 'water@gramseva.gov.in', 4, 'Ananthapur Gram Panchayat', 'RWS Office, Near Water Tank'),
        ('officer_power', generate_password_hash('officer123'), 'Sri Suresh Reddy', 'officer', '9848033445', 'power@gramseva.gov.in', 2, 'Ananthapur Gram Panchayat', 'APEPDCL Substation, Bypass Road'),
        ('officer_sanitation', generate_password_hash('officer123'), 'Smt. Lakshmi Devi', 'officer', '9848044556', 'sanitation@gramseva.gov.in', 3, 'Ananthapur Gram Panchayat', 'Panchayat Health Wing'),
        ('officer_roads', generate_password_hash('officer123'), 'Sri Anil Kumar', 'officer', '9848055667', 'roads@gramseva.gov.in', 5, 'Ananthapur Gram Panchayat', 'Engineering Section'),
        # Workers (Distinct WORKER Role)
        ('worker_shiva', generate_password_hash('worker123'), 'Sri Shiva Kumar', 'worker', '9848077889', 'shiva.worker@gramseva.gov.in', 4, 'Ananthapur Gram Panchayat', 'Ward 4 Water Works Shed'),
        ('worker_naresh', generate_password_hash('worker123'), 'Sri Naresh Babu', 'worker', '9848088990', 'naresh.worker@gramseva.gov.in', 2, 'Ananthapur Gram Panchayat', 'Substation Staff Quarters'),
        # Citizens
        ('citizen_ramesh', generate_password_hash('citizen123'), 'Ramesh Naidu', 'citizen', '9876543210', 'ramesh.naidu@gmail.com', 4, 'Ananthapur Gram Panchayat', 'Door No 4-22, Temple Street, Ward 4'),
        ('citizen_priya', generate_password_hash('citizen123'), 'Priya Sharma', 'citizen', '9876543211', 'priya.s@gmail.com', 2, 'Ananthapur Gram Panchayat', 'Door No 2-15, School Lane, Ward 2'),
        ('citizen_venkat', generate_password_hash('citizen123'), 'Venkat Ramana', 'citizen', '9876543212', 'venkat.ramana@gmail.com', 7, 'Ananthapur Gram Panchayat', 'Door No 7-88, Market Road, Ward 7')
    ]
    cursor.executemany(
        "INSERT INTO users (username, password_hash, full_name, role, mobile, email, ward_number, village, address) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        users
    )

    # Seed Officers Table
    cursor.execute("SELECT id FROM users WHERE username = 'officer_water'")
    u_water = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM users WHERE username = 'officer_power'")
    u_power = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM users WHERE username = 'officer_sanitation'")
    u_san = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM users WHERE username = 'officer_roads'")
    u_road = cursor.fetchone()[0]

    cursor.execute("SELECT id FROM departments WHERE code = 'WAT'")
    d_wat = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM departments WHERE code = 'ELEC'")
    d_elec = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM departments WHERE code = 'SAN'")
    d_san = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM departments WHERE code = 'ROAD'")
    d_road = cursor.fetchone()[0]

    officers = [
        (u_water, d_wat, 'Assistant Engineer (RWS)', 'OFF-WAT-01', 1),
        (u_power, d_elec, 'Senior Line Inspector', 'OFF-ELE-02', 1),
        (u_san, d_san, 'Chief Sanitary Inspector', 'OFF-SAN-03', 0),
        (u_road, d_road, 'Panchayat Civil Supervisor', 'OFF-ROA-04', 0)
    ]
    cursor.executemany(
        "INSERT INTO officers (user_id, department_id, designation, badge_id, active_tickets_count) VALUES (?, ?, ?, ?, ?)",
        officers
    )

    # Seed Workers Table
    cursor.execute("SELECT id FROM users WHERE username = 'worker_shiva'")
    u_w_shiva = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM users WHERE username = 'worker_naresh'")
    u_w_naresh = cursor.fetchone()[0]

    workers = [
        (u_w_shiva, d_wat, 'Pipe Fitter & Rural Plumber', 'WRK-WAT-01', 1),
        (u_w_naresh, d_elec, 'Certified Lineman & Electrician', 'WRK-ELE-02', 1)
    ]
    cursor.executemany(
        "INSERT INTO workers (user_id, department_id, skill_trade, badge_id, active_tickets_count) VALUES (?, ?, ?, ?, ?)",
        workers
    )

    cursor.execute("SELECT id FROM workers WHERE badge_id = 'WRK-WAT-01'")
    w_shiva_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM workers WHERE badge_id = 'WRK-ELE-02'")
    w_naresh_id = cursor.fetchone()[0]

    # Get officer IDs
    cursor.execute("SELECT id FROM officers WHERE badge_id = 'OFF-WAT-01'")
    off_wat_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM officers WHERE badge_id = 'OFF-ELE-02'")
    off_elec_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM officers WHERE badge_id = 'OFF-ROA-04'")
    off_road_id = cursor.fetchone()[0]

    # Get citizen IDs
    cursor.execute("SELECT id FROM users WHERE username = 'citizen_ramesh'")
    c_ramesh = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM users WHERE username = 'citizen_priya'")
    c_priya = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM users WHERE username = 'citizen_venkat'")
    c_venkat = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    admin_id = cursor.fetchone()[0]

    # Seed Grievances across all statuses
    now = datetime.now()
    g1_time = (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
    g2_time = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    g3_time = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    g4_time = (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
    g5_time = (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
    g6_time = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    grievances = [
        # G1: Water Supply - IN PROGRESS (Worker Shiva Kumar assigned)
        ('GRV-2026-00101', c_ramesh, 'Drinking Water & Supply',
         'Major drinking water pipeline burst near Shiva Temple',
         'The main 4-inch drinking water feeder pipeline burst 3 days ago. Thousands of liters of treated drinking water are flooding the street, and households in Ward 4 are experiencing zero water pressure in the morning.',
         4, 'Near Shiva Temple, Ward 4 Main Junction', 'High', 'IN_PROGRESS', d_wat, off_wat_id, w_shiva_id,
         None, 'Excavation completed, pipe joint replacement currently underway on-site.', g1_time, now.strftime("%Y-%m-%d %H:%M:%S")),

        # G2: Electricity - ASSIGNED (Worker Naresh assigned)
        ('GRV-2026-00102', c_priya, 'Electricity & Streetlights',
         'Sparks from damaged electric pole transformer causing total darkness',
         'Heavy winds caused tree branches to fall on the transformer near Government Primary School. Sparking was observed last evening and 8 streetlights along the student transit path are completely non-functional.',
         2, 'Opposite Zilla Parishad High School, Ward 2', 'High', 'ASSIGNED', d_elec, off_elec_id, w_naresh_id,
         None, 'Field inspection scheduled by Line Inspector today morning.', g2_time, (now - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")),

        # G3: Roads & Drainage - UNDER REVIEW
        ('GRV-2026-00103', c_ramesh, 'Roads & Drainage Systems',
         'Overflowing stormwater drain creating health hazard near Community Hall',
         'The concrete side-drain has been clogged with silt and plastic debris. Rainwater is backing up onto the pedestrian walkway, emitting severe foul smell.',
         4, 'Behind Gram Panchayat Community Hall', 'Medium', 'UNDER_REVIEW', d_road, None, None,
         None, None, g3_time, g3_time),

        # G4: Roads & Drainage - RESOLVED (Verified & Closed with Feedback)
        ('GRV-2026-00104', c_ramesh, 'Roads & Drainage Systems',
         'Deep hazardous pothole near weekly Rythu Bazaar market gate',
         'A large 2-foot pothole had developed right at the entrance of the agricultural market where heavy tractors and two-wheelers navigate daily.',
         4, 'Rythu Bazaar Gate No. 2, Ward 4', 'High', 'RESOLVED', d_road, off_road_id, None,
         None, 'Road surface cleared, compacted with wet mix macadam, and bitumen seal coat laid. Photo verified.', g4_time, (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")),

        # G5: Waste Management - SUBMITTED
        ('GRV-2026-00105', c_venkat, 'Waste Management & Sanitation',
         'Irregular dry & wet waste door-to-door collection in Ward 7',
         'Sanitation tractor has not visited the residential inner lanes of Ward 7 for the past four days. Waste is accumulating outside residences.',
         7, 'Bazaar Street, Ward 7', 'Medium', 'SUBMITTED', None, None, None,
         None, None, g5_time, g5_time),

        # G6: Health & Vector - CLOSED (With Feedback)
        ('GRV-2026-00106', c_priya, 'Public Health & Vector Control',
         'Mosquito breeding in stagnant water plot needing immediate fogging',
         'Vacant plot behind Anganwadi center is holding stagnant rain water. Severe mosquito menace has developed, posing dengue fever risk.',
         2, 'Plot 45, Near Anganwadi Center, Ward 2', 'Low', 'CLOSED', d_san, None, None,
         None, 'Larvicidal spray applied and cold fogging performed across Ward 2 on 28th Sep.', g6_time, (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"))
    ]

    cursor.executemany('''
    INSERT INTO grievances (
        tracking_id, citizen_id, category, title, description,
        ward_number, location_landmark, priority, status, department_id,
        assigned_officer_id, assigned_worker_id, evidence_image, resolution_notes, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', grievances)

    # Get grievance IDs
    cursor.execute("SELECT id FROM grievances WHERE tracking_id = 'GRV-2026-00101'")
    g1_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM grievances WHERE tracking_id = 'GRV-2026-00102'")
    g2_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM grievances WHERE tracking_id = 'GRV-2026-00103'")
    g3_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM grievances WHERE tracking_id = 'GRV-2026-00104'")
    g4_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM grievances WHERE tracking_id = 'GRV-2026-00105'")
    g5_id = cursor.fetchone()[0]

    # Seed Grievance Updates (Audit Trail)
    updates = [
        # G1 History
        (g1_id, None, 'SUBMITTED', 'Grievance submitted by citizen Ramesh Naidu via Web Portal.', c_ramesh, g1_time),
        (g1_id, 'SUBMITTED', 'UNDER_REVIEW', 'Verified by Panchayat Secretary K. Venkat Rao. Issue confirmed critical.', admin_id, (now - timedelta(days=2, hours=18)).strftime("%Y-%m-%d %H:%M:%S")),
        (g1_id, 'UNDER_REVIEW', 'ASSIGNED', 'Assigned to Rural Water Supply Department (AE Ramesh Varma) and Worker Shiva Kumar.', admin_id, (now - timedelta(days=2, hours=12)).strftime("%Y-%m-%d %H:%M:%S")),
        (g1_id, 'ASSIGNED', 'IN_PROGRESS', 'Worker Shiva Kumar mobilized to site. Excavation and pipe replacement started.', u_w_shiva, (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")),

        # G2 History
        (g2_id, None, 'SUBMITTED', 'Grievance registered by citizen Priya Sharma.', c_priya, g2_time),
        (g2_id, 'SUBMITTED', 'UNDER_REVIEW', 'Reviewed by admin. High school proximity flagged as urgent.', admin_id, (now - timedelta(days=1, hours=14)).strftime("%Y-%m-%d %H:%M:%S")),
        (g2_id, 'UNDER_REVIEW', 'ASSIGNED', 'Routed to Electricity Maintenance. Assigned to Line Inspector Suresh Reddy and Lineman Naresh.', admin_id, (now - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")),

        # G4 History (Completed through full workflow: WORK_COMPLETED -> OFFICER_VERIFICATION -> CITIZEN_VERIFICATION -> VERIFIED -> RESOLVED)
        (g4_id, None, 'SUBMITTED', 'Grievance registered by Ramesh Naidu.', c_ramesh, g4_time),
        (g4_id, 'SUBMITTED', 'UNDER_REVIEW', 'Verified by Panchayat Office.', admin_id, (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")),
        (g4_id, 'UNDER_REVIEW', 'ASSIGNED', 'Assigned to Roads Supervisor Anil Kumar.', admin_id, (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")),
        (g4_id, 'ASSIGNED', 'IN_PROGRESS', 'Patch repair crew mobilized with asphalt mix.', u_road, (now - timedelta(days=2, hours=12)).strftime("%Y-%m-%d %H:%M:%S")),
        (g4_id, 'IN_PROGRESS', 'WORK_COMPLETED', 'Worker marked patch repair as complete with on-site bitumen photo proof.', u_road, (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),
        (g4_id, 'WORK_COMPLETED', 'OFFICER_VERIFICATION', 'Officer Anil Kumar reviewed physical completion proof.', u_road, (now - timedelta(days=1, hours=18)).strftime("%Y-%m-%d %H:%M:%S")),
        (g4_id, 'OFFICER_VERIFICATION', 'CITIZEN_VERIFICATION', 'Officer approved completion proof and initiated citizen verification.', u_road, (now - timedelta(days=1, hours=12)).strftime("%Y-%m-%d %H:%M:%S")),
        (g4_id, 'CITIZEN_VERIFICATION', 'VERIFIED', 'Citizen Ramesh Naidu confirmed over automated telephony that the pothole is completely repaired (Response: YES).', c_ramesh, (now - timedelta(days=1, hours=6)).strftime("%Y-%m-%d %H:%M:%S")),
        (g4_id, 'VERIFIED', 'RESOLVED', 'Pothole remediation officially closed and resolved after confirmed verification.', admin_id, (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"))
    ]
    cursor.executemany(
        "INSERT INTO grievance_updates (grievance_id, from_status, to_status, remarks, updated_by_user_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        updates
    )

    # Seed Resolution Proof for G4
    cursor.execute('''
    INSERT INTO resolution_proofs (grievance_id, worker_id, proof_file, completion_notes, created_at)
    VALUES (?, ?, '/api/uploads/sample_road_repair.jpg', 'Pothole cleared of debris, filled with WMM base and layered with 40mm bitumen seal coat. Traffic open.', ?)
    ''', (g4_id, u_road, (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")))
    proof4_id = cursor.lastrowid

    # Seed Officer Verification for G4
    cursor.execute('''
    INSERT INTO officer_verifications (grievance_id, proof_id, officer_id, decision, remarks, created_at)
    VALUES (?, ?, ?, 'APPROVED', 'Inspected photo proof. Bitumen surface is level and meets Panchayat standards. Proceed to citizen verification.', ?)
    ''', (g4_id, proof4_id, u_road, (now - timedelta(days=1, hours=12)).strftime("%Y-%m-%d %H:%M:%S")))

    # Seed Citizen Verification for G4
    c_verif_ts = (now - timedelta(days=1, hours=6)).strftime("%Y-%m-%d %H:%M:%S")
    c_verif_req_ts = (now - timedelta(days=1, hours=12)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
    INSERT INTO citizen_verifications (
        grievance_id, citizen_id, attempt_number, method, verification_method,
        response, remarks, requested_timestamp, response_timestamp,
        verification_status, call_outcome, created_at
    ) VALUES (?, ?, 1, 'IVR', 'IVR', 'YES', 'Citizen Ramesh Naidu confirmed: Road is smooth and safe for tractors now.', ?, ?, 'CONFIRMED_SOLVED', 'ANSWERED', ?)
    ''', (g4_id, c_ramesh, c_verif_req_ts, c_verif_ts, c_verif_ts))

    # Seed Verification Attempt for G4
    attempt_ts = (now - timedelta(days=1, hours=6)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
    INSERT INTO verification_attempts (
        grievance_id, citizen_id, phone_number_ref, phone_ref, attempt_number,
        contact_number, method, call_outcome, citizen_response, requested_time,
        response_time, provider_ref, status, remarks, attempted_by_user_id, attempted_at
    ) VALUES (?, ?, '******3210', '******3210', 1, '******3210', 'IVR', 'ANSWERED', 'YES', ?, ?, 'MOCK-SEED-CALL-01', 'COMPLETED', '[Development / Mock Verification] Simulated call initiated -> Call answered -> Citizen confirmed issue resolution (YES).', ?, ?)
    ''', (g4_id, c_ramesh, c_verif_req_ts, attempt_ts, admin_id, attempt_ts))

    # Seed Feedback
    cursor.execute('''
    INSERT INTO feedback (grievance_id, citizen_id, star_rating, satisfaction, comments, submitted_at)
    VALUES (?, ?, 5, 'Satisfied', 'Prompt repair work by the Panchayat road supervisor. The road is smooth and safe for tractors and bikes now. Thank you GramSeva!', ?)
    ''', (g4_id, c_ramesh, (now - timedelta(hours=18)).strftime("%Y-%m-%d %H:%M:%S")))

    # Seed Notifications
    notifications = [
        (c_ramesh, g1_id, 'Status Update: In Progress', 'Your grievance GRV-2026-00101 (Water Pipeline Leak) has been updated to IN_PROGRESS by Worker Shiva Kumar.', 0),
        (c_priya, g2_id, 'Grievance Assigned', 'Your grievance GRV-2026-00102 has been assigned to Electricity Dept Inspector Suresh Reddy.', 0),
        (c_ramesh, g4_id, 'Grievance Resolved!', 'Grievance GRV-2026-00104 (Pothole at Rythu Bazaar) has been verified and resolved. Please rate our service!', 1),
        (admin_id, g5_id, 'New Grievance Submitted', 'New complaint GRV-2026-00105 in Ward 7 requires Panchayat verification.', 0)
    ]
    cursor.executemany(
        "INSERT INTO notifications (user_id, grievance_id, title, message, is_read) VALUES (?, ?, ?, ?, ?)",
        notifications
    )

    # Seed Announcements
    announcements = [
        ('Scheduled Drinking Water Supply Maintenance', 'Water Supply',
         'Please note that drinking water supply will be paused in Wards 3, 4, and 5 on Sunday between 10:00 AM and 3:00 PM due to pipeline overhaul. Residents are requested to store adequate water.',
         0, admin_id),
        ('Special Swachh Gram Village Cleanliness Drive', 'Sanitation',
         'The Gram Panchayat is conducting a collective village sanitation drive this Saturday starting at 7:00 AM. Ward members and youth clubs are cordially invited to participate.',
         0, admin_id),
        ('Free Medical Health Camp & Pulse Polio Drive', 'Health',
         'Primary Health Centre (PHC) will host a free health camp and child immunization drive on 15th October at the Gram Panchayat Sabha Bhavan. Doctors will be available from 9 AM to 4 PM.',
         1, admin_id),
        ('Ordinary Gram Sabha Meeting Announcement', 'General Admin',
         'Quarterly Gram Sabha meeting scheduled on October 25th at 10:30 AM to discuss winter crop canal allocations, street lighting expansion, and annual CSP grievance report.',
         0, admin_id)
    ]
    cursor.executemany(
        "INSERT INTO announcements (title, category, content, is_emergency, published_by) VALUES (?, ?, ?, ?, ?)",
        announcements
    )

    conn.commit()
    conn.close()

def seed_workers_and_links(conn, cursor):
    """Helper to ensure worker entities exist if database was previously created."""
    cursor.execute("SELECT id FROM users WHERE username = 'worker_shiva'")
    row = cursor.fetchone()
    if not row:
        cursor.execute('''
        INSERT INTO users (username, password_hash, full_name, role, mobile, email, ward_number, village, address)
        VALUES ('worker_shiva', ?, 'Sri Shiva Kumar', 'worker', '9848077889', 'shiva.worker@gramseva.gov.in', 4, 'Ananthapur Gram Panchayat', 'Ward 4 Water Works Shed')
        ''', (generate_password_hash('worker123'),))
        u_shiva = cursor.lastrowid
    else:
        u_shiva = row[0]

    cursor.execute("SELECT id FROM users WHERE username = 'worker_naresh'")
    row = cursor.fetchone()
    if not row:
        cursor.execute('''
        INSERT INTO users (username, password_hash, full_name, role, mobile, email, ward_number, village, address)
        VALUES ('worker_naresh', ?, 'Sri Naresh Babu', 'worker', '9848088990', 'naresh.worker@gramseva.gov.in', 2, 'Ananthapur Gram Panchayat', 'Substation Staff Quarters')
        ''', (generate_password_hash('worker123'),))
        u_naresh = cursor.lastrowid
    else:
        u_naresh = row[0]

    cursor.execute("SELECT id FROM departments WHERE code = 'WAT'")
    d_wat = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM departments WHERE code = 'ELEC'")
    d_elec = cursor.fetchone()[0]

    cursor.execute("SELECT id FROM workers WHERE badge_id = 'WRK-WAT-01'")
    if not cursor.fetchone():
        cursor.execute('''
        INSERT INTO workers (user_id, department_id, skill_trade, badge_id, active_tickets_count)
        VALUES (?, ?, 'Pipe Fitter & Rural Plumber', 'WRK-WAT-01', 1)
        ''', (u_shiva, d_wat))

    cursor.execute("SELECT id FROM workers WHERE badge_id = 'WRK-ELE-02'")
    if not cursor.fetchone():
        cursor.execute('''
        INSERT INTO workers (user_id, department_id, skill_trade, badge_id, active_tickets_count)
        VALUES (?, ?, 'Certified Lineman & Electrician', 'WRK-ELE-02', 1)
        ''', (u_naresh, d_elec))

    conn.commit()

def seed_worker_assignments_helper(conn, cursor):
    """Backfills worker_assignments for existing grievances assigned to workers."""
    cursor.execute("SELECT id FROM users WHERE role = 'officer' LIMIT 1")
    off_row = cursor.fetchone()
    assigner_id = off_row[0] if off_row else 1

    cursor.execute('''
    SELECT id, assigned_worker_id, department_id, status, created_at
    FROM grievances
    WHERE assigned_worker_id IS NOT NULL
    ''')
    rows = cursor.fetchall()
    for row in rows:
        status = 'IN_PROGRESS' if row['status'] == 'IN_PROGRESS' else ('COMPLETED' if row['status'] in ('WORK_COMPLETED', 'OFFICER_VERIFICATION', 'CITIZEN_VERIFICATION', 'VERIFIED', 'RESOLVED', 'CLOSED') else 'ASSIGNED')
        cursor.execute('''
        INSERT INTO worker_assignments (grievance_id, worker_id, department_id, assigned_by_user_id, assigned_at, assignment_status)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (row['id'], row['assigned_worker_id'], row['department_id'], assigner_id, row['created_at'], status))
    conn.commit()

