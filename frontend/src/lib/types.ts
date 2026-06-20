export type Role = 'student' | 'prof' | 'admin';

export interface User {
	uid: number;
	username: string;
	role: Role;
}

export interface TokenResponse {
	token: string;
	role: Role;
	username: string;
}

export interface LectureSummary {
	id: string;
	date: string;
	course_name: string | null;
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
	annotations: Annotation[];
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
