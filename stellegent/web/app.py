"""Flask app: HTML UI + JSON API."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from flask import (Flask, Blueprint, render_template, request, redirect,
                   url_for, jsonify, send_file, make_response, g, abort)

from ..config import JWT_SECRET, DATA_DIR
from ..db import (init_db, list_lectures, get_lecture, delete_lecture,
                  verify_user, add_annotation, get_annotations, list_audit)
from .auth import issue_token, login_required, log_action


auth_bp = Blueprint("auth", __name__)
ui_bp = Blueprint("ui", __name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")


# ---------- auth ----------
@auth_bp.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login_submit():
    username = request.form.get("username") or (request.json or {}).get("username")
    password = request.form.get("password") or (request.json or {}).get("password")
    user = verify_user(username or "", password or "")
    if not user:
        if request.is_json:
            return jsonify({"error": "invalid credentials"}), 401
        return render_template("login.html", error="Invalid credentials"), 401
    token = issue_token(user["id"], user["username"], user["role"])
    if request.is_json:
        return jsonify({"token": token, "role": user["role"]})
    resp = make_response(redirect(url_for("ui.dashboard")))
    resp.set_cookie("token", token, httponly=True, samesite="Lax",
                    max_age=30 * 60)
    return resp


@auth_bp.route("/logout")
def logout():
    resp = make_response(redirect(url_for("auth.login_page")))
    resp.delete_cookie("token")
    return resp


# ---------- UI ----------
@ui_bp.route("/")
@login_required()
def dashboard():
    date = request.args.get("date") or None
    course = request.args.get("course") or None
    q = request.args.get("q") or None
    rows = list_lectures(date=date, course=course, q=q)
    return render_template("dashboard.html", lectures=rows,
                           date=date or "", course=course or "", q=q or "",
                           user=g.user)


@ui_bp.route("/lecture/<lecture_id>")
@login_required()
def lecture_detail(lecture_id: str):
    row = get_lecture(lecture_id)
    if not row:
        abort(404)
    notes = get_annotations(lecture_id)
    return render_template("lecture.html", lec=row, notes=notes, user=g.user)


@ui_bp.route("/lecture/<lecture_id>/file")
@login_required()
def lecture_file(lecture_id: str):
    row = get_lecture(lecture_id)
    if not row:
        abort(404)
    kind = request.args.get("type", "pdf")
    key = {"pdf": "pdf_path", "docx": "docx_path", "txt": "txt_path",
           "image": "image_path", "manifest": "manifest_path"}.get(kind)
    if not key or not row[key]:
        abort(404)
    log_action(f"download:{kind}", lecture_id)
    return send_file(row[key], as_attachment=(kind != "image"))


# ---------- API ----------
@api_bp.route("/lectures")
@login_required()
def api_list():
    rows = list_lectures(date=request.args.get("date"),
                         course=request.args.get("course"),
                         q=request.args.get("q"))
    return jsonify([dict(r) for r in rows])


@api_bp.route("/lecture/<lecture_id>")
@login_required()
def api_get(lecture_id: str):
    row = get_lecture(lecture_id)
    if not row:
        return jsonify({"error": "not found"}), 404
    out = dict(row)
    try:
        out["manifest"] = json.loads(Path(row["manifest_path"]).read_text("utf-8"))
    except Exception:
        out["manifest"] = None
    out["annotations"] = [dict(a) for a in get_annotations(lecture_id)]
    return jsonify(out)


@api_bp.route("/lecture/<lecture_id>/file")
@login_required()
def api_file(lecture_id: str):
    return lecture_file(lecture_id)


@api_bp.route("/lecture/<lecture_id>/annotate", methods=["POST"])
@login_required()
def api_annotate(lecture_id: str):
    note = (request.json or request.form).get("note", "").strip()
    if not note:
        return jsonify({"error": "empty note"}), 400
    nid = add_annotation(lecture_id, g.user["sub"], note)
    log_action("annotate", lecture_id)
    return jsonify({"id": nid})


@api_bp.route("/lecture/<lecture_id>", methods=["DELETE"])
@login_required(roles=("prof", "admin"))
def api_delete(lecture_id: str):
    delete_lecture(lecture_id)
    log_action("delete", lecture_id)
    return jsonify({"ok": True})


@api_bp.route("/capture", methods=["POST"])
@login_required(roles=("prof", "admin"))
def api_capture():
    """Trigger a capture from the attached camera (synchronous)."""
    from ..capture.camera import open_camera
    from ..pipeline import process_image
    course = (request.json or {}).get("course") if request.is_json else request.form.get("course")
    cam = open_camera()
    try:
        frame = cam.read()
    finally:
        cam.release()
    if frame is None:
        return jsonify({"error": "camera read failed"}), 500
    res = process_image(frame, course_name=course)
    log_action("capture", res["lecture_id"])
    return jsonify(res)


@api_bp.route("/audit")
@login_required(roles=("admin",))
def api_audit():
    return jsonify([dict(r) for r in list_audit()])


def create_app() -> Flask:
    init_db()
    app = Flask(__name__,
                template_folder=str(Path(__file__).parent / "templates"),
                static_folder=str(Path(__file__).parent / "static"))
    app.secret_key = JWT_SECRET
    app.register_blueprint(auth_bp)
    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp)
    return app
