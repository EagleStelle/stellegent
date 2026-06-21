"""Pydantic request/response models for the v1 API."""
from __future__ import annotations
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

Role = Literal["prof", "student", "admin"]
EditableRole = Literal["prof", "student"]
Visibility = Literal["public", "private"]


# ---- auth ----
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    token: str
    role: Role
    username: str


class UserOut(BaseModel):
    uid: int
    username: str
    role: Role
    email: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    ok: bool = True
    message: Optional[str] = None
    # dev convenience: reset link/token surfaced when no SMTP is configured
    reset_token: Optional[str] = None


# ---- account management ----
class ManagedUserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: Role
    auth_provider: str = "local"
    email_verified: int = 0
    disabled: int = 0
    created_at: str


class ManagedUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: EditableRole


class ManagedUserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=64)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    role: Optional[EditableRole] = None
    disabled: Optional[bool] = None


# ---- courses ----
class CourseOut(BaseModel):
    id: int
    name: str
    faculty_id: int
    faculty_username: str
    description: Optional[str] = None
    student_count: int = 0
    lecture_count: int = 0
    created_at: str
    updated_at: str


class CourseDetail(CourseOut):
    student_ids: List[int] = []
    lecture_ids: List[str] = []


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    faculty_id: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=500)
    student_ids: List[int] = []
    lecture_ids: List[str] = []


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    faculty_id: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=500)
    student_ids: Optional[List[int]] = None
    lecture_ids: Optional[List[str]] = None


class CourseOptionsOut(BaseModel):
    students: List[ManagedUserOut] = []
    faculty: List[ManagedUserOut] = []


# ---- lectures ----
class LectureSummary(BaseModel):
    id: str
    date: str
    course_name: Optional[str] = None
    course_id: Optional[int] = None
    course_title: Optional[str] = None
    owner_user_id: Optional[int] = None
    owner_username: Optional[str] = None
    visibility: Visibility = "public"
    captured_at: str
    summary: Optional[str] = None
    tags: Optional[str] = None


class AnnotationOut(BaseModel):
    id: int
    lecture_id: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    note_text: str
    created_at: str


class AnnotateRequest(BaseModel):
    note: str = Field(min_length=1)


class LectureDetail(BaseModel):
    id: str
    date: str
    course_name: Optional[str] = None
    course_id: Optional[int] = None
    course_title: Optional[str] = None
    owner_user_id: Optional[int] = None
    owner_username: Optional[str] = None
    visibility: Visibility = "public"
    captured_at: str
    raw_ocr_text: Optional[str] = None
    corrected_text: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[str] = None
    manifest: Optional[dict] = None
    student_ids: List[int] = []
    annotations: List[AnnotationOut] = []


class LectureUpdateRequest(BaseModel):
    course_name: Optional[str] = Field(default=None, max_length=160)
    course_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    visibility: Optional[Visibility] = None
    corrected_text: Optional[str] = None
    summary: Optional[str] = None
    student_ids: Optional[List[int]] = None


# ---- pipeline / capture ----
class PipelineResult(BaseModel):
    lecture_id: str
    dir: str
    engine: str
    raw_text: str
    corrected_text: str
    summary: str
    tags: List[str] = []


class GuidanceOut(BaseModel):
    messages: List[str] = []
    ready: bool = False
    sharpness: float = 0.0
    distance_m: Optional[float] = None
    skew_deg: Optional[float] = None
    coverage: Optional[float] = None
    has_board: bool = False


class CaptureRequest(BaseModel):
    course: Optional[str] = None
    course_id: Optional[int] = None
    visibility: Visibility = "public"
