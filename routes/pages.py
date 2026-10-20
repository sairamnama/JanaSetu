"""
GramSeva - Frontend Page Routes & Portal Architecture
Provides distinct, isolated portal entry points and navigation for:
1. Citizen Portal (/citizen, /citizen/submit, /citizen/track)
2. Worker Portal (/worker, /worker/work, /worker/proof)
3. Panchayat Admin Portal (/admin, /admin/solve, /admin/workers)
Along with public landing, tracker, and civic analytics.
Protected by role_required decorators enforcing RBAC boundaries.
"""

from flask import render_template, redirect, url_for
from core.security import role_required

# ==========================================
# 1. PUBLIC ROUTES (No Login Required)
# ==========================================
def index():
    """Public Landing Page & Civic Notice Board."""
    return render_template('index.html')

def citizen_login_page():
    """Dedicated Citizen Login Page."""
    return render_template('citizen_login.html', initial_tab='login')

def citizen_register_page():
    """Dedicated Citizen Registration View."""
    return render_template('citizen_login.html', initial_tab='register')

def worker_login_page():
    """Dedicated Worker Login Page."""
    return render_template('worker_login.html')

def worker_register_page():
    """Dedicated Worker Registration Page."""
    return render_template('worker_register.html')

def admin_login_page():
    """Dedicated Admin / Officer Login Page."""
    return render_template('admin_login.html')

def track_page(tracking_id=None):
    """Public Grievance Tracker with interactive visual stepper."""
    return render_template('track.html', initial_tracking_id=tracking_id or '')

def analytics_page():
    """Gram Sabha Civic Analytics & Performance Dashboard."""
    return render_template('analytics.html')

# ==========================================
# 2. CITIZEN PORTAL ROUTES (Role: CITIZEN)
# ==========================================
@role_required(['citizen'])
def citizen_portal():
    """Citizen Redressal & Grievances Home."""
    return render_template('citizen_portal.html')

@role_required(['citizen'])
def citizen_submit():
    """Citizen Grievance Submission Form."""
    return render_template('citizen_submit.html')

@role_required(['citizen'])
def citizen_track(tracking_id=None):
    """Citizen Grievance Tracker View."""
    return render_template('citizen_track.html', initial_tracking_id=tracking_id or '')

# ==========================================
# 3. WORKER PORTAL ROUTES (Role: WORKER)
# ==========================================
@role_required(['worker'])
def worker_portal():
    """Field Staff & Technician Operations Home."""
    return render_template('worker_portal.html')

@role_required(['worker'])
def worker_work():
    """Field Staff Remediation Task Board."""
    return render_template('worker_work.html')

@role_required(['worker'])
def worker_proof():
    """Field Staff Work Proof & Resolution Reporting."""
    return render_template('worker_proof.html')

# ==========================================
# 4. PANCHAYAT / ADMIN PORTAL (Role: ADMIN, OFFICER)
# ==========================================
@role_required(['admin', 'officer'])
def admin_portal():
    """Panchayat Secretary & Sarpanch Administrative Dashboard Home."""
    return render_template('admin_portal.html')

@role_required(['admin', 'officer'])
def admin_solve():
    """Grievance Verification & Dispatch Board."""
    return render_template('admin_solve.html')

@role_required(['admin', 'officer'])
def admin_workers():
    """Field Workers Roster & Workload Management."""
    return render_template('admin_workers.html')

def register_pages(app):
    """Registers all frontend views directly onto the Flask app with role protection."""
    # Public routes
    app.add_url_rule('/', 'index', index)
    app.add_url_rule('/track', 'track_page', track_page)
    app.add_url_rule('/track/<tracking_id>', 'track_page_with_id', track_page)
    app.add_url_rule('/analytics', 'analytics_page', analytics_page)

    # Citizen portal routes
    app.add_url_rule('/citizen', 'citizen_portal', citizen_portal)
    app.add_url_rule('/citizen/submit', 'citizen_submit', citizen_submit)
    app.add_url_rule('/citizen/track', 'citizen_track', citizen_track)
    app.add_url_rule('/citizen/track/<tracking_id>', 'citizen_track_with_id', citizen_track)

    # Worker portal routes
    app.add_url_rule('/worker', 'worker_portal', worker_portal)
    app.add_url_rule('/worker/work', 'worker_work', worker_work)
    app.add_url_rule('/worker/proof', 'worker_proof', worker_proof)

    # Admin portal routes
    app.add_url_rule('/admin', 'admin_portal', admin_portal)
    app.add_url_rule('/admin/solve', 'admin_solve', admin_solve)
    app.add_url_rule('/admin/workers', 'admin_workers', admin_workers)

    # Login & Register routes
    app.add_url_rule('/citizen/login', 'citizen_login_page', citizen_login_page)
    app.add_url_rule('/login/citizen', 'citizen_login_page_alias', citizen_login_page)
    app.add_url_rule('/citizen/register', 'citizen_register_page', citizen_register_page)
    app.add_url_rule('/register/citizen', 'citizen_register_page_alias', citizen_register_page)
    app.add_url_rule('/register', 'register_redirect', citizen_register_page)

    app.add_url_rule('/worker/login', 'worker_login_page', worker_login_page)
    app.add_url_rule('/login/worker', 'worker_login_page_alias', worker_login_page)
    app.add_url_rule('/worker/register', 'worker_register_page', worker_register_page)
    app.add_url_rule('/register/worker', 'worker_register_page_alias', worker_register_page)

    app.add_url_rule('/admin/login', 'admin_login_page', admin_login_page)
    app.add_url_rule('/login/admin', 'admin_login_page_alias', admin_login_page)
    app.add_url_rule('/login', 'login_redirect', lambda: redirect('/citizen/login'))

    # Provide alias support for pages.<endpoint>
    for ep, fn in [
        ('pages.index', index),
        ('pages.citizen_login_page', citizen_login_page),
        ('pages.citizen_login_page_alias', citizen_login_page),
        ('pages.citizen_register_page', citizen_register_page),
        ('pages.citizen_register_page_alias', citizen_register_page),
        ('pages.worker_login_page', worker_login_page),
        ('pages.worker_login_page_alias', worker_login_page),
        ('pages.worker_register_page', worker_register_page),
        ('pages.worker_register_page_alias', worker_register_page),
        ('pages.admin_login_page', admin_login_page),
        ('pages.admin_login_page_alias', admin_login_page),
        ('pages.track_page', track_page),
        ('pages.track_page_with_id', track_page),
        ('pages.analytics_page', analytics_page),
        ('pages.citizen_portal', citizen_portal),
        ('pages.citizen_submit', citizen_submit),
        ('pages.citizen_track', citizen_track),
        ('pages.citizen_track_with_id', citizen_track),
        ('pages.worker_portal', worker_portal),
        ('pages.worker_work', worker_work),
        ('pages.worker_proof', worker_proof),
        ('pages.admin_portal', admin_portal),
        ('pages.admin_solve', admin_solve),
        ('pages.admin_workers', admin_workers),
    ]:
        app.view_functions[ep] = fn
