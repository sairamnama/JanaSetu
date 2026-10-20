"""
GramSeva - Security & Access Control Helpers
Implements authentication decorators, RBAC checks, and PII masking for rural citizen privacy.
"""

import re
from functools import wraps
from flask import request, jsonify, session, redirect, url_for, render_template

def login_required(f):
    """Ensures a valid user session is active before allowing access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/') or request.is_json or request.path in ('/status', '/status/'):
                return jsonify({'success': False, 'error': 'Authentication required. Please log in.'}), 401
            try:
                if request.path.startswith('/worker'):
                    return redirect(url_for('worker_login_page'))
                elif request.path.startswith('/admin'):
                    return redirect(url_for('admin_login_page'))
                else:
                    return redirect(url_for('citizen_login_page'))
            except Exception:
                return redirect('/citizen/login')
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    """Ensures the active user has one of the specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/') or request.is_json or request.path in ('/status', '/status/'):
                    return jsonify({'success': False, 'error': 'Authentication required.'}), 401
                try:
                    if 'worker' in allowed_roles and 'citizen' not in allowed_roles and 'admin' not in allowed_roles:
                        return redirect(url_for('worker_login_page'))
                    elif 'admin' in allowed_roles or 'officer' in allowed_roles:
                        return redirect(url_for('admin_login_page'))
                    else:
                        return redirect(url_for('citizen_login_page'))
                except Exception:
                    return redirect('/citizen/login')
            if session.get('role') not in allowed_roles:
                if request.path.startswith('/api/') or request.is_json or request.path in ('/status', '/status/'):
                    return jsonify({'success': False, 'error': f'Access forbidden. Requires one of: {allowed_roles}'}), 403
                return render_template('unauthorized.html', role=session.get('role'), allowed_roles=allowed_roles), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def mask_text(text: str) -> str:
    """Masks names or identifiers to protect privacy from public visitors."""
    if not text:
        return ""
    if len(text) <= 4:
        return "****"
    return text[:2] + "*" * (len(text) - 4) + text[-2:]

def mask_phone(phone: str) -> str:
    """Masks phone numbers to protect citizen PII on public status checks."""
    if not phone:
        return ""
    phone_str = str(phone).strip()
    if phone_str.startswith("******") and len(phone_str) >= 10:
        return phone_str
    clean = re.sub(r'\D', '', phone_str)
    if len(clean) >= 10:
        return "******" + clean[-4:]
    return "****"
