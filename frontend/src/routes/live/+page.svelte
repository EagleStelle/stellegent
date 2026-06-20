<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { apiGet, apiPost } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import type { Guidance, PipelineResult } from '$lib/types';

	let course = $state('');
	let g = $state<Guidance | null>(null);
	let capturing = $state(false);
	let status = $state('');
	let timer: ReturnType<typeof setInterval>;

	const fmt = (v: number | null | undefined) =>
		v == null ? '—' : typeof v === 'number' ? v.toFixed(2) : v;

	async function poll() {
		try {
			g = await apiGet<Guidance>('/api/v1/guidance');
		} catch {
			/* camera may be absent; ignore */
		}
	}

	async function capture() {
		capturing = true;
		status = 'Capturing + processing…';
		try {
			const res = await apiPost<PipelineResult>(
				'/api/v1/capture',
				course.trim() ? { course: course.trim() } : {}
			);
			goto(`/lecture/${res.lecture_id}`);
		} catch (err) {
			status = err instanceof Error ? err.message : 'capture failed';
			capturing = false;
		}
	}

	onMount(() => {
		poll();
		timer = setInterval(poll, 500);
	});
	onDestroy(() => clearInterval(timer));
</script>

<h1 class="mb-6 text-2xl font-semibold">Live capture</h1>

<div class="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
	<div class="overflow-hidden rounded-lg border border-border bg-black">
		<!-- MJPEG stream is a plain <img>, not a Query -->
		<img src="/api/v1/stream" alt="live preview" class="w-full" />
	</div>

	<div class="space-y-4">
		<input
			bind:value={course}
			placeholder="Course (optional)"
			class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
		/>

		<div class="rounded-lg border border-border p-4">
			<div class="mb-2 space-y-1">
				{#each g?.messages ?? [] as m}
					<div
						class="rounded px-2 py-1 text-sm {g?.ready
							? 'bg-green-100 text-green-800'
							: 'bg-secondary'}"
					>
						{m}
					</div>
				{/each}
			</div>
			<ul class="space-y-1 text-sm text-muted-foreground">
				<li>Sharpness: {fmt(g?.sharpness)}</li>
				<li>Distance: {fmt(g?.distance_m)} m</li>
				<li>Skew: {fmt(g?.skew_deg)}°</li>
				<li>Coverage: {fmt(g?.coverage)}</li>
			</ul>
		</div>

		<Button
			onclick={capture}
			disabled={capturing}
			variant={g?.ready ? 'default' : 'secondary'}
			class="w-full"
		>
			{capturing ? 'Processing…' : 'Capture'}
		</Button>
		{#if status}<p class="text-sm text-muted-foreground">{status}</p>{/if}
	</div>
</div>
