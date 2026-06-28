<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiDelete, apiGet, apiPatch } from "$lib/api/client";
	import type {
		CourseDetail,
		CourseOptions,
		LectureSummary,
		User,
		Visibility,
	} from "$lib/types";
	import Input from "$lib/components/ui/Input.svelte";
	import ComboBox from "$lib/components/ui/ComboBox.svelte";
	import Button from "$lib/components/ui/Button.svelte";
	import Assignments from "$lib/components/course/Assignments.svelte";
	import { ArrowLeft } from "phosphor-svelte";

	const qc = useQueryClient();
	const id = $derived(page.params.id);

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
	const course = createQuery(() => ({
		queryKey: ["course", id],
		queryFn: () => apiGet<CourseDetail>(`/api/v1/courses/${id}`),
	}));

	$effect(() => {
		if (me.isError) goto("/");
		if (me.data?.role === "student") goto("/lectures");
	});

	let draftName = $state("");
	let draftDescription = $state("");
	let draftFacultyId = $state("");
	let draftVisibility = $state<Visibility>("public");
	let draftStudentIds = $state<number[]>([]);
	let draftLectureIds = $state<string[]>([]);
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

	// Seed the drafts once per course. Background refetches should not erase
	// in-progress assignment edits before the user saves.
	let seededCourseId = "";
	$effect(() => {
		if (!course.data) return;
		if (String(course.data.id) !== id || seededCourseId === id) return;
		seededCourseId = id;
		draftName = course.data.name;
		draftDescription = course.data.description ?? "";
		draftFacultyId = String(course.data.faculty_id);
		draftVisibility = course.data.visibility;
		draftStudentIds = [...course.data.student_ids];
		draftLectureIds = [...course.data.lecture_ids];
	});

	async function saveCourse(e?: SubmitEvent) {
		if (e) e.preventDefault();
		if (!course.data) return;
		saving = true;
		editError = "";
		const assignableLectureIds = new Set(
			ownedLectures.map((lecture) => lecture.id),
		);
		try {
			await apiPatch<CourseDetail>(`/api/v1/courses/${course.data.id}`, {
				name: draftName.trim(),
				description: draftDescription.trim(),
				faculty_id:
					isAdmin && draftFacultyId
						? Number(draftFacultyId)
						: undefined,
				visibility: draftVisibility,
				student_ids: draftStudentIds,
				lecture_ids: draftLectureIds.filter((lid) =>
					assignableLectureIds.has(lid),
				),
			});
			await qc.invalidateQueries({ queryKey: ["courses"] });
			await qc.invalidateQueries({ queryKey: ["lectures"] });
			await qc.invalidateQueries({ queryKey: ["course", id] });
			goto("/courses");
		} catch (err) {
			editError = err instanceof Error ? err.message : "Save failed";
		} finally {
			saving = false;
		}
	}

	async function removeCourse() {
		if (!course.data) return;
		if (!confirm("Delete this course?")) return;
		editError = "";
		try {
			await apiDelete(`/api/v1/courses/${course.data.id}`);
			await qc.invalidateQueries({ queryKey: ["courses"] });
			await qc.invalidateQueries({ queryKey: ["lectures"] });
			goto("/courses");
		} catch (err) {
			editError = err instanceof Error ? err.message : "Delete failed";
		}
	}
</script>

{#if course.isLoading}
	<div
		class="h-[calc(100dvh-2rem)] w-full animate-pulse rounded-2xl bg-gray-200 dark:bg-gray-800"
	></div>
{:else if course.data}
	<form
		onsubmit={saveCourse}
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
						Edit Course
					</h1>
				</div>
				<Button
					variant="text"
					type="button"
					danger
					class="ml-auto"
					onclick={removeCourse}
					title="Delete course"
				>
					Delete
				</Button>
			</div>
		</header>

		<div class="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto pr-2">
			<div class="grid gap-6 md:grid-cols-2">
				<div class="md:col-span-2">
					<Input id="course-name" label="Name" bind:value={draftName} />
				</div>
				{#if isAdmin}
					<label class="grid gap-1.5 md:col-span-2">
						<span class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">Faculty</span>
						<ComboBox
							bind:value={draftFacultyId}
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
						bind:value={draftVisibility}
						options={[
							{ value: "public", label: "Public" },
							{ value: "private", label: "Private" },
						]}
					/>
				</label>
				<Input
					id="course-description"
					label="Description"
					bind:value={draftDescription}
				/>
			</div>

			<Assignments
				students={studentOptions}
				lectures={ownedLectures}
				bind:studentIds={draftStudentIds}
				bind:lectureIds={draftLectureIds}
			/>

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
						{draftName}
					</span>
				</div>
				<div class="flex shrink-0 items-center gap-3">
					<Button secondary type="button" onclick={() => goto("/courses")}
						>Cancel</Button
					>
					<Button type="submit" disabled={saving}>
						Save Course
					</Button>
				</div>
			</div>
		</footer>
	</form>
{/if}
