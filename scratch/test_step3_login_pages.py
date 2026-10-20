"""
Step 3 Automated Verification Test Suite
Tests:
1. Citizen Login page (/citizen/login) & authentication flow
2. Worker Login page (/worker/login), skill lookup, & authentication flow
3. Admin Login page (/admin/login) & security authorization guardrails
4. Navigation links between all 3 login pages
5. Telugu language toggle & translation content presence
"""

import sys
import os
import unittest

sys.path.insert(0, r"d:\csp")

from app import app
from core.database import get_db_connection

class Step3SeparateLoginPagesTest(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['DEMO_MODE'] = True
        self.client = self.app.test_client()

    def test_01_citizen_login_page_and_flow(self):
        """1. Citizen Login: Page load, fields, auth flow, and redirect"""
        for route in ['/citizen/login', '/login/citizen']:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Route {route} failed to load.")
            html = res.data.decode('utf-8')
            # Check fields
            self.assertIn('name="name"', html, "Missing name field")
            self.assertIn('name="mobile"', html, "Missing mobile field")
            self.assertIn('name="password"', html, "Missing password field")
            # Check language selector
            self.assertIn('English', html)
            self.assertIn('తెలుగు', html)
            # Check links to other portals
            self.assertIn('/worker/login', html)
            self.assertIn('/admin/login', html)

        # Missing fields rejected
        res_empty = self.client.post('/api/login/citizen', json={})
        self.assertEqual(res_empty.status_code, 400)
        self.assertFalse(res_empty.get_json()['success'])

        # Non-existent citizen rejected
        res_not_found = self.client.post('/api/login/citizen', json={
            'name': 'Unknown Citizen',
            'mobile': '9999999999',
            'password': 'somepassword'
        })
        self.assertEqual(res_not_found.status_code, 404)

        # Invalid password rejected
        res_wrong_pw = self.client.post('/api/login/citizen', json={
            'name': 'Ramesh Naidu',
            'mobile': '9876543210',
            'password': 'wrongpassword'
        })
        self.assertEqual(res_wrong_pw.status_code, 401)

        # Valid Citizen login
        res_login = self.client.post('/api/login/citizen', json={
            'name': 'Ramesh Naidu',
            'mobile': '9876543210',
            'password': 'citizen123'
        })
        self.assertEqual(res_login.status_code, 200)
        data = res_login.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect'], '/citizen')
        self.assertEqual(data['user']['role'], 'citizen')

        # Check citizen can access Citizen Portal
        res_portal = self.client.get('/citizen')
        self.assertEqual(res_portal.status_code, 200)

        # Clear session
        self.client.post('/api/logout')
        print(" [PASS] 1. Citizen Login page, validation, authentication, and /citizen redirect verified.")

    def test_02_worker_login_page_and_flow(self):
        """2. Worker Login: Page load, fields, skill detection, auth flow, and redirect"""
        for route in ['/worker/login', '/login/worker']:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200)
            html = res.data.decode('utf-8')
            self.assertIn('name="name"', html)
            self.assertIn('name="worker_id"', html)
            self.assertIn('name="mobile"', html)
            self.assertIn('name="skill"', html)
            self.assertIn('name="password"', html)
            # Skills check
            for sk in ['Electrician', 'Plumber', 'Mechanic', 'Mason', 'Sanitation Worker', 'Other']:
                self.assertIn(sk, html, f"Missing skill: {sk}")
            self.assertIn('English', html)
            self.assertIn('తెలుగు', html)

        # Worker skill lookup API
        res_lookup = self.client.get('/api/worker-lookup?worker_id=WRK-WAT-01')
        self.assertEqual(res_lookup.status_code, 200)
        lookup_data = res_lookup.get_json()
        self.assertTrue(lookup_data['success'])
        self.assertTrue(lookup_data['found'])
        self.assertEqual(lookup_data['skill'], 'Plumber')
        self.assertEqual(lookup_data['name'], 'Sri Shiva Kumar')

        # Electrician lookup
        res_lookup_elec = self.client.get('/api/worker-lookup?worker_id=WRK-ELE-02')
        self.assertEqual(res_lookup_elec.status_code, 200)
        self.assertEqual(res_lookup_elec.get_json()['skill'], 'Electrician')

        # Worker login with invalid password
        res_wrong = self.client.post('/api/login/worker', json={
            'name': 'Sri Shiva Kumar',
            'worker_id': 'WRK-WAT-01',
            'mobile': '9848077889',
            'skill': 'Plumber',
            'password': 'badpassword'
        })
        self.assertEqual(res_wrong.status_code, 401)

        # Worker login success
        res_w_login = self.client.post('/api/login/worker', json={
            'name': 'Sri Shiva Kumar',
            'worker_id': 'WRK-WAT-01',
            'mobile': '9848077889',
            'skill': 'Plumber',
            'password': 'worker123'
        })
        self.assertEqual(res_w_login.status_code, 200)
        data = res_w_login.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect'], '/worker')
        self.assertEqual(data['user']['role'], 'worker')

        # Check worker can access Worker Portal
        res_w_portal = self.client.get('/worker')
        self.assertEqual(res_w_portal.status_code, 200)

        self.client.post('/api/logout')
        print(" [PASS] 2. Worker Login page, DB skill lookup, authentication, and /worker redirect verified.")

    def test_03_admin_login_page_and_guardrail(self):
        """3. Admin Login: Page load, fields, authorization validation, and redirect"""
        for route in ['/admin/login', '/login/admin']:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200)
            html = res.data.decode('utf-8')
            self.assertIn('name="name"', html)
            self.assertIn('name="mobile"', html)
            self.assertIn('name="employee_id"', html)
            self.assertIn('name="role"', html)
            self.assertIn('name="password"', html)

        # Attack Vector: Fake user trying to claim Admin access
        res_fake_admin = self.client.post('/api/login/admin', json={
            'name': 'Fake Intruder',
            'mobile': '9999999999',
            'employee_id': 'EMP-FAKE',
            'role': 'admin',
            'password': 'admin123'
        })
        self.assertEqual(res_fake_admin.status_code, 403, "Fake user gained admin access!")

        # Attack Vector: Registered citizen trying to gain admin access
        res_cit_as_admin = self.client.post('/api/login/admin', json={
            'name': 'Ramesh Naidu',
            'mobile': '9876543210',
            'employee_id': 'citizen_ramesh',
            'role': 'admin',
            'password': 'citizen123'
        })
        self.assertEqual(res_cit_as_admin.status_code, 403, "Citizen gained unauthorized admin access!")

        # Valid Admin login: Secretary
        res_adm_login = self.client.post('/api/login/admin', json={
            'name': 'Sri K. Venkat Rao',
            'mobile': '9848011223',
            'employee_id': 'admin',
            'role': 'admin',
            'password': 'admin123'
        })
        self.assertEqual(res_adm_login.status_code, 200)
        data = res_adm_login.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect'], '/admin')
        self.assertEqual(data['user']['role'], 'admin')

        # Access Admin Portal
        res_adm_portal = self.client.get('/admin')
        self.assertEqual(res_adm_portal.status_code, 200)

        self.client.post('/api/logout')

        # Valid Officer login
        res_off_login = self.client.post('/api/login/admin', json={
            'name': 'Sri Ramesh Varma',
            'mobile': '9848022334',
            'employee_id': 'OFF-WAT-01',
            'role': 'officer',
            'password': 'officer123'
        })
        self.assertEqual(res_off_login.status_code, 200)
        self.assertEqual(res_off_login.get_json()['user']['role'], 'officer')

        self.client.post('/api/logout')
        print(" [PASS] 3. Admin Login page, strict security authorization, and /admin redirect verified.")

    def test_04_cross_navigation_links(self):
        """4. Verify clear navigation links between all three login pages"""
        # Citizen Login page links
        res_cit = self.client.get('/citizen/login')
        html_cit = res_cit.data.decode('utf-8')
        self.assertIn('/worker/login', html_cit)
        self.assertIn('/admin/login', html_cit)

        # Worker Login page links
        res_wrk = self.client.get('/worker/login')
        html_wrk = res_wrk.data.decode('utf-8')
        self.assertIn('/citizen/login', html_wrk)
        self.assertIn('/admin/login', html_wrk)

        # Admin Login page links
        res_adm = self.client.get('/admin/login')
        html_adm = res_adm.data.decode('utf-8')
        self.assertIn('/citizen/login', html_adm)
        self.assertIn('/worker/login', html_adm)

        print(" [PASS] 4. Clear cross-navigation between all 3 login pages verified.")

    def test_05_telugu_language_support(self):
        """5. Verify Telugu translations on Citizen and Worker login pages"""
        res_cit = self.client.get('/citizen/login')
        html_cit = res_cit.data.decode('utf-8')
        self.assertIn('పౌరుల లాగిన్', html_cit, "Missing Telugu title on Citizen login")
        self.assertIn('పూర్తి పేరు', html_cit, "Missing Telugu name label")
        self.assertIn('నమోదైన మొబైల్ నంబర్', html_cit, "Missing Telugu mobile label")

        res_wrk = self.client.get('/worker/login')
        html_wrk = res_wrk.data.decode('utf-8')
        self.assertIn('వర్కర్ లాగిన్', html_wrk, "Missing Telugu title on Worker login")
        self.assertIn('వర్కర్ ఐడి', html_wrk, "Missing Telugu Worker ID label")
        self.assertIn('ఎలక్ట్రీషియన్', html_wrk, "Missing Telugu Electrician skill")
        self.assertIn('ప్లంబర్', html_wrk, "Missing Telugu Plumber skill")

        print(" [PASS] 5. Telugu language translations and toggle verified.")

if __name__ == '__main__':
    unittest.main()
