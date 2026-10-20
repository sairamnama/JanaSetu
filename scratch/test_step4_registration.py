"""
Test Step 4: Add Registration to All Three Portals
Validates:
1. New citizen registers -> account saved -> citizen logged in -> redirect /citizen.
2. Existing citizen logs in -> /citizen.
3. Duplicate citizen mobile prevented with clear error.
4. New worker registers -> profile saved (active_tickets_count=0) -> worker authenticated -> redirect /worker.
5. Existing worker logs in -> /worker.
6. Duplicate worker ID and duplicate worker mobile prevented.
7. Unauthorized users cannot register as admins (403 forbidden).
8. Worker and citizen pages support English and Telugu localization.
"""

import unittest
import uuid
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from core.database import get_db_connection

class TestStep4Registration(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_citizen_registration_and_auto_login(self):
        mobile = f"99{uuid.uuid4().int % 100000000:08d}"
        res = self.client.post('/api/register', json={
            'full_name': 'Anil Rao',
            'mobile': mobile,
            'ward_number': 4,
            'address': 'Door 4-12, Temple Street',
            'password': 'citizen_secret_123',
            'confirm_password': 'citizen_secret_123'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data.get('redirect'), '/citizen')
        self.assertEqual(data['user']['role'], 'citizen')

        # Check session is logged in and can access /citizen
        portal_res = self.client.get('/citizen')
        self.assertEqual(portal_res.status_code, 200)
        self.assertIn(b'Rangapuram', portal_res.data)

        # Verify record in database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT full_name, mobile, ward_number, address FROM users WHERE mobile = ?", (mobile,))
        row = c.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row['full_name'], 'Anil Rao')
        self.assertEqual(row['mobile'], mobile)

    def test_02_citizen_duplicate_mobile_rejected(self):
        mobile = f"99{uuid.uuid4().int % 100000000:08d}"
        # First registration
        res1 = self.client.post('/api/register', json={
            'full_name': 'Original Citizen',
            'mobile': mobile,
            'password': 'pass',
            'confirm_password': 'pass'
        })
        self.assertEqual(res1.status_code, 200)

        # Duplicate registration with same mobile
        res2 = self.client.post('/api/register', json={
            'full_name': 'Duplicate Citizen',
            'mobile': mobile,
            'password': 'pass',
            'confirm_password': 'pass'
        })
        self.assertEqual(res2.status_code, 400)
        data2 = res2.get_json()
        self.assertFalse(data2['success'])
        self.assertIn('already registered', data2['error'].lower())

    def test_03_existing_citizen_login(self):
        # Existing seeded citizen Ramesh Naidu (9876543210, citizen123)
        res = self.client.post('/api/login/citizen', json={
            'name': 'Ramesh Naidu',
            'mobile': '9876543210',
            'password': 'citizen123'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data.get('redirect'), '/citizen')

    def test_04_worker_registration_and_authentication(self):
        w_id = f"WRK-TEST-{uuid.uuid4().hex[:4].upper()}"
        mobile = f"88{uuid.uuid4().int % 100000000:08d}"
        res = self.client.post('/api/register/worker', json={
            'full_name': 'Ravi Kumar Electrician',
            'worker_id': w_id,
            'mobile': mobile,
            'work_type': 'Electrician',
            'experience': '5 Years Certified',
            'password': 'worker_pass_123',
            'confirm_password': 'worker_pass_123'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data.get('redirect'), '/worker')
        self.assertEqual(data['user']['role'], 'worker')

        # Check worker can access /worker
        portal_res = self.client.get('/worker')
        self.assertEqual(portal_res.status_code, 200)

        # Verify worker record in DB: active_tickets_count must be 0
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT w.*, u.full_name, u.mobile FROM workers w JOIN users u ON w.user_id = u.id WHERE w.badge_id = ?", (w_id,))
        row = c.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row['badge_id'], w_id)
        self.assertEqual(row['active_tickets_count'], 0)
        self.assertIn('Electrician', row['skill_trade'])

    def test_05_worker_duplicate_checks(self):
        w_id = f"WRK-DUP-{uuid.uuid4().hex[:4].upper()}"
        mobile1 = f"88{uuid.uuid4().int % 100000000:08d}"
        mobile2 = f"88{uuid.uuid4().int % 100000000:08d}"

        # Register worker 1
        res1 = self.client.post('/api/register/worker', json={
            'full_name': 'Worker First',
            'worker_id': w_id,
            'mobile': mobile1,
            'work_type': 'Plumber',
            'password': 'pass',
            'confirm_password': 'pass'
        })
        self.assertEqual(res1.status_code, 200)

        # Attempt same worker ID with different mobile
        res2 = self.client.post('/api/register/worker', json={
            'full_name': 'Worker Second',
            'worker_id': w_id,
            'mobile': mobile2,
            'work_type': 'Plumber',
            'password': 'pass',
            'confirm_password': 'pass'
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn('worker id is already registered', res2.get_json()['error'].lower())

        # Attempt duplicate mobile with different worker ID
        res3 = self.client.post('/api/register/worker', json={
            'full_name': 'Worker Third',
            'worker_id': f"WRK-NEW-{uuid.uuid4().hex[:4].upper()}",
            'mobile': mobile1,
            'work_type': 'Plumber',
            'password': 'pass',
            'confirm_password': 'pass'
        })
        self.assertEqual(res3.status_code, 400)
        self.assertIn('mobile number is already registered', res3.get_json()['error'].lower())

    def test_06_existing_worker_login(self):
        # Seeded worker Shiva Kumar (WRK-WAT-01, 9848077889, worker123)
        res = self.client.post('/api/login/worker', json={
            'name': 'Sri Shiva Kumar',
            'worker_id': 'WRK-WAT-01',
            'mobile': '9848077889',
            'skill': 'Plumber',
            'password': 'worker123'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data.get('redirect'), '/worker')

    def test_07_unauthorized_users_cannot_register_as_admin(self):
        # 1. Attempt registering role='admin' on /api/register
        res1 = self.client.post('/api/register', json={
            'full_name': 'Hacker Admin',
            'mobile': '9999999999',
            'role': 'admin',
            'password': 'password123'
        })
        self.assertEqual(res1.status_code, 403)
        self.assertIn('prohibited', res1.get_json()['error'].lower())

        # 2. Attempt registering on /api/register/admin without admin session
        res2 = self.client.post('/api/register/admin', json={
            'full_name': 'Public Admin',
            'mobile': '9999999998',
            'password': 'password123'
        })
        self.assertEqual(res2.status_code, 403)
        self.assertIn('disabled', res2.get_json()['error'].lower())

    def test_08_password_mismatch_validation(self):
        # Citizen mismatch
        res1 = self.client.post('/api/register', json={
            'full_name': 'Mismatch Citizen',
            'mobile': '9111111111',
            'password': 'pass1',
            'confirm_password': 'pass2'
        })
        self.assertEqual(res1.status_code, 400)
        self.assertIn('passwords do not match', res1.get_json()['error'].lower())

        # Worker mismatch
        res2 = self.client.post('/api/register/worker', json={
            'full_name': 'Mismatch Worker',
            'worker_id': 'WRK-MISMATCH',
            'mobile': '9222222222',
            'work_type': 'Mechanic',
            'password': 'pass1',
            'confirm_password': 'pass2'
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn('passwords do not match', res2.get_json()['error'].lower())

    def test_09_registration_and_login_pages_rendered_with_bilingual_support(self):
        # 1. Citizen login & registration page
        c_page = self.client.get('/citizen/login')
        self.assertEqual(c_page.status_code, 200)
        self.assertIn(b'Citizen Portal', c_page.data)
        self.assertIn(b'Already registered? Login', c_page.data)
        self.assertIn(b'New user? Register', c_page.data)
        self.assertIn('తెలుగు'.encode('utf-8'), c_page.data)

        # /citizen/register route
        cr_page = self.client.get('/citizen/register')
        self.assertEqual(cr_page.status_code, 200)

        # 2. Worker login page
        w_page = self.client.get('/worker/login')
        self.assertEqual(w_page.status_code, 200)
        self.assertIn(b'Worker Login', w_page.data)
        self.assertIn(b'Register worker profile', w_page.data)
        self.assertIn('తెలుగు'.encode('utf-8'), w_page.data)

        # 3. Worker registration page
        wr_page = self.client.get('/worker/register')
        self.assertEqual(wr_page.status_code, 200)
        self.assertIn(b'Worker Registration', wr_page.data)
        self.assertIn(b'Unique Worker ID', wr_page.data)
        self.assertIn('తెలుగు'.encode('utf-8'), wr_page.data)

        # 4. Admin login page has restricted registration notice
        a_page = self.client.get('/admin/login')
        self.assertEqual(a_page.status_code, 200)
        self.assertIn(b'Restricted Access', a_page.data)
        self.assertIn(b'Registration Policy', a_page.data)

if __name__ == '__main__':
    unittest.main()
