<script lang="ts">
	import { goto } from "$app/navigation";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiDelete, apiGet } from "$lib/api/client";
	import type { Course, CourseOptions, User } from "$lib/types";
	import Card from "$lib/components/ui/Card.svelte";
	import Input from "$lib/components/ui/Input.svelte";
	import ComboBox from "$lib/components/ui/ComboBox.svelte";
	import Button from "$lib/components/ui/Button.svelte";
	import {
		BookOpen,
		CircleNotch,
		FloppyDisk,
		MagnifyingGlass,
		PencilSimple,
		Plus,
		Trash,
		UserCircle,
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


	$effect(() => {
		if (me.isError || courses.isError) goto("/");
	});

	let q = $state("");
	let facultyFilter = $state("");

	const isAdmin = $derived(me.data?.role === "admin");
	const canTeach = $derived(
		me.data?.role === "prof" || me.data?.role === "admin",
	);
	const facultyOptions = $derived(options.data?.faculty ?? []);

	const filtered = $derived(
		(courses.data ?? []).filter((c) => {
			if (facultyFilter && String(c.faculty_id) !== facultyFilter) return false;
			if (!q.trim()) return true;
			const hay = `${c.name} ${c.faculty_username} ${c.description ?? ""}`.toLowerCase();
			return hay.includes(q.toLowerCase());
		}),
	);

	function openCreate() {
		goto("/courses/add");
	}

	function openCourseLectures(courseId: number) {
		goto(`/lectures?courseId=${courseId}`);
	}

	function editCourse(event: MouseEvent, courseId: number) {
		event.stopPropagation();
		goto(`/courses/${courseId}/edit`);
	}

	async function deleteCourseById(courseId: number) {
		if (!confirm("Delete this course?")) return;
		try {
			await apiDelete(`/api/v1/courses/${courseId}`);
			await qc.invalidateQueries({ queryKey: ["courses"] });
			await qc.invalidateQueries({ queryKey: ["lectures"] });
		} catch (err) {
			alert(err instanceof Error ? err.message : "Delete failed");
		}
	}

	async function deleteCourse(event: MouseEvent, courseId: number) {
		event.stopPropagation();
		await deleteCourseById(courseId);
	}
</script>

<div class="mb-4 flex flex-col gap-2 lg:flex-row lg:items-center">
	<div class="min-w-0 flex-1">
		<Input id="search" bind:value={q} icon={MagnifyingGlass} />
	</div>
	<div class="w-full lg:w-56">
		<ComboBox
			bind:value={facultyFilter}
			placeholder="All faculty"
			class="w-full"
			options={facultyOptions.map((f) => ({
				value: String(f.id),
				label: f.username,
			}))}
		/>
	</div>
	{#if canTeach}
		<Button variant="icon+text" type="button" onclick={openCreate}>
			{#snippet icon()}
				<Plus size={18} />
			{/snippet}
			Add course
		</Button>
	{/if}
</div>

{#if courses.isLoading}
	<p class="text-zinc-500 dark:text-zinc-400">Loading</p>
{:else if filtered.length > 0}
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each filtered as course (course.id)}
			<Card
				padding="default"
				as="div"
				onclick={() => openCourseLectures(course.id)}
				aria-label={`View lectures for ${course.name}`}
				class="group flex h-full w-full flex-col gap-3 outline-none"
			>
				<div class="flex items-start justify-between gap-4">
					<div class="min-w-0">
						<h3 class="truncate text-base font-semibold text-primary transition-colors group-hover:text-secondary dark:text-gray-50">
							{course.name}
						</h3>
						<p class="mt-1 flex items-center gap-1.5 truncate text-xs text-gray-500 dark:text-gray-400">
							<UserCircle size={14} weight="bold" class="shrink-0" />
							<span class="truncate">{course.faculty_username}</span>
						</p>
					</div>

					{#if canTeach}
						<div class="flex shrink-0 items-center gap-1 -mr-2 -mt-1">
							<Button
								variant="icon"
								ghost
								type="button"
								onclick={(event) => editCourse(event, course.id)}
								aria-label={`Edit ${course.name}`}
								title="Edit"
							>
								{#snippet icon()}
									<PencilSimple size={16} />
								{/snippet}
							</Button>
							<Button
								variant="icon"
								ghost
								danger
								type="button"
								onclick={(event) => deleteCourse(event, course.id)}
								aria-label={`Delete ${course.name}`}
								title="Delete"
							>
								{#snippet icon()}
									<Trash size={16} />
								{/snippet}
							</Button>
						</div>
					{/if}
				</div>

				{#if course.description}
					<p class="line-clamp-3 text-sm leading-6 text-gray-600 dark:text-gray-400">
						{course.description}
					</p>
				{/if}

				<div class="mt-auto flex items-center justify-between gap-3 pt-1">
					<div class="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
						<span class="flex items-center gap-1.5">
							<BookOpen size={14} weight="bold" />
							{course.lecture_count} lectures
						</span>
						<span class="flex items-center gap-1.5">
							<UsersThree size={14} weight="bold" />
							{course.student_count} students
						</span>
					</div>

				</div>
			</Card>
		{/each}
	</div>
{/if}
