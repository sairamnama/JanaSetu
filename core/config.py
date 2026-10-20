"""
GramSeva - Application Configuration
Handles environment configurations, file upload limits, and session secret security.
"""

import os

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _load_env_file():
    """Lightweight .env file loader using standard library to avoid external dependencies."""
    env_file = os.path.join(BASE_DIR, '.env')
    if os.path.isfile(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    k, v = k.strip(), v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v

_load_env_file()

# Database file location and credentials
DB_PATH = (
    os.environ.get('DATABASE_PATH') or
    os.environ.get('DB_PATH') or
    os.path.join(BASE_DIR, 'gramseva.db')
)
DB_USER = os.environ.get('DATABASE_USER', '')
DB_PASSWORD = os.environ.get('DATABASE_PASSWORD', '')

# Protected uploads directory (stored outside static to enforce RBAC)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed file extensions for attachments and proof photos
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
ALLOWED_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/pjpeg', 'image/webp',
    'application/pdf', 'application/octet-stream'
}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB maximum upload limit

# Magic byte signatures for file content validation
MAGIC_SIGNATURES = {
    'jpg': [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'png': [b'\x89PNG\r\n\x1a\n', b'\x89PNG'],
    'webp': [b'RIFF'],
    'pdf': [b'%PDF-'],
}

# Dangerous executable / script patterns to explicitly block
DANGEROUS_SIGNATURES = [
    b'MZ',          # Windows DOS/PE executable
    b'\x7fELF',     # Linux ELF executable
    b'<?php',       # PHP script
    b'<script',     # HTML/JS payload
    b'#!/bin/',     # Unix shell script
    b'#!/usr/bin/', # Unix script
]

# Secret key resolution (Environment variable -> secure random fallback)
SECRET_KEY = (
    os.environ.get('SECRET_KEY') or
    os.environ.get('FLASK_SECRET_KEY') or
    ('gramseva-sec-' + os.urandom(24).hex())
)

# Demo Mode toggle: MUST be disabled (false) by default in production
DEMO_MODE = os.environ.get('DEMO_MODE', 'false').lower() in ('true', '1', 'yes')

# Flask Debug mode toggle: MUST be disabled (false) by default in production
FLASK_DEBUG = (
    os.environ.get('FLASK_DEBUG', 'false').lower() in ('true', '1', 'yes') or
    os.environ.get('DEBUG', 'false').lower() in ('true', '1', 'yes')
)

def allowed_file(filename: str) -> bool:
    """Validates whether an uploaded filename has a safe allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_uploaded_file(file, max_size: int = MAX_UPLOAD_SIZE):
    """
    Comprehensive file security validator:
    - Validates filename safety (no path traversal)
    - Validates extension against strict whitelist
    - Validates MIME type
    - Validates file size (rejects empty or oversized files)
    - Validates magic header bytes against content spoofing
    - Explicitly blocks executable and script signatures
    Returns: (is_valid: bool, error_msg: str, file_info: dict)
    """
    import hashlib
    from werkzeug.utils import secure_filename

    if not file or not getattr(file, 'filename', None):
        return False, "No file provided or missing filename.", None

    original_filename = file.filename
    clean_name = secure_filename(original_filename)
    if not clean_name or '.' not in clean_name:
        return False, "Invalid or unsafe filename.", None

    ext = clean_name.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type '.{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}.", None

    # Validate MIME type if provided by client
    content_type = getattr(file, 'content_type', '') or ''
    if content_type:
        lowered_ct = content_type.lower().split(';')[0].strip()
        if lowered_ct not in ALLOWED_MIME_TYPES and not lowered_ct.startswith(('image/', 'application/pdf')):
            return False, f"Invalid MIME type '{content_type}'.", None

    # Validate file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size == 0:
        return False, "Uploaded file is empty (0 bytes).", None

    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        return False, f"File size ({actual_mb:.2f}MB) exceeds the maximum allowed limit of {max_mb:.1f}MB.", None

    # Validate file content / magic bytes
    header = file.read(32)
    file.seek(0)

    for bad_sig in DANGEROUS_SIGNATURES:
        if header.startswith(bad_sig):
            return False, "Malicious or executable file signature detected.", None

    expected_sigs = MAGIC_SIGNATURES.get(ext)
    if expected_sigs:
        matched = any(header.startswith(sig) for sig in expected_sigs)
        if ext == 'webp' and matched:
            matched = len(header) >= 12 and header[8:12] == b'WEBP'
        if not matched:
            return False, f"File content does not match expected {ext.upper()} format signature.", None

    # Calculate SHA-256 hash for audit integrity
    hasher = hashlib.sha256()
    while chunk := file.read(8192):
        hasher.update(chunk)
    file.seek(0)
    sha256_hash = hasher.hexdigest()

    file_info = {
        'original_filename': original_filename,
        'clean_filename': clean_name,
        'extension': ext,
        'size': file_size,
        'mime_type': content_type or f"image/{ext}",
        'sha256': sha256_hash
    }

    return True, None, file_info

# ==========================================
# Worker Loyalty Points Configuration
# ==========================================
LOYALTY_POINTS_CONFIG = {
    'INITIAL_POINTS': int(os.environ.get('WORKER_INITIAL_POINTS', 100)),
    'MIN_POINTS': int(os.environ.get('MIN_WORKER_POINTS', 0)),
    'ALLOW_NEGATIVE': os.environ.get('ALLOW_NEGATIVE_POINTS', 'false').lower() in ('true', '1', 'yes'),
    'REJECTED_ASSIGNMENT_PENALTY': int(os.environ.get('REJECTED_ASSIGNMENT_PENALTY', -5)),
    'MIN_ASSIGNMENT_LOYALTY_POINTS': int(os.environ.get('MIN_ASSIGNMENT_LOYALTY_POINTS', 60)),
}

INITIAL_WORKER_POINTS = LOYALTY_POINTS_CONFIG['INITIAL_POINTS']
MIN_WORKER_POINTS = LOYALTY_POINTS_CONFIG['MIN_POINTS']
REJECTED_ASSIGNMENT_PENALTY_POINTS = LOYALTY_POINTS_CONFIG['REJECTED_ASSIGNMENT_PENALTY']
MIN_ASSIGNMENT_LOYALTY_POINTS = LOYALTY_POINTS_CONFIG['MIN_ASSIGNMENT_LOYALTY_POINTS']

