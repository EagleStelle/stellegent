"""Seed the single default admin account. Use only for dev."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stellegent.db import admin_exists, init_db, create_user, get_user

init_db()
if get_user("admin") is None and not admin_exists():
    create_user("admin", "admin123", "admin")
    print("created admin (superadmin)")
else:
    print("admin exists")
