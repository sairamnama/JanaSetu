"""
GramSeva Database Seeding CLI Tool
Re-initializes tables and populates sample rural Panchayat records.
Usage:
    python scripts/seed_db.py [--reset]
"""

import sys
import os

# Add parent directory to sys.path so core and services can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schema import init_db
from core.database import get_db_connection
from core.config import DB_PATH
from services.seed_service import seed_sample_data

def reset_and_seed():
    print("=" * 60)
    print(" GramSeva Database Seeder")
    print(f" Target Database: {DB_PATH}")
    print("=" * 60)

    if '--reset' in sys.argv:
        print("[!] --reset specified. Clearing existing data...")
        conn = get_db_connection()
        cursor = conn.cursor()
        tables = [
            'feedback', 'verification_attempts', 'citizen_verifications',
            'officer_verifications', 'resolution_proofs', 'grievance_updates',
            'grievances', 'workers', 'officers', 'departments',
            'notifications', 'announcements', 'users'
        ]
        for t in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {t}")
        conn.commit()
        conn.close()
        print("[OK] Tables dropped.")

    print("[*] Initializing relational schema...")
    init_db()
    print("[OK] Schema initialized.")

    print("[*] Seeding rural Panchayat demo records...")
    seed_sample_data()
    print("[OK] Database successfully seeded with demo personas and tickets.")

if __name__ == '__main__':
    reset_and_seed()
