"""Seed the single default admin account. Use only for dev."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stellegent.db import admin_exists, init_db, create_user, get_user, update_user

DEFAULT_ADMIN_EMAIL = "admin@example.com"

init_db()
admin = get_user("admin")
if admin is None and not admin_exists():
    create_user("admin", "admin123", "admin", email=DEFAULT_ADMIN_EMAIL)
    print(f"created admin (superadmin): {DEFAULT_ADMIN_EMAIL}")
else:
    if admin is not None and not admin["email"]:
        update_user(admin["id"], email=DEFAULT_ADMIN_EMAIL)
        print(f"admin email set to {DEFAULT_ADMIN_EMAIL}")
    print("admin exists")
