<script lang="ts">
	import { goto } from "$app/navigation";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiPost, apiGet } from "$lib/api/client";
	import type {
		CourseDetail,
		CourseOptions,
		LectureSummary,
		User,
		Visibility,
	} from "$lib/types";
	import Input from "$lib/components/ui/Input.svelte";
	import Textarea from "$lib/components/ui/Textarea.svelte";
	import ComboBox from "$lib/components/ui/ComboBox.svelte";
	import Button from "$lib/components/ui/Button.svelte";
	import Assignments from "$lib/components/course/Assignments.svelte";
	import { ArrowLeft } from "phosphor-svelte";

	const qc = useQueryClient();

	const me = createQuery(() => ({
		queryKey: ["me"],
		queryFn: () => apiGet<User>("/api/v1/me"),
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
		if (me.isError) goto("/");
		if (me.data?.role === "student") goto("/lectures");
	});

	let newName = $state("");
	let newDescription = $state("");
	let newFacultyId = $state("");
	let newStudentIds = $state<number[]>([]);
	let newLectureIds = $state<string[]>([]);
	let newVisibility = $state<Visibility>("public");
	let creating = $state(false);
	let createError = $state("");

	const isAdmin = $derived(me.data?.role === "admin");
	const facultyOptions = $derived(options.data?.faculty ?? []);
	const ownedLectures = $derived(
		(lectures.data ?? []).filter(
			(lecture) => isAdmin || lecture.owner_user_id === me.data?.uid,
		),
	);

	$effect(() => {
		const firstFaculty = facultyOptions[0];
		if (!newFacultyId && firstFaculty)
			newFacultyId = String(firstFaculty.id);
	});

	async function createCourse(e: SubmitEvent) {
		e.preventDefault();
		if (!newName.trim()) return;
		creating = true;
		createError = "";
		const assignableLectureIds = new Set(
			ownedLectures.map((lecture) => lecture.id),
		);
		try {
			await apiPost<CourseDetail>("/api/v1/courses", {
				name: newName.trim(),
				description: newDescription.trim(),
				faculty_id:
					isAdmin && newFacultyId ? Number(newFacultyId) : undefined,
				visibility: newVisibility,
				student_ids: newStudentIds,
				lecture_ids: newLectureIds.filter((lid) =>
					assignableLectureIds.has(lid),
				),
			});
			await qc.invalidateQueries({ queryKey: ["courses"] });
			await qc.invalidateQueries({ queryKey: ["lectures"] });
			goto("/courses");
		} catch (err) {
			createError = err instanceof Error ? err.message : "Create failed";
		} finally {
			creating = false;
		}
	}
</script>

<form
	onsubmit={createCourse}
	class="relative flex min-h-[calc(100dvh-2rem)] flex-col"
>
	<!-- Sticky Header -->
	<header
		class="sticky top-0 z-10 flex items-center gap-4 border-b border-gray-200 bg-gray-50 pb-2 dark:border-gray-800 dark:bg-gray-950"
	>
		<Button
			variant="icon"
			ghost
			type="button"
			onclick={() => goto("/courses")}
			title="Back to courses"
		>
			{#snippet icon()}
				<ArrowLeft size={20} />
			{/snippet}
		</Button>
		<div>
			<h1
				class="text-2xl font-bold tracking-tight text-primary dark:text-gray-50"
			>
				Add Course
			</h1>
		</div>
	</header>

	<!-- Scrollable Middle -->
	<div class="flex flex-col flex-1 gap-6 py-4">
		<div class="grid gap-6 md:grid-cols-2">
			<Input
				id="new-course-name"
				label="Name"
				bind:value={newName}
				required
			/>
			{#if isAdmin}
				<label class="grid gap-1.5">
					<span class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">Faculty</span>
					<ComboBox
						bind:value={newFacultyId}
						placeholder=""
						options={facultyOptions.map((f) => ({
							value: String(f.id),
							label: f.username,
						}))}
					/>
				</label>
			{/if}
			<label class="grid gap-1.5">
				<span class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">Visibility</span>
				<ComboBox
					bind:value={newVisibility}
					options={[
						{ value: "public", label: "Public" },
						{ value: "private", label: "Private" },
					]}
				/>
			</label>
			<Textarea
				id="new-course-description"
				label="Description"
				bind:value={newDescription}
				rows={4}
				class="md:col-span-2"
			/>
		</div>

		<Assignments
			students={options.data?.students ?? []}
			lectures={ownedLectures}
			bind:studentIds={newStudentIds}
			bind:lectureIds={newLectureIds}
		/>

		{#if createError}
			<p
				class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400"
			>
				{createError}
			</p>
		{/if}
	</div>

	<!-- Sticky Footer -->
	<footer
		class="sticky bottom-20 z-10 flex items-center justify-between gap-4 border-t border-gray-200 bg-gray-50 pt-2 dark:border-gray-800 dark:bg-gray-950 md:bottom-0"
	>
		<div class="min-w-0 flex-1 pl-2">
			<span class="block truncate text-sm font-medium text-gray-500 dark:text-gray-400">
				{newName}
			</span>
		</div>
		<div class="flex shrink-0 items-center gap-3">
			<Button secondary type="button" onclick={() => goto("/courses")}
				>Cancel</Button
			>
			<Button type="submit" disabled={creating}>
				Save Course
			</Button>
		</div>
	</footer>
</form>
