"""Seed default admin/prof/student accounts. Use only for dev."""
from stellegent.db import init_db, create_user, get_user

init_db()
for u, p, r in [("admin", "admin123", "admin"),
                ("prof", "prof123", "prof"),
                ("student", "student123", "student")]:
    if get_user(u) is None:
        create_user(u, p, r)
        print(f"created {u} ({r})")
    else:
        print(f"exists {u}")
