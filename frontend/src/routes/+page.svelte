<script lang="ts">
	import { goto } from '$app/navigation';
	import { createQuery } from '@tanstack/svelte-query';
	import { apiGet } from '$lib/api/client';
	import type { LectureSummary, PipelineResult, User } from '$lib/types';
	import Input from '$lib/components/ui/Input.svelte';
	import { CircleNotch, MagnifyingGlass, UploadSimple } from 'phosphor-svelte';

	let q = $state('');
	let uploadInput: HTMLInputElement | null = $state(null);
	let uploading = $state(false);
	let uploadError = $state('');

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
</script>

<div class="mb-4 flex gap-2">
	<div class="min-w-0 flex-1">
		<Input id="search" bind:value={q} icon={MagnifyingGlass} placeholder="Search" />
	</div>
	{#if canUpload}
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
			class="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-sm font-medium text-white shadow-sm shadow-primary/20 transition-all duration-200 hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/30 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-60 sm:px-4"
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
			<a
				href={`/lecture/${lec.id}`}
				class="rounded-lg border border-zinc-200 bg-white p-4 transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 dark:hover:bg-zinc-700"
			>
				<div class="mb-1 text-base font-medium">{lec.course_name ?? 'Untitled'}</div>
				<div class="mb-2 text-sm text-zinc-500 dark:text-zinc-400">
					{new Date(lec.captured_at).toLocaleString()}
				</div>
				<p class="line-clamp-3 text-base leading-7 text-zinc-500 dark:text-zinc-400">{lec.summary ?? ''}</p>
			</a>
		{/each}
	</div>
{/if}
