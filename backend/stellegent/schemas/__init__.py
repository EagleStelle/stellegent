"""Pydantic request/response models for the v1 API."""
from __future__ import annotations
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

Role = Literal["prof", "student", "admin"]
EditableRole = Literal["prof", "student"]
Visibility = Literal["public", "private"]
ProcessingTaskKind = Literal["upload", "capture"]
ProcessingTaskStatus = Literal["queued", "running", "succeeded", "failed"]


# ---- auth ----
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginMfaRequest(BaseModel):
    code: str = Field(min_length=4, max_length=32)
    mfa_token: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    token: str
    role: Role
    username: str


class MfaChallengeResponse(BaseModel):
    mfa_required: Literal[True] = True
    mfa_token: Optional[str] = None
    message: str = "verification code required"


class UserOut(BaseModel):
    uid: int
    username: str
    role: Role
    email: Optional[str] = None
    auth_provider: str = "local"
    google_linked: bool = False
    two_factor_enabled: bool = False


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str


class MessageResponse(BaseModel):
    ok: bool = True
    message: Optional[str] = None
    # dev convenience: reset link/token surfaced when no SMTP is configured
    reset_token: Optional[str] = None
    verification_token: Optional[str] = None


class AccountOut(UserOut):
    email_verified: int = 0
    has_password: bool = True
    email_locked: bool = False


class AccountUpdateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    # Authenticator code, required when 2FA is enabled.
    code: Optional[str] = Field(default=None, max_length=32)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    # Authenticator code, required when 2FA is enabled.
    code: Optional[str] = Field(default=None, max_length=32)


class TotpSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_data_url: Optional[str] = None


class TotpVerifyRequest(BaseModel):
    code: str = Field(min_length=4, max_length=32)


class TotpEnableResponse(BaseModel):
    ok: bool = True
    recovery_codes: List[str] = []


class TotpDisableRequest(BaseModel):
    code: str = Field(min_length=4, max_length=32)
    current_password: Optional[str] = None


# ---- account management ----
class ManagedUserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: Role
    auth_provider: str = "local"
    email_verified: int = 0
    disabled: int = 0
    totp_enabled: int = 0
    created_at: str


class ManagedUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: EditableRole


class ManagedUserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=64)
    email: Optional[EmailStr] = None
    role: Optional[EditableRole] = None
    disabled: Optional[bool] = None


# ---- courses ----
class CourseOut(BaseModel):
    id: int
    name: str
    faculty_id: int
    faculty_username: str
    description: Optional[str] = None
    visibility: Visibility = "public"
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
    visibility: Visibility = "public"
    student_ids: List[int] = []
    lecture_ids: List[str] = []


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    faculty_id: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=500)
    visibility: Optional[Visibility] = None
    student_ids: Optional[List[int]] = None
    lecture_ids: Optional[List[str]] = None


class CourseOptionsOut(BaseModel):
    students: List[ManagedUserOut] = []
    faculty: List[ManagedUserOut] = []


# ---- lectures ----
class LectureSummary(BaseModel):
    id: str
    date: str
    title: Optional[str] = None
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


class ErrorMetric(BaseModel):
    errors: int
    substitutions: int
    insertions: int
    deletions: int
    reference_length: int
    hypothesis_length: int
    error_rate: float
    recognition_rate: float


class TranscriptEvaluation(BaseModel):
    cer: ErrorMetric
    wer: ErrorMetric


class RougeMetric(BaseModel):
    precision: float
    recall: float
    fmeasure: float


class SummaryEvaluation(BaseModel):
    rouge1: RougeMetric
    rouge2: RougeMetric
    rougeL: RougeMetric


class LectureEvaluation(BaseModel):
    raw_ocr: Optional[TranscriptEvaluation] = None
    corrected: Optional[TranscriptEvaluation] = None
    summary: Optional[SummaryEvaluation] = None


class ProcessingStageTiming(BaseModel):
    key: str
    label: str
    duration_ms: float
    triggered: bool = True


class ProcessingTiming(BaseModel):
    stages: List[ProcessingStageTiming] = []
    total_ms: float = 0.0
    mean_ms: float = 0.0
    median_ms: float = 0.0


class LectureDetail(BaseModel):
    id: str
    date: str
    title: Optional[str] = None
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
    reference_transcript: Optional[str] = None
    reference_summary: Optional[str] = None
    evaluation: LectureEvaluation = Field(default_factory=LectureEvaluation)
    processing_timing: Optional[ProcessingTiming] = None
    tags: Optional[str] = None
    student_ids: List[int] = []
    annotations: List[AnnotationOut] = []


class LectureUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=160)
    course_name: Optional[str] = Field(default=None, max_length=160)
    course_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    visibility: Optional[Visibility] = None
    corrected_text: Optional[str] = None
    summary: Optional[str] = None
    reference_transcript: Optional[str] = None
    reference_summary: Optional[str] = None
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
    processing_timing: Optional[ProcessingTiming] = None


class ProcessingTaskOut(BaseModel):
    id: str
    kind: ProcessingTaskKind
    status: ProcessingTaskStatus
    created_by_user_id: Optional[int] = None
    created_by_username: Optional[str] = None
    course_name: Optional[str] = None
    course_id: Optional[int] = None
    filename: Optional[str] = None
    lecture_id: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0
    queue_position: Optional[int] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_at: str


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
