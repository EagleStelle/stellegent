<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiGet, apiPatch, apiDelete } from "$lib/api/client";
	import type {
		Course,
		CourseOptions,
		LectureDetail,
		User,
		ManagedUser,
		Visibility,
	} from "$lib/types";
	import { Plus, ArrowLeft } from "phosphor-svelte";
	import Button from "$lib/components/ui/Button.svelte";
	import Input from "$lib/components/ui/Input.svelte";
	import ComboBox from "$lib/components/ui/ComboBox.svelte";

	const qc = useQueryClient();
	const id = $derived(page.params.id);

	const me = createQuery(() => ({
		queryKey: ["me"],
		queryFn: () => apiGet<User>("/api/v1/me"),
	}));
	const lecture = createQuery(() => ({
		queryKey: ["lecture", id],
		queryFn: () => apiGet<LectureDetail>(`/api/v1/lectures/${id}`),
	}));

	const canTeach = $derived(
		me.data?.role === "prof" || me.data?.role === "admin",
	);
	const courses = createQuery(() => ({
		queryKey: ["courses"],
		queryFn: () => apiGet<Course[]>("/api/v1/courses"),
		enabled: canTeach,
	}));
	const options = createQuery(() => ({
		queryKey: ["course-options"],
		queryFn: () => apiGet<CourseOptions>("/api/v1/courses/options"),
		enabled: canTeach,
	}));

	let saving = $state(false);
	let editError = $state("");
	let draftTitle = $state("");
	let draftVisibility = $state<Visibility>("public");
	let draftCourseId = $state("");
	let draftStudentIds = $state<number[]>([]);
	
	let pendingStudentId = $state("");

	const selectedStudentSet = $derived.by(
		(): Set<number> => new Set(draftStudentIds ?? []),
	);

	const availableStudents = $derived.by(
		(): ManagedUser[] =>
			(options.data?.students ?? []).filter(
				(student) => !selectedStudentSet.has(student.id),
			),
	);

	const selectedStudents = $derived.by(
		(): ManagedUser[] =>
			(draftStudentIds ?? [])
				.map((studentId: number) =>
					(options.data?.students ?? []).find(
						(student) => student.id === studentId,
					),
				)
			.filter((student): student is ManagedUser => Boolean(student)),
	);

	const pendingStudent = $derived.by(
		(): ManagedUser | undefined =>
			availableStudents.find(
				(student) =>
					String(student.id) === pendingStudentId,
			),
	);
	const canAddStudent = $derived(Boolean(pendingStudent));

	function studentLabel(student: ManagedUser) {
		return `${student.username} - ${student.email ?? "No email"}`;
	}

	const studentChoices = $derived(
		availableStudents.map((student) => ({
			value: String(student.id),
			label: studentLabel(student),
		})),
	);

	function addStudent() {
		if (!pendingStudent) return;
		draftStudentIds = [...(draftStudentIds ?? []), pendingStudent.id];
		pendingStudentId = "";
	}

	function removeStudent(studentId: number) {
		draftStudentIds = (draftStudentIds ?? []).filter(
			(id: number) => id !== studentId,
		);
	}

	// Seed the drafts once from the loaded lecture. Must not re-run on every
	// background refetch, or it would clobber the user's in-progress edits.
	let seeded = false;
	$effect(() => {
		if (seeded || !lecture.data) return;
		seeded = true;
		draftTitle = lecture.data.title ?? lecture.data.course_name ?? "";
		draftVisibility = lecture.data.visibility;
		draftCourseId = lecture.data.course_id
			? String(lecture.data.course_id)
			: "";
		draftStudentIds = [...lecture.data.student_ids];
	});

	// A lecture under a course always inherits the course's visibility; lock the
	// visibility picker while a course is selected. Mirrors /lectures/add and /live.
	const selectedCourse = $derived(
		(courses.data ?? []).find((c) => String(c.id) === draftCourseId) ?? null,
	);
	$effect(() => {
		if (selectedCourse) draftVisibility = selectedCourse.visibility;
	});

	async function removeLecture() {
		if (!confirm("Delete this lecture?")) return;
		editError = "";
		try {
			await apiDelete(`/api/v1/lectures/${id}`);
			await qc.invalidateQueries({ queryKey: ["lectures"] });
			goto("/lectures");
		} catch (err) {
			editError = err instanceof Error ? err.message : "Delete failed";
		}
	}

	async function saveLecture(e?: SubmitEvent) {
		if (e) e.preventDefault();
		saving = true;
		editError = "";
		const body: Record<string, unknown> = {
			title: draftTitle.trim() || null,
			course_id: draftCourseId ? Number(draftCourseId) : null,
			visibility: draftVisibility,
			student_ids: draftStudentIds,
		};
		try {
			await apiPatch<LectureDetail>(`/api/v1/lectures/${id}`, body);
			await qc.invalidateQueries({ queryKey: ["lecture", id] });
			await qc.invalidateQueries({ queryKey: ["lectures"] });
			goto(`/lectures/${id}`);
		} catch (err) {
			editError = err instanceof Error ? err.message : "Save failed";
		} finally {
			saving = false;
		}
	}
