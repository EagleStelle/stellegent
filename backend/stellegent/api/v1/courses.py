"""Course catalog reads plus faculty/admin course management."""
from __future__ import annotations
import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...db import (
    can_manage_course, create_course, delete_course, get_course,
    list_course_lecture_ids, list_course_student_ids, list_courses, list_users,
    replace_course_lectures, set_course_students, update_course,
)
from ...deps import require_roles, log_action
from ...schemas import (
    CourseCreate, CourseDetail, CourseOptionsOut, CourseOut, CourseUpdate,
    ManagedUserOut, MessageResponse,
)

router = APIRouter(prefix="/courses", tags=["courses"])


def _course_detail(course_id: int) -> dict:
    row = get_course(course_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    out = dict(row)
    out["student_ids"] = list_course_student_ids(course_id)
    out["lecture_ids"] = list_course_lecture_ids(course_id)
    return out


@router.get("", response_model=List[CourseOut])
def all_courses(user: dict = Depends(require_roles("student", "prof", "admin"))):
    return [
        dict(r)
        for r in list_courses(user_id=user["uid"], role=user["role"])
    ]


@router.get("/options", response_model=CourseOptionsOut)
def options(user: dict = Depends(require_roles("student", "prof", "admin"))):
    if user["role"] == "student":
        faculty_by_id: dict[int, str] = {}
        for course in list_courses(user_id=user["uid"], role=user["role"]):
            faculty_by_id.setdefault(
                int(course["faculty_id"]),
                str(course["faculty_username"]),
            )
        return CourseOptionsOut(
            students=[],
            faculty=[
                ManagedUserOut(
                    id=faculty_id,
                    username=username,
                    role="prof",
                    created_at="",
                )
                for faculty_id, username in faculty_by_id.items()
            ],
        )

    users = [dict(r) for r in list_users()]
    students = [u for u in users if u["role"] == "student"]
    if user["role"] == "admin":
        faculty = [u for u in users if u["role"] == "prof"]
    else:
        faculty = [u for u in users if u["id"] == user["uid"]]
    return CourseOptionsOut(
        students=[ManagedUserOut(**u) for u in students],
        faculty=[ManagedUserOut(**u) for u in faculty],
    )


@router.post("", response_model=CourseDetail, status_code=201)
def create(body: CourseCreate, request: Request,
           user: dict = Depends(require_roles("prof", "admin"))):
    faculty_id = body.faculty_id if user["role"] == "admin" else user["uid"]
    if faculty_id is None:
        faculty_id = user["uid"]
    try:
        course_id = create_course(name=body.name.strip(), faculty_id=faculty_id,
                                  description=body.description, visibility=body.visibility)
        if body.student_ids:
            set_course_students(course_id, body.student_ids)
        if body.lecture_ids:
            replace_course_lectures(
                course_id, body.lecture_ids,
                owner_user_id=None if user["role"] == "admin" else user["uid"],
            )
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "course exists")
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    log_action(request, user, "create_course", str(course_id))
    return _course_detail(course_id)


@router.get("/{course_id}", response_model=CourseDetail)
def detail(course_id: int, user: dict = Depends(require_roles("prof", "admin"))):
    row = get_course(course_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    if not can_manage_course(row, user_id=user["uid"], role=user["role"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
    return _course_detail(course_id)


@router.patch("/{course_id}", response_model=CourseDetail)
def update(course_id: int, body: CourseUpdate, request: Request,
           user: dict = Depends(require_roles("prof", "admin"))):
    row = get_course(course_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    if not can_manage_course(row, user_id=user["uid"], role=user["role"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")

    kwargs = {}
    fields = body.model_fields_set
    if "name" in fields and body.name is not None:
        kwargs["name"] = body.name.strip()
    if "description" in fields and body.description is not None:
        kwargs["description"] = body.description
    if "visibility" in fields and body.visibility is not None:
        kwargs["visibility"] = body.visibility
    if "faculty_id" in fields:
        if user["role"] != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
        kwargs["faculty_id"] = body.faculty_id

    try:
        if kwargs:
            updated = update_course(course_id, **kwargs)
            if not updated:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
        if "student_ids" in fields and body.student_ids is not None:
            set_course_students(course_id, body.student_ids)
        if "lecture_ids" in fields and body.lecture_ids is not None:
            replace_course_lectures(
                course_id, body.lecture_ids,
                owner_user_id=None if user["role"] == "admin" else user["uid"],
            )
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "course exists")
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    log_action(request, user, "update_course", str(course_id))
    return _course_detail(course_id)


@router.delete("/{course_id}", response_model=MessageResponse)
def remove(course_id: int, request: Request,
           user: dict = Depends(require_roles("prof", "admin"))):
    row = get_course(course_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    if not can_manage_course(row, user_id=user["uid"], role=user["role"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
    delete_course(course_id)
    log_action(request, user, "delete_course", str(course_id))
    return MessageResponse(ok=True)
