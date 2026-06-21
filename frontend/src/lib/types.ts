export type Role = 'student' | 'prof' | 'admin';
export type EditableRole = 'student' | 'prof';
export type Visibility = 'public' | 'private';

export interface User {
	uid: number;
	username: string;
	role: Role;
	email?: string | null;
	auth_provider?: string;
	google_linked?: boolean;
	two_factor_enabled?: boolean;
}

export interface TokenResponse {
	token: string;
	role: Role;
	username: string;
}

export interface MfaChallenge {
	mfa_required: true;
	mfa_token?: string | null;
	message: string;
}

export interface Account extends User {
	email: string | null;
	auth_provider: string;
	email_verified: number;
	google_linked: boolean;
	two_factor_enabled: boolean;
	has_password: boolean;
	email_locked: boolean;
}

export interface TotpSetup {
	secret: string;
	otpauth_uri: string;
	qr_data_url?: string | null;
}

export interface TotpEnableResponse {
	ok: boolean;
	recovery_codes: string[];
}

export interface MessageResponse {
	ok: boolean;
	message?: string | null;
	reset_token?: string | null;
	verification_token?: string | null;
}

export interface LectureSummary {
	id: string;
	date: string;
	title: string | null;
	course_name: string | null;
	course_id: number | null;
	course_title: string | null;
	owner_user_id: number | null;
	owner_username: string | null;
	visibility: Visibility;
	captured_at: string;
	summary: string | null;
	tags: string | null;
}

export interface Annotation {
	id: number;
	lecture_id: string;
	user_id: number | null;
	username: string | null;
	note_text: string;
	created_at: string;
}

export interface LectureDetail extends LectureSummary {
	raw_ocr_text: string | null;
	corrected_text: string | null;
	manifest: Record<string, unknown> | null;
	student_ids: number[];
	annotations: Annotation[];
}

export interface ManagedUser {
	id: number;
	username: string;
	email: string | null;
	role: Role;
	auth_provider: string;
	email_verified: number;
	disabled: number;
	created_at: string;
}

export interface Course {
	id: number;
	name: string;
	faculty_id: number;
	faculty_username: string;
	description: string | null;
	visibility: Visibility;
	student_count: number;
	lecture_count: number;
	created_at: string;
	updated_at: string;
}

export interface CourseDetail extends Course {
	student_ids: number[];
	lecture_ids: string[];
}

export interface CourseOptions {
	students: ManagedUser[];
	faculty: ManagedUser[];
}

export interface Guidance {
	messages: string[];
	ready: boolean;
	sharpness: number;
	distance_m: number | null;
	skew_deg: number | null;
	coverage: number | null;
	has_board: boolean;
}

export interface PipelineResult {
	lecture_id: string;
	dir: string;
	engine: string;
	raw_text: string;
	corrected_text: string;
	summary: string;
	tags: string[];
}

export interface CapturePayload {
	course?: string | null;
	course_id?: number | null;
	visibility?: Visibility;
}
