"""Pydantic request/response models for the v1 API."""
from __future__ import annotations
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ---- auth ----
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    token: str
    role: str
    username: str


class UserOut(BaseModel):
    uid: int
    username: str
    role: str


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


# ---- lectures ----
class LectureSummary(BaseModel):
    id: str
    date: str
    course_name: Optional[str] = None
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
    captured_at: str
    raw_ocr_text: Optional[str] = None
    corrected_text: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[str] = None
    manifest: Optional[dict] = None
    annotations: List[AnnotationOut] = []


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
