<script lang="ts">
	import { goto } from "$app/navigation";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiDelete, apiGet, apiPatch, apiPost } from "$lib/api/client";
	import type { Course, CourseDetail, CourseOptions, LectureSummary, User } from "$lib/types";
	import Card from "$lib/components/ui/Card.svelte";
	import Input from "$lib/components/ui/Input.svelte";
	import Select from "$lib/components/ui/Select.svelte";
	import Button from "$lib/components/ui/Button.svelte";
	import Modal from "$lib/components/ui/Modal.svelte";
	import {
		BookOpen,
		CircleNotch,
		FloppyDisk,
		MagnifyingGlass,
		Plus,
		Trash,
		UsersThree,
	} from "phosphor-svelte";

	const qc = useQueryClient();

	const me = createQuery(() => ({
		queryKey: ["me"],
		queryFn: () => apiGet<User>("/api/v1/me"),
	}));
	const courses = createQuery(() => ({
		queryKey: ["courses"],
		queryFn: () => apiGet<Course[]>("/api/v1/courses"),
	}));
	const options = createQuery(() => ({
		queryKey: ["course-options"],
		queryFn: () => apiGet<CourseOptions>("/api/v1/courses/options"),
	}));
	const lectures = createQuery(() => ({
		queryKey: ["lectures"],
		queryFn: () => apiGet<LectureSummary[]>("/api/v1/lectures"),
	}));

	$effect(() => {
		if (me.isError || courses.isError) goto("/");
		if (me.data?.role === "student") goto("/lectures");
	});

	let q = $state("");
	let facultyFilter = $state("");

	let createOpen = $state(false);
	let newName = $state("");
	let newDescription = $state("");
	let newFacultyId = $state("");
	let creating = $state(false);
	let createError = $state("");

	let activeCourse = $state<CourseDetail | null>(null);
	let editOpen = $state(false);
	let draftName = $state("");
	let draftDescription = $state("");
	let draftFacultyId = $state("");
	let draftStudentIds = $state<number[]>([]);
	let draftLectureIds = $state<string[]>([]);
	let loadingDetail = $state(false);
	let saving = $state(false);
	let editError = $state("");

	const isAdmin = $derived(me.data?.role === "admin");
	const facultyOptions = $derived(options.data?.faculty ?? []);
	const studentOptions = $derived(options.data?.students ?? []);
	const ownedLectures = $derived(
		(lectures.data ?? []).filter(
			(lecture) => isAdmin || lecture.owner_user_id === me.data?.uid,
		),
	);

	const filtered = $derived(
		(courses.data ?? []).filter((c) => {
			if (facultyFilter && String(c.faculty_id) !== facultyFilter) return false;
			if (!q.trim()) return true;
			const hay = `${c.name} ${c.faculty_username} ${c.description ?? ""}`.toLowerCase();
			return hay.includes(q.toLowerCase());
		}),
	);

	$effect(() => {
		const firstFaculty = facultyOptions[0];
		if (!newFacultyId && firstFaculty) newFacultyId = String(firstFaculty.id);
	});

	function openCreate() {
		createError = "";
		newName = "";
		newDescription = "";
		createOpen = true;
	}

	async function createCourse(e: SubmitEvent) {
		e.preventDefault();
		if (!newName.trim()) return;
		creating = true;
		createError = "";
		try {
			await apiPost<CourseDetail>("/api/v1/courses", {
				name: newName.trim(),
				description: newDescription.trim(),
				faculty_id: isAdmin && newFacultyId ? Number(newFacultyId) : undefined,
			});
			newName = "";
			newDescription = "";
			await qc.invalidateQueries({ queryKey: ["courses"] });
			createOpen = false;
		} catch (err) {
			createError = err instanceof Error ? err.message : "Create failed";
		} finally {
			creating = false;
		}
	}

	function hydrateDraft(course: CourseDetail) {
		activeCourse = course;
		draftName = course.name;
		draftDescription = course.description ?? "";
		draftFacultyId = String(course.faculty_id);
		draftStudentIds = [...course.student_ids];
		draftLectureIds = [...course.lecture_ids];
	}

	async function openCourse(courseId: number) {
		editError = "";
		loadingDetail = true;
		editOpen = true;
		try {
			const detail = await apiGet<CourseDetail>(`/api/v1/courses/${courseId}`);
			hydrateDraft(detail);
		} catch (err) {
			editError = err instanceof Error ? err.message : "Could not load course";
		} finally {
			loadingDetail = false;
		}
	}

	function toggleStudent(studentId: number) {
		draftStudentIds = draftStudentIds.includes(studentId)
			? draftStudentIds.filter((id) => id !== studentId)
			: [...draftStudentIds, studentId];
	}

	function toggleLecture(lectureId: string) {
		draftLectureIds = draftLectureIds.includes(lectureId)
			? draftLectureIds.filter((id) => id !== lectureId)
			: [...draftLectureIds, lectureId];
	}

	async function saveCourse() {
		if (!activeCourse) return;
		saving = true;
		editError = "";
		const assignableLectureIds = new Set(ownedLectures.map((lecture) => lecture.id));
		try {
			await apiPatch<CourseDetail>(`/api/v1/courses/${activeCourse.id}`, {
				name: draftName.trim(),
				description: draftDescription.trim(),
				faculty_id: isAdmin && draftFacultyId ? Number(draftFacultyId) : undefined,
				student_ids: draftStudentIds,
				lecture_ids: draftLectureIds.filter((id) => assignableLectureIds.has(id)),
			});
			await qc.invalidateQueries({ queryKey: ["courses"] });
			await qc.invalidateQueries({ queryKey: ["lectures"] });
			editOpen = false;
		} catch (err) {
			editError = err instanceof Error ? err.message : "Save failed";
		} finally {
			saving = false;
		}
	}

	async function removeCourse() {
		if (!activeCourse || !confirm("Delete this course?")) return;
		editError = "";
		try {
			await apiDelete(`/api/v1/courses/${activeCourse.id}`);
			editOpen = false;
			activeCourse = null;
			await qc.invalidateQueries({ queryKey: ["courses"] });
			await qc.invalidateQueries({ queryKey: ["lectures"] });
		} catch (err) {
			editError = err instanceof Error ? err.message : "Delete failed";
		}
	}
