<script lang="ts">
	import { goto } from '$app/navigation';
	import { createQuery } from '@tanstack/svelte-query';
	import { apiGet } from '$lib/api/client';
	import type { LectureSummary } from '$lib/types';

	let q = $state('');

	const lectures = createQuery(() => ({
		queryKey: ['lectures'],
		queryFn: () => apiGet<LectureSummary[]>('/api/v1/lectures')
	}));

	$effect(() => {
		if (lectures.isError) goto('/login');
	});

	const filtered = $derived(
		(lectures.data ?? []).filter((l) => {
			if (!q.trim()) return true;
			const hay = `${l.course_name ?? ''} ${l.summary ?? ''} ${l.tags ?? ''}`.toLowerCase();
			return hay.includes(q.toLowerCase());
		})
	);
</script>

<div class="mb-4 flex justify-end">
	<input
		bind:value={q}
		placeholder="Search…"
		class="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2.5 text-base sm:max-w-sm dark:border-zinc-700 dark:bg-zinc-900"
	/>
</div>

{#if lectures.isLoading}
	<p class="text-zinc-500 dark:text-zinc-400">Loading…</p>
{:else if filtered.length > 0}
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each filtered as lec (lec.id)}
			<a
				href={`/lecture/${lec.id}`}
				class="rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4 transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-700"
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
