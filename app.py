"""
GramSeva (గ్రామసేవ) - Rural Panchayat Grievance Management System
Main Application Entry Point & Factory
Community Service Project (CSP) - e-Governance Civic Technology
"""

import os
from flask import Flask
from core.config import SECRET_KEY, UPLOAD_FOLDER, DEMO_MODE, DB_PATH, FLASK_DEBUG
from core.schema import init_db
from services.seed_service import seed_sample_data
from routes import register_routes

def create_app() -> Flask:
    """Application factory for GramSeva."""
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Security configuration
    app.secret_key = SECRET_KEY
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['DEMO_MODE'] = DEMO_MODE
    app.config['DB_PATH'] = DB_PATH
    app.config['DEBUG'] = FLASK_DEBUG
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # Initialize relational schema and seed default rural dataset
    init_db()
    seed_sample_data()

    # Register all modular blueprints
    register_routes(app)

    # Multilingual Localization Engine
    from core.translations import TRANSLATIONS, t as t_func, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
    from flask import request, session, jsonify

    @app.before_request
    def detect_and_sync_language():
        # Prefer session language if set, else read persistent cookie, fallback to default 'en'
        cookie_lang = request.cookies.get('gramseva_lang')
        if 'lang' not in session:
            session['lang'] = cookie_lang if cookie_lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        elif cookie_lang in SUPPORTED_LANGUAGES and cookie_lang != session['lang']:
            session['lang'] = cookie_lang

    @app.context_processor
    def inject_localization():
        lang = session.get('lang') or request.cookies.get('gramseva_lang') or DEFAULT_LANGUAGE
        if lang not in SUPPORTED_LANGUAGES:
            lang = DEFAULT_LANGUAGE
        def jinja_t(key, default=None):
            return t_func(key, lang=lang, default=default)
        return {
            'current_lang': lang,
            't': jinja_t,
            'SUPPORTED_LANGUAGES': SUPPORTED_LANGUAGES
        }

    @app.route('/api/set-language', methods=['POST'])
    def set_language_api():
        data = request.get_json(silent=True) or request.form or {}
        lang = (data.get('lang') or '').strip().lower()
        if not lang or lang not in SUPPORTED_LANGUAGES:
            return jsonify({'success': False, 'error': f'Unsupported language. Supported languages: {list(SUPPORTED_LANGUAGES)}'}), 400
        session['lang'] = lang
        resp = jsonify({'success': True, 'lang': lang, 'message': f'Language updated to {lang}'})
        resp.set_cookie('gramseva_lang', lang, max_age=31536000, samesite='Lax', path='/')
        return resp

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
