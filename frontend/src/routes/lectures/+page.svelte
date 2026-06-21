<script lang="ts">
	import { goto } from '$app/navigation';
	import { createQuery } from '@tanstack/svelte-query';
	import { apiGet } from '$lib/api/client';
	import type { Course, LectureSummary, PipelineResult, User, Visibility } from '$lib/types';
	import Input from '$lib/components/ui/Input.svelte';
	import Card from '$lib/components/ui/Card.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Select from '$lib/components/ui/Select.svelte';
	import { CircleNotch, MagnifyingGlass, Plus, CalendarBlank } from 'phosphor-svelte';

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
		if (lectures.isError) goto('/');
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
			goto(`/lectures/${data.lecture_id}`);
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
		<Input id="search" bind:value={q} icon={MagnifyingGlass} />
	</div>
	{#if canUpload}
		<div class="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center">
			<Select
				bind:value={selectedCourseId}
				placeholder="All courses"
				class="w-48 shrink-0"
				options={(courses.data ?? []).map((c) => ({
					value: String(c.id),
					label: c.name,
				}))}
			/>
		</div>
		<input
			bind:this={uploadInput}
			type="file"
			accept=".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
			onchange={onFile}
			disabled={uploading}
			class="sr-only"
		/>
		<Button
			variant="icon+text"
			type="button"
			onclick={chooseUpload}
			disabled={uploading}
			aria-label="Add lecture"
		>
			{#snippet icon()}
				{#if uploading}
					<CircleNotch size={18} class="animate-spin" />
				{:else}
					<Plus size={18} />
				{/if}
			{/snippet}
			{uploading ? 'Processing' : 'Add lecture'}
		</Button>
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
			<Card href={`/lectures/${lec.id}`} class="group flex h-full flex-col gap-3">
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