</script>

{#if lecture.isLoading}
	<div
		class="h-[calc(100dvh-2rem)] w-full animate-pulse rounded-2xl bg-gray-200 dark:bg-gray-800"
	></div>
{:else if lecture.data}
	<form
		onsubmit={saveLecture}
		class="relative flex h-[calc(100dvh-7rem)] max-h-[calc(100dvh-7rem)] flex-col gap-4 md:h-[calc(100dvh-2rem)] md:max-h-[calc(100dvh-2rem)]"
	>
		<header class="shrink-0">
			<div
				class="flex items-center gap-4 border-b border-gray-200 pb-2 dark:border-gray-800"
			>
				<Button
					variant="icon"
					ghost
					type="button"
					onclick={() => goto(`/lectures/${id}`)}
					title="Back to lecture"
				>
					{#snippet icon()}
						<ArrowLeft size={20} />
					{/snippet}
				</Button>
				<div>
					<h1
						class="text-2xl font-bold tracking-tight text-primary dark:text-gray-50"
					>
						Edit Lecture
					</h1>
				</div>
				<Button
					variant="text"
					type="button"
					danger
					class="ml-auto"
					onclick={removeLecture}
					title="Delete lecture"
				>
					Delete
				</Button>
			</div>
		</header>

		<div class="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto pr-2">
			<div class="grid gap-6 md:grid-cols-2">
				<div class="md:col-span-2">
					<Input
						id="lecture-title"
						label="Title"
						bind:value={draftTitle}
					/>
				</div>
				<label class="grid gap-1.5">
					<span class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">Course</span>
					<ComboBox
						bind:value={draftCourseId}
						placeholder="No course"
						options={(courses.data ?? []).map((c) => ({
							value: String(c.id),
							label: c.name,
						}))}
					/>
				</label>
				<label class="grid gap-1.5">
					<span class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">Visibility</span>
					<ComboBox
						bind:value={draftVisibility}
						disabled={selectedCourse !== null}
						options={[
							{ value: "public", label: "Public" },
							{ value: "private", label: "Private" },
						]}
					/>
				</label>
			</div>

			{#if draftVisibility === "private" && options.data?.students?.length}
				<section class="grid content-start gap-3">
					<div class="flex items-center justify-between gap-3">
						<h2 class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">
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
			{/if}

			{#if editError}
				<p
					class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400"
				>
					{editError}
				</p>
			{/if}
		</div>

		<footer class="shrink-0">
			<div
				class="flex items-center justify-between gap-4 border-t border-gray-200 pt-2 dark:border-gray-800"
			>
				<div class="min-w-0 flex-1 pl-2">
					<span class="block truncate text-sm font-medium text-gray-500 dark:text-gray-400">
						{lecture.data.title ?? lecture.data.course_name ?? "Untitled"}
					</span>
				</div>
				<div class="flex shrink-0 items-center gap-3">
					<Button secondary type="button" onclick={() => goto(`/lectures/${id}`)}
						>Cancel</Button
					>
					<Button type="submit" disabled={saving}>
						Save
					</Button>
				</div>
			</div>
		</footer>
	</form>
{/if}
