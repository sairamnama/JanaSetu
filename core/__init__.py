"""
GramSeva Core Module
Provides database access, configuration, security decorators, and schema management.
"""

from core.config import BASE_DIR, DB_PATH, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, SECRET_KEY, DEMO_MODE, allowed_file
from core.database import get_db_connection
from core.schema import init_db
from core.security import login_required, role_required, mask_text, mask_phone
from core.constants import (
    VALID_STATUSES,
    VALID_TRANSITIONS,
    CALL_OUTCOMES,
    CITIZEN_RESPONSES,
    VERIFICATION_METHODS,
    CATEGORY_DEPARTMENT_MAP,
    SYSTEM_ROLES,
    ROLE_ALLOWED_TRANSITIONS,
    validate_transition,
    record_status_history,
    apply_status_transition
)

