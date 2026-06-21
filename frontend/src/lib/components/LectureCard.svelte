<script lang="ts">
	import type { LectureSummary } from '$lib/types';
	import Card from '$lib/components/ui/Card.svelte';
	import { CalendarBlank } from 'phosphor-svelte';

	let { lecture }: { lecture: LectureSummary } = $props();

	const tags = $derived(
		(lecture.tags ?? '')
			.split(',')
			.map((t) => t.trim())
			.filter(Boolean)
			.slice(0, 3)
	);
</script>

<Card href={`/lecture/${lecture.id}`} variant="accent" class="group flex h-full flex-col gap-3">
	<div class="flex flex-col gap-1">
		<h3 class="text-base font-semibold text-primary transition-colors group-hover:text-secondary dark:text-gray-50">
			{lecture.course_name ?? 'Untitled'}
		</h3>
		<div class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
			<CalendarBlank size={14} weight="bold" />
			<span>{new Date(lecture.captured_at).toLocaleString()}</span>
		</div>
	</div>

	{#if lecture.summary}
		<p class="line-clamp-3 text-sm leading-6 text-gray-600 dark:text-gray-400">
			{lecture.summary}
		</p>
	{/if}

	{#if tags.length}
		<div class="mt-auto flex flex-wrap gap-1.5 pt-1">
			{#each tags as tag (tag)}
				<span
					class="rounded-full bg-secondary/10 px-2.5 py-0.5 text-[11px] font-medium text-secondary"
				>
					{tag}
				</span>
			{/each}
		</div>
	{/if}
</Card>
