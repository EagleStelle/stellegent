<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { apiGet, apiDelete } from '$lib/api/client';
	import type { Course, CourseOptions, LectureSummary, ProcessingTask, User } from '$lib/types';
	import Input from '$lib/components/ui/Input.svelte';
	import Card from '$lib/components/ui/Card.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import ComboBox from '$lib/components/ui/ComboBox.svelte';
	import { CircleNotch, MagnifyingGlass, Plus, CalendarBlank, PencilSimple, Trash, BookOpen, UserCircle, WarningCircle } from 'phosphor-svelte';
	import { untrack } from 'svelte';
	import { pendingUpload } from '$lib/upload.svelte';

	let q = $state('');
	let facultyFilter = $state('');
	let uploadInput: HTMLInputElement | null = $state(null);
	let selectedCourseId = $state(page.url.searchParams.get('courseId') ?? '');

	const lectures = createQuery(() => ({
		queryKey: ['lectures'],
		queryFn: () => apiGet<LectureSummary[]>('/api/v1/lectures')
	}));
	const qc = useQueryClient();
	let hadProcessingTasks = $state(false);

	const me = createQuery(() => ({
		queryKey: ['me'],
		queryFn: () => apiGet<User>('/api/v1/me')
	}));

	$effect(() => {
		if (lectures.isError) goto('/');
	});

	const canUpload = $derived(me.data?.role === 'prof' || me.data?.role === 'admin');
	const courses = createQuery(() => ({
		queryKey: ['courses'],
		queryFn: () => apiGet<Course[]>('/api/v1/courses')
	}));
	const processingTasks = createQuery(() => ({
		queryKey: ['processing-tasks'],
		queryFn: () => apiGet<ProcessingTask[]>('/api/v1/tasks'),
		refetchInterval: 2500
	}));
	const options = createQuery(() => ({
		queryKey: ['course-options'],
		queryFn: () => apiGet<CourseOptions>('/api/v1/courses/options')
	}));

	const facultyOptions = $derived(options.data?.faculty ?? []);
	const courseFilterOptions = $derived(
		(courses.data ?? []).map((c) => ({
			value: String(c.id),
			label: c.name,
		})),
	);

	// URL -> state: adopt the courseId from the URL (deep link, back/forward).
	// The current selection is read untracked so this effect fires only when the
	// URL changes, never when the user picks a course (which would revert it).
	$effect(() => {
		const courseId = page.url.searchParams.get('courseId') ?? '';
		if (untrack(() => selectedCourseId) !== courseId) selectedCourseId = courseId;
	});

	// state -> URL: when the user picks a course, push it to the URL. The URL is
	// read untracked so this effect fires only on a user selection, not when the
	// URL changes from the effect above.
	$effect(() => {
		const sel = selectedCourseId;
		const courseId = untrack(() => page.url.searchParams.get('courseId') ?? '');
		if (sel === courseId) return;
		const hasCourseOption =
			sel === '' || (courses.data ?? []).some((course) => String(course.id) === sel);
		if (!hasCourseOption) return;
		goto(sel ? `/lectures?courseId=${encodeURIComponent(sel)}` : '/lectures', {
			keepFocus: true,
			noScroll: true,
		});
	});

	const filtered = $derived(
		(lectures.data ?? []).filter((l) => {
			if (facultyFilter && String(l.owner_user_id) !== facultyFilter) return false;
			if (selectedCourseId && String(l.course_id) !== selectedCourseId) return false;
			if (!q.trim()) return true;
			const hay = `${l.course_name ?? ''} ${l.summary ?? ''} ${l.tags ?? ''}`.toLowerCase();
			return hay.includes(q.toLowerCase());
		})
	);
	const taskCards = $derived(processingTasks.data ?? []);
	const hasActiveProcessing = $derived(taskCards.some((task) => task.status === 'queued' || task.status === 'running'));

	$effect(() => {
		if (hasActiveProcessing) {
			hadProcessingTasks = true;
			return;
		}
		if (!hadProcessingTasks) return;
		hadProcessingTasks = false;
		void qc.invalidateQueries({ queryKey: ['lectures'] });
		void qc.invalidateQueries({ queryKey: ['courses'] });
	});

	function chooseUpload() {
		uploadInput?.click();
	}

	// Picking a file no longer uploads immediately. Stash it and head to the add
	// page, where the user sets course/visibility and confirms with a preview.
	function onFile(e: Event) {
		const input = e.target as HTMLInputElement;
		const selected = input.files?.[0];
		input.value = '';
		if (!selected) return;
		pendingUpload.set(selected);
		goto(selectedCourseId ? `/lectures/add?courseId=${encodeURIComponent(selectedCourseId)}` : '/lectures/add');
	}

	function taskTitle(task: ProcessingTask) {
		if (task.kind === 'capture') return task.course_name ?? 'Camera capture';
		return task.course_name ?? task.filename ?? 'Lecture upload';
	}

	function taskStatus(task: ProcessingTask) {
		if (task.status === 'queued') return task.queue_position ? `Queued #${task.queue_position}` : 'Queued';
		if (task.status === 'running') return 'Processing';
		if (task.status === 'failed') return 'Failed';
		return 'Complete';
	}

	function editLecture(e: MouseEvent, id: string) {
		e.preventDefault();
		e.stopPropagation();
		goto(`/lectures/${id}/edit`);
	}

	async function deleteLecture(e: MouseEvent, id: string) {
		e.preventDefault();
		e.stopPropagation();
		if (!confirm('Delete this lecture?')) return;
		try {
			await apiDelete(`/api/v1/lectures/${id}`);
			await qc.invalidateQueries({ queryKey: ['lectures'] });
		} catch (err) {
			console.error('Delete failed:', err);
		}
	}
