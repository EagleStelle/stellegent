<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiGet, apiPatch } from "$lib/api/client";
	import type {
		Course,
		CourseOptions,
		LectureDetail,
		User,
		Visibility,
	} from "$lib/types";
	import { UsersThree, ArrowLeft } from "phosphor-svelte";
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
	let draftOwnerId = $state("");
	let draftStudentIds = $state<number[]>([]);

	// Seed the drafts once from the loaded lecture. Must not re-run on every
	// background refetch, or it would clobber the user's in-progress edits.
	let seeded = false;
	$effect(() => {
		if (seeded || !lecture.data) return;
		seeded = true;
		draftTitle = lecture.data.course_name ?? "";
		draftVisibility = lecture.data.visibility;
		draftCourseId = lecture.data.course_id
			? String(lecture.data.course_id)
			: "";
		draftOwnerId = lecture.data.owner_user_id
			? String(lecture.data.owner_user_id)
			: "";
		draftStudentIds = [...lecture.data.student_ids];
	});

	function toggleStudent(studentId: number) {
		draftStudentIds = draftStudentIds.includes(studentId)
			? draftStudentIds.filter((sid) => sid !== studentId)
			: [...draftStudentIds, studentId];
	}

	async function saveLecture(e?: SubmitEvent) {
		if (e) e.preventDefault();
		saving = true;
		editError = "";
		const body: Record<string, unknown> = {
			course_name: draftTitle.trim() || null,
			course_id: draftCourseId ? Number(draftCourseId) : null,
			visibility: draftVisibility,
			student_ids: draftStudentIds,
		};
		if (me.data?.role === "admin") {
			body.owner_user_id = draftOwnerId ? Number(draftOwnerId) : null;
		}
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
		class="relative flex min-h-[calc(100dvh-2rem)] flex-col"
	>
		<!-- Sticky Header -->
		<header
			class="sticky top-0 z-10 flex items-center gap-4 bg-gray-50 pb-2 dark:bg-gray-950 shadow-sm border-b border-gray-200 dark:border-gray-800"
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
		</header>

		<!-- Scrollable Middle -->
		<div class="flex flex-col flex-1 gap-6 py-4">
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
						options={[
							{ value: "public", label: "Public" },
							{ value: "private", label: "Private" },
						]}
					/>
				</label>
				{#if me.data?.role === "admin"}
					<label class="grid gap-1.5 md:col-span-2">
						<span class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">Owner</span>
						<ComboBox
							bind:value={draftOwnerId}
							placeholder="Unassigned"
							options={(options.data?.faculty ?? []).map((f) => ({
								value: String(f.id),
								label: f.username,
							}))}
						/>
					</label>
				{/if}
			</div>

			{#if options.data?.students?.length}
				<div class="grid content-start gap-3">
					<div
						class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400"
					>
						<UsersThree size={16} />
						<span>Direct students</span>
					</div>
					<div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
						{#each options.data.students as student (student.id)}
							<label
								class="flex min-w-0 items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm font-medium dark:border-gray-800 dark:bg-gray-950"
							>
								<input
									type="checkbox"
									checked={draftStudentIds.includes(
										student.id,
									)}
									onchange={() => toggleStudent(student.id)}
									class="size-4 rounded border-gray-300 text-secondary focus:ring-secondary"
								/>
								<span class="truncate">{student.username}</span
								>
							</label>
						{/each}
					</div>
				</div>
			{/if}

			{#if editError}
				<p
					class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400"
				>
					{editError}
				</p>
			{/if}
		</div>

		<!-- Sticky Footer -->
		<footer
			class="sticky bottom-20 z-10 flex items-center justify-between gap-4 border-t border-gray-200 bg-gray-50 pt-2 dark:border-gray-800 dark:bg-gray-950 md:bottom-0"
		>
			<div class="min-w-0 flex-1 pl-2">
				<span class="block truncate text-sm font-medium text-gray-500 dark:text-gray-400">
					{lecture.data.course_name ?? "Untitled"}
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
		</footer>
	</form>
{/if}
