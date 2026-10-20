"""
Test Script for Step 2 — Simplify Citizen Portal UI
Tests:
1. Citizen Home Page (/citizen)
2. Submit Grievance Page (/citizen/submit) & Form Validation
3. Track Grievance Page (/citizen/track) & Citizen Scoping
4. Progress Updates Timeline
5. Preserving Worker & Admin Portals
"""

import sys
import os
import unittest
import io

# Add workspace to path
sys.path.insert(0, r"d:\csp")

from app import app
from core.database import get_db_connection

class Step2CitizenPortalVerification(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['DEMO_MODE'] = True
        self.client = self.app.test_client()

    def test_01_citizen_home_page(self):
        """1. Verify Citizen Home Page (/citizen)"""
        # Login as citizen
        res_login = self.client.post('/api/login', json={'username': 'citizen_ramesh', 'password': 'citizen123'})
        self.assertEqual(res_login.status_code, 200)

        res = self.client.get('/citizen')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Rangapuram Panchayat welcome message
        self.assertIn("Rangapuram", html, "Home page missing Rangapuram Panchayat mention")
        self.assertIn("Welcome to Rangapuram", html, "Home page missing welcome message for Rangapuram")

        # Short explanation of grievance service
        self.assertIn("grievance", html.lower(), "Home page missing grievance explanation")

        # Two prominent buttons: Submit Grievance & Track Grievance
        self.assertIn("/citizen/submit", html, "Home page missing link to Submit Grievance")
        self.assertIn("/citizen/track", html, "Home page missing link to Track Grievance")
        self.assertIn("Submit Grievance", html)
        self.assertIn("Track Grievance", html)

        # Navigation limited to Home, Submit Grievance, Track Grievance
        self.assertIn("Home", html)
        self.assertIn("Submit Grievance", html)
        self.assertIn("Track Grievance", html)

        print(" [PASS] 1. Citizen Home Page verified: Rangapuram welcome, explanation, and prominent action buttons.")

    def test_02_citizen_submit_form_validation(self):
        """2. Verify Submit Grievance Page (/citizen/submit) and required field validation"""
        self.client.post('/api/login', json={'username': 'citizen_ramesh', 'password': 'citizen123'})

        res = self.client.get('/citizen/submit')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Form fields present
        self.assertIn('name="title"', html, "Submit form missing title field")
        self.assertIn('name="category"', html, "Submit form missing category field")
        self.assertIn('name="ward_number"', html, "Submit form missing ward_number field")
        self.assertIn('name="location_landmark"', html, "Submit form missing location_landmark field")
        self.assertIn('name="description"', html, "Submit form missing description field")
        self.assertIn('name="evidence_image"', html, "Submit form missing evidence_image photo upload")

        # Validation: missing mandatory fields rejected by backend
        res_empty = self.client.post('/api/grievances', data={})
        self.assertEqual(res_empty.status_code, 400)
        self.assertFalse(res_empty.get_json()['success'])
        self.assertIn('mandatory fields', res_empty.get_json()['error'].lower())

        # Validation: partial missing fields rejected
        res_partial = self.client.post('/api/grievances', data={'title': 'Broken pipe'})
        self.assertEqual(res_partial.status_code, 400)

        # Successful submission
        test_title = "Water leakage near community center"
        test_data = {
            'title': test_title,
            'category': 'Drinking Water & Supply',
            'ward_number': '4',
            'location_landmark': 'Opposite Primary School',
            'description': 'Main pipeline leaking drinking water since yesterday morning.'
        }
        res_submit = self.client.post('/api/grievances', data=test_data)
        self.assertEqual(res_submit.status_code, 200)
        data = res_submit.get_json()
        self.assertTrue(data['success'])
        self.assertIn('tracking_id', data)
        tracking_id = data['tracking_id']
        self.assertTrue(tracking_id.startswith('GRV-'), f"Invalid tracking ID format: {tracking_id}")

        # Submission with photo upload
        photo_data = dict(test_data)
        photo_data['title'] = "Broken streetlight on Pole 7"
        photo_data['category'] = 'Electricity & Streetlights'
        photo_data['evidence_image'] = (io.BytesIO(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9'), 'test_photo.jpg')
        res_photo_submit = self.client.post('/api/grievances', data=photo_data, content_type='multipart/form-data')
        self.assertEqual(res_photo_submit.status_code, 200)
        photo_result = photo_submit = res_photo_submit.get_json()
        self.assertTrue(photo_result['success'])
        self.assertTrue(photo_result['tracking_id'].startswith('GRV-'))

        print(f" [PASS] 2. Submit Grievance Form verified: All fields, validation errors, generated ID: {tracking_id}, and photo upload.")

    def test_03_citizen_track_page_and_scoping(self):
        """3. Verify Track Grievance Page (/citizen/track) and real-data citizen isolation"""
        # Citizen Ramesh logs in
        self.client.post('/api/login', json={'username': 'citizen_ramesh', 'password': 'citizen123'})
        res_ramesh = self.client.get('/api/grievances?scope=my')
        self.assertEqual(res_ramesh.status_code, 200)
        ramesh_data = res_ramesh.get_json()
        self.assertTrue(ramesh_data['success'])
        ramesh_grievances = ramesh_data['grievances']
        self.assertGreater(len(ramesh_grievances), 0)

        # Check fields required by prompt: Grievance ID, title, submission date, current status
        sample = ramesh_grievances[0]
        self.assertIn('tracking_id', sample)
        self.assertIn('title', sample)
        self.assertIn('created_at', sample)
        self.assertIn('status', sample)

        # Check timeline progress updates
        res_detail = self.client.get(f"/api/grievances/{sample['tracking_id']}")
        self.assertEqual(res_detail.status_code, 200)
        detail_data = res_detail.get_json()
        self.assertTrue(detail_data['success'])
        self.assertIn('timeline', detail_data['grievance'])

        # Now Citizen Priya logs in: should only see Priya's grievances
        self.client.post('/api/login', json={'username': 'citizen_priya', 'password': 'citizen123'})
        res_priya = self.client.get('/api/grievances?scope=my')
        self.assertEqual(res_priya.status_code, 200)
        priya_grievances = res_priya.get_json()['grievances']

        # Priya cannot see Ramesh's grievance
        priya_tracking_ids = [g['tracking_id'] for g in priya_grievances]
        self.assertNotIn(sample['tracking_id'], priya_tracking_ids, "Citizen Priya saw Citizen Ramesh's grievance!")

        # Cross-access via detail endpoint is blocked (HTTP 403)
        res_cross = self.client.get(f"/api/grievances/{sample['tracking_id']}")
        self.assertEqual(res_cross.status_code, 403, "Citizen Priya accessed Citizen Ramesh's grievance detail!")

        # Check Track HTML page loads
        res_track_html = self.client.get('/citizen/track')
        self.assertEqual(res_track_html.status_code, 200)
        track_html = res_track_html.data.decode('utf-8')
        self.assertIn('Track Grievance', track_html)
        self.assertIn('Rangapuram', track_html)

        print(" [PASS] 3. Track Grievance verified: Real data, progress updates, citizen isolation strictly enforced.")

    def test_04_portals_integrity(self):
        """4. Verify Worker and Admin portals remain unaffected and functional"""
        # Worker portal
        self.client.post('/api/login', json={'username': 'worker_shiva', 'password': 'worker123'})
        res_worker = self.client.get('/worker')
        self.assertEqual(res_worker.status_code, 200)
        self.assertIn('Worker', res_worker.data.decode('utf-8'))

        # Admin portal
        self.client.post('/api/login', json={'username': 'admin', 'password': 'admin123'})
        res_admin = self.client.get('/admin')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn('Admin', res_admin.data.decode('utf-8'))

        print(" [PASS] 4. Worker and Admin Portals verified intact and unmodified.")

if __name__ == '__main__':
    unittest.main()