</script>

<div class="mb-4 flex flex-col gap-2 lg:flex-row lg:items-center">
	<div class="min-w-0 flex-1">
		<Input id="search" bind:value={q} icon={MagnifyingGlass} />
	</div>
	<Select
		bind:value={facultyFilter}
		placeholder="All faculty"
		class="w-48 shrink-0"
		options={facultyOptions.map((f) => ({
			value: String(f.id),
			label: f.username,
		}))}
	/>
	<Button variant="icon+text" type="button" onclick={openCreate}>
		{#snippet icon()}
			<Plus size={18} />
		{/snippet}
		Add course
	</Button>
</div>

{#if courses.isLoading}
	<p class="text-zinc-500 dark:text-zinc-400">Loading</p>
{:else if filtered.length > 0}
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each filtered as course (course.id)}
			<Card padding="default" class="group flex h-full flex-col">
				<button
					type="button"
					onclick={() => openCourse(course.id)}
					class="flex h-full w-full flex-col gap-3 text-left outline-none"
				>
					<div class="flex items-start justify-between gap-3">
						<div class="min-w-0">
							<h3 class="truncate text-base font-semibold text-primary transition-colors group-hover:text-secondary dark:text-gray-50">
								{course.name}
							</h3>
							<p class="mt-1 truncate text-xs text-gray-500 dark:text-gray-400">
								Prof. {course.faculty_username}
							</p>
						</div>
						<span class="shrink-0 rounded-lg bg-gray-100 px-2 py-1 text-xs font-semibold text-gray-600 dark:bg-gray-800 dark:text-gray-300">
							{course.lecture_count}
						</span>
					</div>

					{#if course.description}
						<p class="line-clamp-3 text-sm leading-6 text-gray-600 dark:text-gray-400">
							{course.description}
						</p>
					{/if}

					<div class="mt-auto flex items-center gap-3 pt-1 text-xs text-gray-500 dark:text-gray-400">
						<span class="flex items-center gap-1.5">
							<BookOpen size={14} weight="bold" />
							{course.lecture_count} lectures
						</span>
						<span class="flex items-center gap-1.5">
							<UsersThree size={14} weight="bold" />
							{course.student_count} students
						</span>
					</div>
				</button>
			</Card>
		{/each}
	</div>
{:else}
	<p class="text-sm text-gray-500 dark:text-gray-400">No courses found.</p>
{/if}

<Modal bind:open={createOpen} label="Add Course">
	<Card class="grid w-full max-w-lg shrink-0 gap-4 overflow-y-auto max-h-[90dvh]">
		<div class="flex items-center gap-2">
			<BookOpen size={18} class="text-secondary" />
			<h2 class="text-xl font-bold text-primary dark:text-gray-50">Add Course</h2>
		</div>

		<form onsubmit={createCourse} class="grid gap-3">
			<Input id="new-course-name" label="Name" bind:value={newName} required />
			<label class="grid gap-1.5 text-sm font-semibold text-primary dark:text-gray-100">
				<span>Description</span>
				<textarea
					bind:value={newDescription}
					rows="3"
					class="rounded-lg border border-gray-200 bg-white p-3 text-sm leading-6 outline-none focus:border-secondary/60 focus:ring-3 focus:ring-secondary/15 dark:border-gray-800 dark:bg-gray-950"
				></textarea>
			</label>
			{#if isAdmin}
				<label class="grid gap-1.5 text-sm font-semibold text-primary dark:text-gray-100">
					<span>Faculty</span>
					<Select
						bind:value={newFacultyId}
						options={facultyOptions.map((f) => ({
							value: String(f.id),
							label: f.username,
						}))}
					/>
				</label>
			{/if}

			{#if createError}
				<p class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400">
					{createError}
				</p>
			{/if}

			<Button variant="icon+text" type="submit" disabled={creating}>
				{#snippet icon()}
					{#if creating}
						<CircleNotch size={18} class="animate-spin" />
					{:else}
						<Plus size={18} />
					{/if}
				{/snippet}
				Create
			</Button>
		</form>
	</Card>
</Modal>

<Modal bind:open={editOpen} label="Edit Course">
	<Card class="grid w-full max-w-4xl shrink-0 gap-5 overflow-y-auto max-h-[90dvh]">
		{#if loadingDetail}
			<div class="flex h-64 items-center justify-center text-gray-500 dark:text-gray-400">
				<CircleNotch size={24} class="animate-spin" />
			</div>
		{:else if activeCourse}
			<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<h2 class="text-xl font-bold tracking-tight text-primary dark:text-gray-50">{activeCourse.name}</h2>
					<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
						Prof. {activeCourse.faculty_username}
					</p>
				</div>
				<div class="flex gap-2">
					<Button variant="icon+text" type="button" onclick={saveCourse} disabled={saving}>
						{#snippet icon()}
							{#if saving}
								<CircleNotch size={18} class="animate-spin" />
							{:else}
								<FloppyDisk size={18} />
							{/if}
						{/snippet}
						Save
					</Button>
					<Button variant="icon+text" type="button" danger onclick={removeCourse}>
						{#snippet icon()}
							<Trash size={18} />
						{/snippet}
						Delete
					</Button>
				</div>
			</div>

			{#if editError}
				<p class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400">
					{editError}
				</p>
			{/if}

			<div class="grid gap-3 md:grid-cols-2">
				<Input id="course-name" label="Name" bind:value={draftName} />
				{#if isAdmin}
					<label class="grid gap-1.5 text-sm font-semibold text-primary dark:text-gray-100">
						<span>Faculty</span>
						<Select
							bind:value={draftFacultyId}
							options={facultyOptions.map((f) => ({
								value: String(f.id),
								label: f.username,
							}))}
						/>
					</label>
				{/if}
				<label class="grid gap-1.5 text-sm font-semibold text-primary md:col-span-2 dark:text-gray-100">
					<span>Description</span>
					<textarea
						bind:value={draftDescription}
						rows="3"
						class="rounded-lg border border-gray-200 bg-white p-3 text-sm leading-6 outline-none focus:border-secondary/60 focus:ring-3 focus:ring-secondary/15 dark:border-gray-800 dark:bg-gray-950"
					></textarea>
				</label>
			</div>

			<div class="grid gap-4 lg:grid-cols-2">
				<div class="grid content-start gap-2">
					<div class="flex items-center gap-2 text-sm font-semibold text-primary dark:text-gray-100">
						<UsersThree size={16} />
						<span>Students</span>
					</div>
					<div class="grid max-h-[26rem] gap-2 overflow-auto pr-1">
						{#each studentOptions as student (student.id)}
							<label class="flex min-w-0 items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium dark:border-gray-800">
								<input
									type="checkbox"
									checked={draftStudentIds.includes(student.id)}
									onchange={() => toggleStudent(student.id)}
									class="size-4 rounded border-gray-300 text-secondary focus:ring-secondary"
								/>
								<span class="truncate">{student.username}</span>
							</label>
						{/each}
					</div>
				</div>

				<div class="grid content-start gap-2">
					<div class="flex items-center gap-2 text-sm font-semibold text-primary dark:text-gray-100">
						<BookOpen size={16} />
						<span>Lectures</span>
					</div>
					<div class="grid max-h-[26rem] gap-2 overflow-auto pr-1">
						{#each ownedLectures as lecture (lecture.id)}
							<label class="flex min-w-0 items-start gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium dark:border-gray-800">
								<input
									type="checkbox"
									checked={draftLectureIds.includes(lecture.id)}
									onchange={() => toggleLecture(lecture.id)}
									class="mt-0.5 size-4 rounded border-gray-300 text-secondary focus:ring-secondary"
								/>
								<span class="min-w-0">
									<span class="block truncate">{lecture.course_name ?? "Lecture"}</span>
									<span class="block truncate text-xs text-gray-500 dark:text-gray-400">
										{new Date(lecture.captured_at).toLocaleString()}
									</span>
								</span>
							</label>
						{/each}
					</div>
				</div>
			</div>
		{/if}
	</Card>
</Modal>
