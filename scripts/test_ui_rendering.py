import sys
import os
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')
from app import app

class TestUIRendering(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_pages_render_english_and_telugu(self):
        routes = [
            '/',
            '/track',
            '/analytics',
            '/citizen/login',
            '/worker/login',
            '/admin/login',
        ]
        for route in routes:
            # English
            res_en = self.client.get(route, headers={'Cookie': 'gramseva_lang=en'})
            self.assertEqual(res_en.status_code, 200, f"Route {route} failed in English")
            self.assertIn(b'<!DOCTYPE html>', res_en.data)
            self.assertIn(b'lang="en"', res_en.data)

            # Telugu
            res_te = self.client.get(route, headers={'Cookie': 'gramseva_lang=te'})
            self.assertEqual(res_te.status_code, 200, f"Route {route} failed in Telugu")
            self.assertIn(b'<!DOCTYPE html>', res_te.data)
            self.assertIn(b'lang="te"', res_te.data)

    def test_css_tokens_and_telugu_rules(self):
        res = self.client.get('/static/css/style.css')
        self.assertEqual(res.status_code, 200)
        content = res.data.decode('utf-8')
        self.assertIn('--font-telugu', content)
        self.assertIn('html[lang="te"]', content)
        self.assertIn('--civic-primary: #0D5C3A;', content)
        self.assertIn('min-height: 44px;', content)

    def test_citizen_portal_authenticated_render(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'citizen'
            sess['username'] = 'ramesh2026'

        for route in ['/citizen', '/citizen/submit', '/citizen/track']:
            res = self.client.get(route, headers={'Cookie': 'gramseva_lang=te'})
            self.assertEqual(res.status_code, 200, f"Citizen route {route} failed")
            self.assertIn(b'lang="te"', res.data)

    def test_worker_portal_authenticated_render(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 6
            sess['role'] = 'worker'
            sess['username'] = 'shiva_worker'

        for route in ['/worker', '/worker/work', '/worker/proof']:
            res = self.client.get(route, headers={'Cookie': 'gramseva_lang=te'})
            self.assertEqual(res.status_code, 200, f"Worker route {route} failed")
            self.assertIn(b'lang="te"', res.data)

    def test_admin_portal_authenticated_render(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 8
            sess['role'] = 'admin'
            sess['username'] = 'admin_venkat'

        for route in ['/admin', '/admin/solve', '/admin/workers']:
            res = self.client.get(route, headers={'Cookie': 'gramseva_lang=te'})
            self.assertEqual(res.status_code, 200, f"Admin route {route} failed")
            self.assertIn(b'lang="te"', res.data)

if __name__ == '__main__':
    unittest.main()
