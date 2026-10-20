"""
GramSeva Routes Package
Registers all modular Blueprints and page views on the Flask application instance.
"""

from flask import Flask
from routes.pages import register_pages
from routes.auth import auth_bp
from routes.grievances import grievances_bp
from routes.worker import worker_bp
from routes.verification import verification_bp
from routes.feedback import feedback_bp
from routes.announcements import announcements_bp
from routes.departments import departments_bp
from routes.notifications import notifications_bp
from routes.analytics import analytics_bp
from routes.uploads import uploads_bp

def register_routes(app: Flask):
    """Registers all domain blueprints and page views with the Flask application."""
    register_pages(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(grievances_bp)
    app.register_blueprint(worker_bp)
    app.register_blueprint(verification_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(uploads_bp)
