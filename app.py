"""
GramSeva (గ్రామసేవ) - Rural Panchayat Grievance Management System
Main Application Entry Point & Factory
Community Service Project (CSP) - e-Governance Civic Technology
"""

import os
from flask import Flask
from core.config import SECRET_KEY, UPLOAD_FOLDER, DEMO_MODE, DB_PATH, FLASK_DEBUG
from core.schema import init_db
from core.database import get_db_connection
from core.security import login_required, role_required, mask_text, mask_phone
from core.constants import VALID_STATUSES, VALID_TRANSITIONS, CALL_OUTCOMES, CITIZEN_RESPONSES, VERIFICATION_METHODS
from services.seed_service import seed_sample_data
from services.verification_service import get_verification_service
from routes import register_routes

# Verification service instance (Mock for local/dev, pluggable for production)
verification_service = get_verification_service()

def create_app() -> Flask:
    """Application factory for GramSeva."""
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Security configuration
    app.secret_key = SECRET_KEY
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['DEMO_MODE'] = DEMO_MODE
    app.config['DB_PATH'] = DB_PATH
    app.config['DEBUG'] = FLASK_DEBUG

    # Initialize relational schema and seed default rural dataset
    init_db()
    seed_sample_data()

    # Register all modular blueprints
    register_routes(app)

    # Status route shortcut mapping directly to status state machine
    @app.route('/status', methods=['POST', 'PUT'])
    def root_status_route():
        from routes.grievances import direct_status_update
        return direct_status_update()

    return app

# Expose app instance at module level for WSGI servers, test runners, and run.bat
app = create_app()

if __name__ == '__main__':
    print("=" * 65)
    print("  GramSeva - Rural Panchayat Grievance System")
    print(f"  Status: Active & Modularized Architecture (Debug: {FLASK_DEBUG})")
    print("  Access Portal: http://127.0.0.1:5000")
    print("=" * 65)
    app.run(host=os.environ.get('HOST', '127.0.0.1'), port=int(os.environ.get('PORT', 5000)), debug=FLASK_DEBUG)