</script>

<div class="mb-4 flex flex-col gap-2 lg:flex-row lg:items-center">
	<div class="min-w-0 flex-1">
		<Input id="search" bind:value={q} icon={MagnifyingGlass} />
	</div>
	<div class="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center">
		<ComboBox
			bind:value={facultyFilter}
			placeholder="All faculty"
			class="w-full"
			options={facultyOptions.map((f) => ({
				value: String(f.id),
				label: f.username,
			}))}
		/>
		<ComboBox
			bind:value={selectedCourseId}
			placeholder="All courses"
			class="w-full"
			options={courseFilterOptions}
		/>
	</div>
	{#if canUpload}
		<input
			bind:this={uploadInput}
			type="file"
			accept=".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
			onchange={onFile}
			class="sr-only"
		/>
		<Button
			variant="icon+text"
			type="button"
			onclick={chooseUpload}
			aria-label="Add lecture"
		>
			{#snippet icon()}
				<Plus size={18} />
			{/snippet}
			Add lecture
		</Button>
	{/if}
</div>

{#if lectures.isLoading}
	<p class="text-zinc-500 dark:text-zinc-400">Loading</p>
{:else if taskCards.length > 0 || filtered.length > 0}
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each taskCards as task (task.id)}
			<Card class="flex h-full flex-col gap-3 border-secondary/30 bg-secondary/5 dark:border-secondary/40 dark:bg-secondary/10">
				<div class="flex items-start justify-between gap-4">
					<div class="flex min-w-0 flex-col gap-1.5">
						<div class="flex items-center gap-2">
							{#if task.status === 'failed'}
								<WarningCircle size={18} weight="bold" class="shrink-0 text-red-600 dark:text-red-400" />
							{:else}
								<CircleNotch size={18} class="shrink-0 animate-spin text-secondary" />
							{/if}
							<span class="text-xs font-semibold text-secondary">
								{taskStatus(task)}
							</span>
						</div>
						<h3 class="truncate text-base font-semibold text-primary dark:text-gray-50">
							{taskTitle(task)}
						</h3>
						<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
							<span class="flex min-w-0 items-center gap-1.5">
								<UserCircle size={14} weight="bold" class="shrink-0" />
								<span class="truncate">{task.created_by_username ?? 'Unknown'}</span>
							</span>
							{#if task.course_name}
								<span class="flex min-w-0 items-center gap-1.5">
									<BookOpen size={14} weight="bold" class="shrink-0" />
									<span class="truncate">{task.course_name}</span>
								</span>
							{/if}
						</div>
						<div class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
							<CalendarBlank size={14} weight="bold" />
							<span class="truncate">{new Date(task.created_at).toLocaleString()}</span>
						</div>
					</div>
				</div>

				{#if task.status === 'queued'}
					<p class="text-sm leading-6 text-gray-600 dark:text-gray-400">
						Waiting for the processing worker.
					</p>
				{:else if task.status === 'running'}
					<p class="text-sm leading-6 text-gray-600 dark:text-gray-400">
						Running in the background.
					</p>
				{:else if task.status === 'failed'}
					<p class="line-clamp-3 text-sm leading-6 text-red-600 dark:text-red-400">
						{task.error ?? 'Processing failed'}
					</p>
				{/if}
			</Card>
		{/each}
		{#each filtered as lec (lec.id)}
			<Card href={`/lectures/${lec.id}`} class="group flex h-full flex-col gap-3">
				<div class="flex items-start justify-between gap-4">
					<div class="flex min-w-0 flex-col gap-1.5">
						<h3 class="truncate text-base font-semibold text-primary transition-colors group-hover:text-secondary dark:text-gray-50">
							{lec.title ?? lec.course_name ?? 'Untitled'}
						</h3>
						<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
							<span class="flex min-w-0 items-center gap-1.5">
								<UserCircle size={14} weight="bold" class="shrink-0" />
								<span class="truncate">{lec.owner_username ?? 'Unknown'}</span>
							</span>
							{#if lec.course_name}
								<span class="flex min-w-0 items-center gap-1.5">
									<BookOpen size={14} weight="bold" class="shrink-0" />
									<span class="truncate">{lec.course_name}</span>
								</span>
							{/if}
						</div>
						<div class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
							<CalendarBlank size={14} weight="bold" />
							<span class="truncate">{new Date(lec.captured_at).toLocaleString()}</span>
						</div>
					</div>

					{#if me.data?.role === 'admin' || (me.data?.role === 'prof' && lec.owner_user_id === me.data?.uid)}
						<div class="flex shrink-0 items-center gap-1 -mr-2 -mt-1">
							<Button
								variant="icon"
								ghost
								type="button"
								onclick={(e) => editLecture(e, lec.id)}
								aria-label={`Edit ${lec.course_name ?? 'lecture'}`}
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
								onclick={(e) => deleteLecture(e, lec.id)}
								aria-label={`Delete ${lec.course_name ?? 'lecture'}`}
								title="Delete"
							>
								{#snippet icon()}
									<Trash size={16} />
								{/snippet}
							</Button>
						</div>
					{/if}
				</div>

				{#if lec.summary}
					<p class="line-clamp-3 text-sm leading-6 text-gray-600 dark:text-gray-400">
						{lec.summary}
					</p>
				{/if}
			</Card>
		{/each}
	</div>
{/if}
