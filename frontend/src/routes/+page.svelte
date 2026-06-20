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

	// Redirect to login on 401.
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

<div class="mb-6 flex items-center justify-between">
	<h1 class="text-2xl font-semibold">Lectures</h1>
	<input
		bind:value={q}
		placeholder="Search…"
		class="rounded-md border border-input bg-background px-3 py-2 text-sm"
	/>
</div>

{#if lectures.isLoading}
	<p class="text-muted-foreground">Loading…</p>
{:else if filtered.length === 0}
{:else}
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each filtered as lec (lec.id)}
			<a
				href={`/lecture/${lec.id}`}
				class="rounded-lg border border-border bg-card p-4 transition-colors hover:bg-secondary"
			>
				<div class="mb-1 text-sm font-medium">{lec.course_name ?? 'Untitled'}</div>
				<div class="mb-2 text-xs text-muted-foreground">
					{new Date(lec.captured_at).toLocaleString()}
				</div>
				<p class="line-clamp-3 text-sm text-muted-foreground">{lec.summary ?? ''}</p>
			</a>
		{/each}
	</div>
{/if}
