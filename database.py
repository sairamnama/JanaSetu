"""
GramSeva Database Compatibility Layer
Maintains backwards compatibility for existing scripts and commands importing from database.py.
Forwards to modular components in core.database, core.schema, and services.seed_service.
"""

from core.config import DB_PATH
from core.database import get_db_connection
from core.schema import init_db
from services.seed_service import seed_sample_data, seed_workers_and_links

if __name__ == '__main__':
    print("=" * 65)
    print(" GramSeva Database Migration & Seeding Utility")
    print("=" * 65)
    print("Initializing relational schema...")
    init_db()
    print("Seeding rural Panchayat records...")
    seed_sample_data()
    print("Database ready!")
