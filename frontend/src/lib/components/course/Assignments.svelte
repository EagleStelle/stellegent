<script lang="ts">
	import { Plus } from "phosphor-svelte";
	import type { LectureSummary, ManagedUser } from "$lib/types";
	import Button from "$lib/components/ui/Button.svelte";
	import ComboBox from "$lib/components/ui/ComboBox.svelte";

	type Props = {
		students?: ManagedUser[];
		lectures?: LectureSummary[];
		studentIds?: number[];
		lectureIds?: string[];
	};

	let {
		students = [],
		lectures = [],
		studentIds = $bindable(),
		lectureIds = $bindable(),
	}: Props = $props();

	let pendingStudentId = $state("");
	let pendingLectureId = $state("");

	const selectedStudentSet = $derived.by(
		(): Set<number> => new Set(studentIds ?? []),
	);
	const selectedLectureSet = $derived.by(
		(): Set<string> => new Set(lectureIds ?? []),
	);

	const availableStudents = $derived.by(
		(): ManagedUser[] =>
			students.filter(
				(student: ManagedUser) => !selectedStudentSet.has(student.id),
			),
	);
	const availableLectures = $derived.by(
		(): LectureSummary[] =>
			lectures.filter(
				(lecture: LectureSummary) =>
					!selectedLectureSet.has(lecture.id),
			),
	);

	const selectedStudents = $derived.by(
		(): ManagedUser[] =>
			(studentIds ?? [])
				.map((studentId: number) =>
					students.find(
						(student: ManagedUser) => student.id === studentId,
					),
				)
			.filter((student): student is ManagedUser => Boolean(student)),
	);
	const selectedLectures = $derived.by(
		(): LectureSummary[] =>
			(lectureIds ?? [])
				.map((lectureId: string) =>
					lectures.find(
						(lecture: LectureSummary) =>
							lecture.id === lectureId,
					),
				)
			.filter((lecture): lecture is LectureSummary => Boolean(lecture)),
	);

	const pendingStudent = $derived.by(
		(): ManagedUser | undefined =>
			availableStudents.find(
				(student: ManagedUser) =>
					String(student.id) === pendingStudentId,
			),
	);
	const pendingLecture = $derived.by(
		(): LectureSummary | undefined =>
			availableLectures.find(
				(lecture: LectureSummary) =>
					lecture.id === pendingLectureId,
			),
	);
	const canAddStudent = $derived(Boolean(pendingStudent));
	const canAddLecture = $derived(Boolean(pendingLecture));

	function studentLabel(student: ManagedUser) {
		return `${student.username} - ${student.email ?? "No email"}`;
	}

	const studentChoices = $derived(
		availableStudents.map((student: ManagedUser) => ({
			value: String(student.id),
			label: studentLabel(student),
		})),
	);
	const lectureChoices = $derived(
		availableLectures.map((lecture: LectureSummary) => ({
			value: lecture.id,
			label: lectureLabel(lecture),
		})),
	);

	function lectureTitle(lecture: LectureSummary) {
		return lecture.course_name ?? lecture.course_title ?? "Untitled lecture";
	}

	function formatLectureDate(lecture: LectureSummary) {
		const capturedAt = new Date(lecture.captured_at);
		if (Number.isNaN(capturedAt.getTime())) return lecture.date;
		return capturedAt.toLocaleString();
	}

	function lectureLabel(lecture: LectureSummary) {
		return `${lectureTitle(lecture)} - ${formatLectureDate(lecture)}`;
	}

	function addStudent() {
		if (!pendingStudent) return;
		studentIds = [...(studentIds ?? []), pendingStudent.id];
		pendingStudentId = "";
	}

	function addLecture() {
		if (!pendingLecture) return;
		lectureIds = [...(lectureIds ?? []), pendingLecture.id];
		pendingLectureId = "";
	}

	function removeStudent(studentId: number) {
		studentIds = (studentIds ?? []).filter(
			(id: number) => id !== studentId,
		);
	}

	function removeLecture(lectureId: string) {
		lectureIds = (lectureIds ?? []).filter(
			(id: string) => id !== lectureId,
		);
	}
</script>

<div class="grid gap-8 lg:grid-cols-2">
	<section class="grid content-start gap-3">
		<div class="flex items-center justify-between gap-3">
			<h2
				class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400"
			>
				Students
			</h2>
			<span class="text-xs font-medium text-gray-500 dark:text-gray-400">
				{selectedStudents.length}
			</span>
		</div>

		<div class="flex items-center gap-2">
			<ComboBox
				bind:value={pendingStudentId}
				placeholder="Search students…"
				options={studentChoices}
				class="flex-1"
			/>
			<Button
				variant="icon"
				type="button"
				onclick={addStudent}
				disabled={!canAddStudent}
				title="Add student"
			>
				{#snippet icon()}
					<Plus size={19} weight="bold" />
				{/snippet}
			</Button>
		</div>

		<div class="grid max-h-128 gap-2 overflow-auto pr-1">
			{#each selectedStudents as student (student.id)}
				<div
					class="flex min-w-0 items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2.5 dark:border-gray-800 dark:bg-gray-950"
				>
					<div class="min-w-0">
						<p
							class="truncate text-sm font-semibold text-primary dark:text-gray-50"
						>
							{student.username}
						</p>
						<p class="truncate text-xs text-gray-500 dark:text-gray-400">
							{student.email ?? "No email on file"}
						</p>
					</div>
					<Button
						ghost
						danger
						type="button"
						onclick={() => removeStudent(student.id)}
					>
						Delete
					</Button>
				</div>
			{/each}
		</div>
	</section>

	<section class="grid content-start gap-3">
		<div class="flex items-center justify-between gap-3">
			<h2
				class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400"
			>
				Lectures
			</h2>
			<span class="text-xs font-medium text-gray-500 dark:text-gray-400">
				{selectedLectures.length}
			</span>
		</div>

		<div class="flex items-center gap-2">
			<ComboBox
				bind:value={pendingLectureId}
				placeholder="Search lectures…"
				options={lectureChoices}
				class="flex-1"
			/>
			<Button
				variant="icon"
				type="button"
				onclick={addLecture}
				disabled={!canAddLecture}
				title="Add lecture"
			>
				{#snippet icon()}
					<Plus size={19} weight="bold" />
				{/snippet}
			</Button>
		</div>

		<div class="grid max-h-128 gap-2 overflow-auto pr-1">
			{#each selectedLectures as lecture (lecture.id)}
				<div
					class="flex min-w-0 items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2.5 dark:border-gray-800 dark:bg-gray-950"
				>
					<div class="min-w-0">
						<p
							class="truncate text-sm font-semibold text-primary dark:text-gray-50"
						>
							{lectureTitle(lecture)}
						</p>
						<p class="truncate text-xs text-gray-500 dark:text-gray-400">
							{formatLectureDate(lecture)}
						</p>
					</div>
					<Button
						ghost
						danger
						type="button"
						onclick={() => removeLecture(lecture.id)}
					>
						Delete
					</Button>
				</div>
			{/each}
		</div>
	</section>
</div>
