"""
Step 1 Portal Separation & RBAC Verification Check
Tests isolated portal entry points, navigation boundaries, and cross-role protection.
"""

import sys
import os

# Add workspace root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

def run_checks():
    app.config['TESTING'] = True
    app.config['DEMO_MODE'] = True
    client = app.test_client()

    print("=" * 65)
    print(" Running Step 1: Portal Separation & RBAC Self-Check")
    print("=" * 65)

    # 1. Unauthenticated Direct URL Access to Protected Routes
    for route in ['/citizen', '/citizen/submit', '/citizen/track', '/worker', '/worker/work', '/worker/proof', '/admin', '/admin/solve', '/admin/workers']:
        res = client.get(route)
        assert res.status_code == 302, f"Expected 302 redirect for unauthenticated {route}, got {res.status_code}"
    print(" [PASS] 1. Unauthenticated direct URL access to protected portals redirected")

    # 2. Public Routes accessible without login
    for route in ['/', '/track', '/analytics']:
        res = client.get(route)
        assert res.status_code == 200, f"Expected 200 for public {route}, got {res.status_code}"
    print(" [PASS] 2. Public routes (Home, Track, Analytics) load without auth (HTTP 200)")

    # 3. Citizen Authentication and Navigation
    res = client.post('/api/demo-switch-user', json={'role': 'citizen'})
    assert res.status_code == 200 and res.get_json()['user']['role'] == 'citizen', "Citizen login failed"
    
    # Citizen can access ONLY Citizen Portal routes
    for route in ['/citizen', '/citizen/submit', '/citizen/track']:
        res = client.get(route)
        assert res.status_code == 200, f"Citizen failed to access permitted route {route} (got {res.status_code})"
    
    # Citizen CANNOT access Worker or Admin routes
    for forbidden in ['/worker', '/worker/work', '/worker/proof', '/admin', '/admin/solve', '/admin/workers']:
        res = client.get(forbidden)
        assert res.status_code == 403, f"Citizen was NOT rejected on {forbidden} (got {res.status_code})"
    print(" [PASS] 3. Citizen portal access verified (Only Home, Submit, Track allowed; Worker/Admin blocked with 403)")

    # 4. Worker Authentication and Navigation
    res = client.post('/api/demo-switch-user', json={'role': 'worker'})
    assert res.status_code == 200 and res.get_json()['user']['role'] == 'worker', "Worker login failed"
    
    # Worker can access ONLY Worker Portal routes
    for route in ['/worker', '/worker/work', '/worker/proof']:
        res = client.get(route)
        assert res.status_code == 200, f"Worker failed to access permitted route {route} (got {res.status_code})"
    
    # Worker CANNOT access Citizen or Admin routes (including /admin/workers)
    for forbidden in ['/citizen', '/citizen/submit', '/citizen/track', '/admin', '/admin/solve', '/admin/workers']:
        res = client.get(forbidden)
        assert res.status_code == 403, f"Worker was NOT rejected on {forbidden} (got {res.status_code})"
    print(" [PASS] 4. Worker portal access verified (Only Home, Work, Proof allowed; Citizen/Admin blocked with 403)")

    # 5. Admin Authentication and Navigation
    res = client.post('/api/demo-switch-user', json={'role': 'admin'})
    assert res.status_code == 200 and res.get_json()['user']['role'] == 'admin', "Admin login failed"
    
    # Admin can access Admin Portal routes
    for route in ['/admin', '/admin/solve', '/admin/workers']:
        res = client.get(route)
        assert res.status_code == 200, f"Admin failed to access permitted route {route} (got {res.status_code})"
    
    # Admin is separated from citizen and worker specific portals
    for forbidden in ['/citizen', '/citizen/submit', '/citizen/track', '/worker', '/worker/work', '/worker/proof']:
        res = client.get(forbidden)
        assert res.status_code == 403, f"Admin was not strictly separated on {forbidden} (got {res.status_code})"
    print(" [PASS] 5. Admin portal access verified (Home, Solve Grievances, Workers allowed; Citizen/Worker separated with 403)")

    # 6. Page Refresh while Authenticated
    # While admin is logged in, refresh /admin/workers
    res = client.get('/admin/workers')
    assert res.status_code == 200, "Refreshing /admin/workers while authenticated failed"
    
    # Switch to citizen and refresh /citizen/track
    client.post('/api/demo-switch-user', json={'role': 'citizen'})
    res = client.get('/citizen/track')
    assert res.status_code == 200, "Refreshing /citizen/track while authenticated failed"
    print(" [PASS] 6. Refreshing pages while authenticated maintains session (HTTP 200)")

    # 7. Logout flow
    res = client.post('/api/logout')
    assert res.status_code == 200, "Logout request failed"
    res = client.get('/api/current-user')
    assert not res.get_json()['logged_in'], "Session was not cleared after logout"
    # Verify protected route is now rejected after logout
    res = client.get('/citizen')
    assert res.status_code == 302, "Protected route accessible after logout"
    print(" [PASS] 7. Logout terminates session and restores protection")

    # 8. Navigation items inspection
    # Citizen layout contains only Citizen navigation
    client.post('/api/demo-switch-user', json={'role': 'citizen'})
    cit_html = client.get('/citizen').get_data(as_text=True)
    assert 'CITIZEN PORTAL' in cit_html, "Citizen badge missing from navbar"
    assert 'Submit Grievance' in cit_html, "Submit Grievance missing from citizen nav"
    assert 'Track Grievance' in cit_html, "Track Grievance missing from citizen nav"
    assert 'Solve Grievances' not in cit_html, "Admin navigation leaked to citizen"
    assert 'Workers Roster' not in cit_html, "Admin workers leaked to citizen"

    # Worker layout contains only Worker navigation
    client.post('/api/demo-switch-user', json={'role': 'worker'})
    wrk_html = client.get('/worker').get_data(as_text=True)
    assert 'FIELD WORKER' in wrk_html, "Worker badge missing from navbar"
    assert 'Work Proof &amp; Report' in wrk_html or 'Work Proof & Report' in wrk_html, "Proof missing from worker nav"
    assert 'Solve Grievances' not in wrk_html, "Admin navigation leaked to worker"
    assert 'Submit Grievance' not in wrk_html, "Citizen navigation leaked to worker"

    # Admin layout contains only Admin navigation
    client.post('/api/demo-switch-user', json={'role': 'admin'})
    adm_html = client.get('/admin').get_data(as_text=True)
    assert 'PANCHAYAT ADMIN' in adm_html, "Admin badge missing from navbar"
    assert 'Solve Grievances' in adm_html, "Solve Grievances missing from admin nav"
    assert 'Workers' in adm_html, "Workers missing from admin nav"
    print(" [PASS] 8. Navigation layout isolation verified (No cross-portal links leaked)")

    print("=" * 65)
    print(" ALL STEP 1 PORTAL SEPARATION CHECKS PASSED!")
    print("=" * 65)

if __name__ == '__main__':
    run_checks()
