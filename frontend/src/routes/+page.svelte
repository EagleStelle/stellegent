<script lang="ts">
	import { goto } from '$app/navigation';
	import { createQuery } from '@tanstack/svelte-query';
	import { apiGet } from '$lib/api/client';
	import type { Course, LectureSummary, PipelineResult, User, Visibility } from '$lib/types';
	import Input from '$lib/components/ui/Input.svelte';
	import Card from '$lib/components/ui/Card.svelte';
	import { CircleNotch, MagnifyingGlass, UploadSimple, CalendarBlank } from 'phosphor-svelte';

	let q = $state('');
	let uploadInput: HTMLInputElement | null = $state(null);
	let uploading = $state(false);
	let uploadError = $state('');
	let selectedCourseId = $state('');
	let visibility = $state<Visibility>('public');

	const lectures = createQuery(() => ({
		queryKey: ['lectures'],
		queryFn: () => apiGet<LectureSummary[]>('/api/v1/lectures')
	}));

	const me = createQuery(() => ({
		queryKey: ['me'],
		queryFn: () => apiGet<User>('/api/v1/me')
	}));

	$effect(() => {
		if (lectures.isError) goto('/login');
	});

	const canUpload = $derived(me.data?.role === 'prof' || me.data?.role === 'admin');
	const courses = createQuery(() => ({
		queryKey: ['courses'],
		queryFn: () => apiGet<Course[]>('/api/v1/courses'),
		enabled: canUpload
	}));

	const filtered = $derived(
		(lectures.data ?? []).filter((l) => {
			if (!q.trim()) return true;
			const hay = `${l.course_name ?? ''} ${l.summary ?? ''} ${l.tags ?? ''}`.toLowerCase();
			return hay.includes(q.toLowerCase());
		})
	);

	function chooseUpload() {
		if (!uploading) uploadInput?.click();
	}

	async function onFile(e: Event) {
		const input = e.target as HTMLInputElement;
		const selected = input.files?.[0];
		if (!selected) return;
		await upload(selected);
		input.value = '';
	}

	async function upload(selected: File) {
		uploadError = '';
		uploading = true;
		const fd = new FormData();
		fd.append('image', selected);
		fd.append('visibility', visibility);
		if (selectedCourseId) fd.append('course_id', selectedCourseId);

		try {
			const res = await fetch('/api/v1/upload', {
				method: 'POST',
				credentials: 'include',
				body: fd
			});
			if (!res.ok) {
				const body = (await res.json().catch(() => null)) as { detail?: string } | null;
				throw new Error(body?.detail ?? res.statusText);
			}
			const data: PipelineResult = await res.json();
			goto(`/lecture/${data.lecture_id}`);
		} catch (err) {
			uploadError = err instanceof Error ? err.message : 'Upload failed';
			uploading = false;
		}
	}

	function getTags(tags: string | null | undefined) {
		return (tags ?? '')
			.split(',')
			.map((t) => t.trim())
			.filter(Boolean)
			.slice(0, 3);
	}
</script>

<div class="mb-4 flex flex-col gap-2 lg:flex-row lg:items-center">
	<div class="min-w-0 flex-1">
		<Input id="search" bind:value={q} icon={MagnifyingGlass} placeholder="Search" />
	</div>
	{#if canUpload}
		<div class="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center">
			<select
				bind:value={selectedCourseId}
				aria-label="Course"
				class="h-10 min-w-0 rounded-lg border border-gray-200 bg-white px-3 text-sm font-medium text-primary outline-none transition-all focus:border-secondary/60 focus:ring-3 focus:ring-secondary/15 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-50"
			>
				<option value="">No course</option>
				{#each courses.data ?? [] as course (course.id)}
					<option value={String(course.id)}>{course.name}</option>
				{/each}
			</select>
			<div
				class="grid h-10 grid-cols-2 rounded-lg border border-gray-200 bg-white p-1 text-sm font-semibold dark:border-gray-800 dark:bg-gray-900"
			>
				<button
					type="button"
					onclick={() => (visibility = 'public')}
					class="rounded-md px-3 transition-colors {visibility === 'public'
						? 'bg-secondary text-white'
						: 'text-gray-500 hover:text-primary dark:text-gray-400 dark:hover:text-gray-100'}"
				>
					Public
				</button>
				<button
					type="button"
					onclick={() => (visibility = 'private')}
					class="rounded-md px-3 transition-colors {visibility === 'private'
						? 'bg-secondary text-white'
						: 'text-gray-500 hover:text-primary dark:text-gray-400 dark:hover:text-gray-100'}"
				>
					Private
				</button>
			</div>
		</div>
		<input
			bind:this={uploadInput}
			type="file"
			accept=".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
			onchange={onFile}
			disabled={uploading}
			class="sr-only"
		/>
		<button
			type="button"
			onclick={chooseUpload}
			disabled={uploading}
			aria-label="Upload board image"
			class="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-lg bg-primary px-3.5 text-sm font-medium text-white shadow-sm shadow-primary/20 transition-all duration-200 hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/30 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-60"
		>
			{#if uploading}
				<CircleNotch size={18} class="animate-spin" />
				<span class="hidden sm:inline">Processing</span>
			{:else}
				<UploadSimple size={18} />
				<span class="hidden sm:inline">Upload</span>
			{/if}
		</button>
	{/if}
</div>

{#if uploadError}
	<p class="mb-4 rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400" role="alert">
		{uploadError}
	</p>
{/if}

{#if lectures.isLoading}
	<p class="text-zinc-500 dark:text-zinc-400">Loading</p>
{:else if filtered.length > 0}
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each filtered as lec (lec.id)}
			{@const tags = getTags(lec.tags)}
			<Card href={`/lecture/${lec.id}`} class="group flex h-full flex-col gap-3">
				<div class="flex flex-col gap-1">
					<h3 class="text-base font-semibold text-primary transition-colors group-hover:text-secondary dark:text-gray-50">
						{lec.course_name ?? 'Untitled'}
					</h3>
					<div class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
						<CalendarBlank size={14} weight="bold" />
						<span>{new Date(lec.captured_at).toLocaleString()}</span>
					</div>
				</div>

				{#if lec.summary}
					<p class="line-clamp-3 text-sm leading-6 text-gray-600 dark:text-gray-400">
						{lec.summary}
					</p>
				{/if}

				{#if tags.length}
					<div class="mt-auto flex flex-wrap gap-1.5 pt-1">
						{#each tags as tag (tag)}
							<span class="rounded-full bg-secondary/10 px-2.5 py-0.5 text-[11px] font-medium text-secondary">
								{tag}
							</span>
						{/each}
					</div>
				{/if}
			</Card>
		{/each}
	</div>
{/if}
