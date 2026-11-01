"""
Automated Comprehensive Test Suite for Language Switching & Internationalization
Tests:
1. Language switching API (/api/set-language)
2. Cookie and session persistence
3. Pre-render template localization (English vs Telugu) across all portals
4. Single consistent language selector header check (no duplicates, no Hindi option)
5. Session/cookie persistence through citizen, worker, and admin login/logout
6. Proper rendering of public pages (Home, Track, Analytics, Logins)
"""

import unittest
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from core.database import get_db_connection

class TestLanguageSwitching(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_01_language_selector_count_and_options(self):
        """Verify only one language selector exists and only EN and TE options are offered."""
        for path in ['/', '/track', '/analytics', '/citizen/login', '/worker/login', '/admin/login']:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Failed to load {path}")
            html = res.get_data(as_text=True)

            # Check that there is at most one lang-selector-group in the layout
            matches = re.findall(r'class="[^"]*lang-selector-group[^"]*"', html)
            self.assertEqual(len(matches), 1, f"Expected exactly 1 lang-selector-group on {path}, got {len(matches)}")

            # Check buttons
            btn_matches = re.findall(r'class="[^"]*lang-switch-btn[^"]*"[^>]*data-lang="([^"]+)"', html)
            self.assertEqual(len(btn_matches), 2, f"Expected 2 language buttons on {path}, got {len(btn_matches)}: {btn_matches}")
            self.assertIn('en', btn_matches)
            self.assertIn('te', btn_matches)
            self.assertNotIn('hi', btn_matches, "Hindi option must not be present")

    def test_02_set_language_api(self):
        """Test /api/set-language endpoint for setting and rejecting invalid languages."""
        # Valid language: Telugu
        res = self.client.post('/api/set-language',
                               data=json.dumps({'lang': 'te'}),
                               content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('lang'), 'te')

        # Check cookie
        cookies = res.headers.getlist('Set-Cookie')
        self.assertTrue(any('gramseva_lang=te' in c for c in cookies), "gramseva_lang cookie must be set to 'te'")

        # Invalid language: Hindi (unsupported)
        res_hi = self.client.post('/api/set-language',
                                  data=json.dumps({'lang': 'hi'}),
                                  content_type='application/json')
        self.assertEqual(res_hi.status_code, 400)

        # Invalid language: French
        res_fr = self.client.post('/api/set-language',
                                  data=json.dumps({'lang': 'fr'}),
                                  content_type='application/json')
        self.assertEqual(res_fr.status_code, 400)

    def test_03_server_side_telugu_rendering_public_pages(self):
        """Test that pages are pre-rendered in Telugu when gramseva_lang cookie is 'te'."""
        self.client.set_cookie('gramseva_lang', 'te')

        # 1. Home page
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('<html lang="te">', html)
        self.assertIn('గ్రామసేవ', html)
        self.assertIn('గ్రామీణ ప్రజా సమస్యల పరిష్కార వేదిక', html)

        # 2. Track page
        res = self.client.get('/track')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('<html lang="te">', html)
        self.assertIn('ఫిర్యాదు ట్రాకింగ్', html)
        self.assertIn('ప్రజా ఫిర్యాదు స్థితిని ట్రాక్ చేయండి', html)

        # 3. Analytics page
        res = self.client.get('/analytics')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('<html lang="te">', html)
        self.assertIn('గ్రామ సభ పౌర విశ్లేషణ', html)

        # 4. Citizen Login page
        res = self.client.get('/citizen/login')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('<html lang="te">', html)
        self.assertIn('పౌరుల లాగిన్', html)

        # 5. Worker Login page
        res = self.client.get('/worker/login')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('<html lang="te">', html)
        self.assertIn('వర్కర్ లాగిన్', html)

        # 6. Admin Login page
        res = self.client.get('/admin/login')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('<html lang="te">', html)
        self.assertIn('పంచాయతీ అడ్మిన్ లాగిన్', html)

    def test_04_citizen_auth_and_portal_language_persistence(self):
        """Verify citizen login and portal retain selected Telugu language."""
        self.client.set_cookie('gramseva_lang', 'te')

        # Login as citizen
        login_res = self.client.post('/api/login/citizen',
                                     data=json.dumps({'phone': '9876543210', 'password': 'citizen123'}),
                                     content_type='application/json')
        self.assertEqual(login_res.status_code, 200)
        data = login_res.get_json()
        self.assertTrue(data.get('success'))

        # Access citizen dashboard
        dash_res = self.client.get('/citizen')
        self.assertEqual(dash_res.status_code, 200)
        html = dash_res.get_data(as_text=True)
        self.assertIn('<html lang="te">', html)
        self.assertIn('పౌర సేవల హోమ్', html)
        self.assertIn('పౌరుల ఫిర్యాదుల డ్యాష్‌బోర్డ్', html)
        self.assertIn('ఫిర్యాదు సమర్పించండి', html)

        # Access submit complaint page
        sub_res = self.client.get('/citizen/submit')
        self.assertEqual(sub_res.status_code, 200)
        sub_html = sub_res.get_data(as_text=True)
        self.assertIn('<html lang="te">', sub_html)
        self.assertIn('ఫిర్యాదు నమోదు', sub_html)

        # Logout citizen and verify language is preserved
        logout_res = self.client.get('/logout')
        self.assertEqual(logout_res.status_code, 200)
        post_logout_res = self.client.get('/')
        self.assertEqual(post_logout_res.status_code, 200)
        self.assertIn('<html lang="te">', post_logout_res.get_data(as_text=True))

    def test_05_worker_auth_and_portal_language_persistence(self):
        """Verify worker login and portal retain selected Telugu language."""
        self.client.set_cookie('gramseva_lang', 'te')

        # Login as worker
        login_res = self.client.post('/api/login/worker',
                                     data=json.dumps({'worker_id': 'WRK-WAT-01', 'password': 'worker123'}),
                                     content_type='application/json')
        self.assertEqual(login_res.status_code, 200)
        data = login_res.get_json()
        self.assertTrue(data.get('success'))

        # Worker home
        home_res = self.client.get('/worker')
        self.assertEqual(home_res.status_code, 200)
        html = home_res.get_data(as_text=True)
        self.assertIn('<html lang="te">', html)
        self.assertIn('లాయల్టీ పాయింట్లు', html)
        self.assertIn('వర్కర్ హోమ్', html)

        # Worker tasks
        work_res = self.client.get('/worker/work')
        self.assertEqual(work_res.status_code, 200)
        work_html = work_res.get_data(as_text=True)
        self.assertIn('<html lang="te">', work_html)
        self.assertIn('నాకు కేటాయించిన క్షేత్రస్థాయి పనులు', work_html)

        # Worker proof
        proof_res = self.client.get('/worker/proof')
        self.assertEqual(proof_res.status_code, 200)
        proof_html = proof_res.get_data(as_text=True)
        self.assertIn('<html lang="te">', proof_html)
        self.assertIn('పని పూర్తయిన రుజువులు', proof_html)

        # Logout
        self.client.get('/logout')

    def test_06_admin_auth_and_portal_language_persistence(self):
        """Verify admin login and portal retain selected Telugu language."""
        self.client.set_cookie('gramseva_lang', 'te')

        # Login as admin
        login_res = self.client.post('/api/login/admin',
                                     data=json.dumps({
                                         'name': 'Sri K. Venkat Rao',
                                         'mobile': '9848011223',
                                         'employee_id': 'admin',
                                         'role': 'admin',
                                         'password': 'admin123'
                                     }),
                                     content_type='application/json')
        self.assertEqual(login_res.status_code, 200)
        data = login_res.get_json()
        self.assertTrue(data.get('success'))

        # Admin dashboard
        adm_res = self.client.get('/admin')
        self.assertEqual(adm_res.status_code, 200)
        html = adm_res.get_data(as_text=True)
        self.assertIn('<html lang="te">', html)
        self.assertIn('పంచాయతీ పరిపాలనా కన్సోల్', html)
        self.assertIn('ఫిర్యాదుల పరిష్కారం', html)

        # Admin solve
        solve_res = self.client.get('/admin/solve')
        self.assertEqual(solve_res.status_code, 200)
        solve_html = solve_res.get_data(as_text=True)
        self.assertIn('<html lang="te">', solve_html)
        self.assertIn('ఫిర్యాదుల పరిష్కారం &amp; సిబ్బంది కేటాయింపు', solve_html)

        # Admin workers
        workers_res = self.client.get('/admin/workers')
        self.assertEqual(workers_res.status_code, 200)
        workers_html = workers_res.get_data(as_text=True)
        self.assertIn('<html lang="te">', workers_html)
        self.assertIn('సిబ్బంది జాబితా', workers_html)

        # Logout
        self.client.get('/logout')

    def test_07_switching_back_to_english(self):
        """Verify switching back to English updates rendering immediately."""
        self.client.set_cookie('gramseva_lang', 'en')
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('<html lang="en">', html)
        self.assertIn('GramSeva', html)
        self.assertIn('Rural Civic Redressal', html)

    def test_08_header_clean_navigation_and_bilingual_cycling(self):
        """Verify removal of duplicate sign-in buttons and clean English -> Telugu -> English header cycling."""
        routes_to_test = ['/', '/track', '/analytics']

        for route in routes_to_test:
            # Step 1: English
            self.client.set_cookie('gramseva_lang', 'en')
            res_en = self.client.get(route)
            self.assertEqual(res_en.status_code, 200)
            html_en = res_en.get_data(as_text=True)

            # Ensure duplicate sign-in buttons are NOT in navbar
            navbar_en = html_en.split('<nav class="main-navbar">')[1].split('</nav>')[0]
            self.assertNotIn('btn_sign_in_citizen', navbar_en)
            self.assertNotIn('btn_sign_in_worker', navbar_en)
            self.assertNotIn('Sign In as Citizen', navbar_en)
            self.assertNotIn('Sign In as Worker', navbar_en)
            self.assertNotIn('Sign In as Administrator', navbar_en)

            # Ensure all 6 clean navigation links are present in English
            self.assertIn('>Home<', html_en)
            self.assertIn('>Citizen Portal<', html_en)
            self.assertIn('>Worker Portal<', html_en)
            self.assertIn('>Admin / Officials<', html_en)
            self.assertIn('>Track Grievance<', html_en)
            self.assertIn('>Analytics<', html_en)

            # Step 2: Switch to Telugu
            self.client.set_cookie('gramseva_lang', 'te')
            res_te = self.client.get(route)
            self.assertEqual(res_te.status_code, 200)
            html_te = res_te.get_data(as_text=True)

            self.assertIn('>హోమ్<', html_te)
            self.assertIn('>పౌరుల పోర్టల్<', html_te)
            self.assertIn('>వర్కర్ పోర్టల్<', html_te)
            self.assertIn('>పంచాయతీ అధికారులు / అడ్మిన్<', html_te)
            self.assertIn('>ఫిర్యాదు ట్రాకింగ్<', html_te)
            self.assertIn('>విశ్లేషణ &amp; నివేదికలు<', html_te)

            # Step 3: Switch BACK to English
            self.client.set_cookie('gramseva_lang', 'en')
            res_en_back = self.client.get(route)
            self.assertEqual(res_en_back.status_code, 200)
            html_en_back = res_en_back.get_data(as_text=True)

            # Confirm English is restored cleanly
            self.assertIn('<html lang="en">', html_en_back)
            self.assertIn('>Home<', html_en_back)
            self.assertIn('>Citizen Portal<', html_en_back)
            self.assertIn('>Worker Portal<', html_en_back)
            self.assertIn('>Admin / Officials<', html_en_back)
            self.assertIn('>Track Grievance<', html_en_back)
            self.assertIn('>Analytics<', html_en_back)

            # Confirm no leftover Telugu labels in navbar
            self.assertNotIn('>పౌరుల పోర్టల్<', html_en_back)
            self.assertNotIn('>వర్కర్ పోర్టల్<', html_en_back)
            self.assertNotIn('లాగిన్ అవ్వండి', html_en_back.split('<nav class="main-navbar">')[1].split('</nav>')[0])

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    unittest.main()
