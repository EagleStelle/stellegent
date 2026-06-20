"""CLI: `python -m stellegent.cli <command> ...`."""
from __future__ import annotations
import argparse
import json
import sys

from .pipeline import process_path
from .db import init_db, create_user, list_lectures, get_user_by_email, set_password


def cmd_process(args: argparse.Namespace) -> int:
    res = process_path(args.image, course_name=args.course)
    print(json.dumps(res, indent=2))
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    from .capture.live_ui import run_live
    from .pipeline import process_image

    def on_cap(frame):
        res = process_image(frame, course_name=args.course)
        print("[captured]", res["lecture_id"], "->", res["dir"])

    run_live(on_cap, prefer_pi=args.pi, fullscreen=args.fullscreen)
    return 0


def cmd_initdb(_args: argparse.Namespace) -> int:
    init_db()
    print("db initialized (migrations applied)")
    return 0


def cmd_adduser(args: argparse.Namespace) -> int:
    init_db()
    uid = create_user(args.username, args.password, args.role, email=args.email)
    print(f"created user id={uid}")
    return 0


def cmd_resetpw(args: argparse.Namespace) -> int:
    """Offline password reset (no email needed)."""
    init_db()
    user = get_user_by_email(args.email)
    if not user:
        print(f"no user with email {args.email}", file=sys.stderr)
        return 1
    set_password(user["id"], args.password)
    print(f"password reset for {user['username']}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    init_db()
    for r in list_lectures(date=args.date, course=args.course, q=args.q):
        print(f"{r['captured_at']}  {r['id']}  {r['course_name'] or '-'}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn
    if args.pi:
        from .capture.hub import get_hub
        get_hub(prefer_pi=True)  # prime singleton with picamera2
    uvicorn.run("stellegent.main:app", host=args.host, port=args.port,
                reload=args.reload)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="stellegent")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("process", help="Process an image file end-to-end")
    pr.add_argument("image")
    pr.add_argument("--course", default=None)
    pr.set_defaults(fn=cmd_process)

    cap = sub.add_parser("capture", help="Live camera capture UI")
    cap.add_argument("--course", default=None)
    cap.add_argument("--pi", action="store_true", help="prefer picamera2")
    cap.add_argument("--fullscreen", action="store_true")
    cap.set_defaults(fn=cmd_capture)

    sub.add_parser("initdb").set_defaults(fn=cmd_initdb)

    au = sub.add_parser("adduser")
    au.add_argument("username")
    au.add_argument("password")
    au.add_argument("--email", default=None)
    au.add_argument("--role", choices=["prof", "student", "admin"], required=True)
    au.set_defaults(fn=cmd_adduser)

    rp = sub.add_parser("resetpw", help="Offline password reset by email")
    rp.add_argument("email")
    rp.add_argument("password")
    rp.set_defaults(fn=cmd_resetpw)

    li = sub.add_parser("list")
    li.add_argument("--date")
    li.add_argument("--course")
    li.add_argument("--q")
    li.set_defaults(fn=cmd_list)

    se = sub.add_parser("serve")
    se.add_argument("--host", default="0.0.0.0")
    se.add_argument("--port", type=int, default=8000)
    se.add_argument("--reload", action="store_true")
    se.add_argument("--pi", action="store_true", help="prefer picamera2 (CSI cam)")
    se.set_defaults(fn=cmd_serve)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
