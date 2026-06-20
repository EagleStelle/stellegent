<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { apiGet, apiPost } from '$lib/api/client';
	import type { Guidance, PipelineResult } from '$lib/types';
	import { Camera, Pulse, CircleNotch } from 'phosphor-svelte';

	let course = $state('');
	let g = $state<Guidance | null>(null);
	let capturing = $state(false);
	let status = $state('');
	let timer: ReturnType<typeof setInterval>;

	const fmt = (v: number | null | undefined, suffix = '') =>
		v == null ? '-' : `${typeof v === 'number' ? v.toFixed(2) : v}${suffix}`;

	async function poll() {
		try {
			g = await apiGet<Guidance>('/api/v1/guidance');
		} catch {
			/* Camera may be absent; ignore polling errors. */
		}
	}

	async function capture() {
		capturing = true;
		status = 'Capturing and processing...';
		try {
			const res = await apiPost<PipelineResult>(
				'/api/v1/capture',
				course.trim() ? { course: course.trim() } : {}
			);
			goto(`/lecture/${res.lecture_id}`);
		} catch (err) {
			status = err instanceof Error ? err.message : 'Capture failed';
			capturing = false;
		}
	}

	onMount(() => {
		poll();
		timer = setInterval(poll, 500);
	});
	onDestroy(() => clearInterval(timer));

	const badgeBase =
		'inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden whitespace-nowrap rounded-2xl border border-transparent px-2 py-0.5 text-xs font-medium';
</script>

<section class="space-y-6">
	<div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
		<div class="space-y-2">
			<p class="text-sm font-medium text-primary">Live capture</p>
			<h1 class="text-3xl font-semibold tracking-tight text-balance">Frame the board and capture</h1>
			<p class="max-w-2xl text-sm leading-6 text-muted-foreground">
				Use the camera preview to align the board before sending it through the lecture pipeline.
			</p>
		</div>
		<span
			class="{badgeBase} {g?.ready
				? 'bg-primary text-primary-foreground'
				: 'bg-secondary text-secondary-foreground'}"
		>
			<Pulse size={12} />
			{g?.ready ? 'Ready' : 'Checking frame'}
		</span>
	</div>

	<div class="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
		<div
			class="overflow-hidden rounded-[min(var(--radius-4xl),24px)] border border-border/70 bg-black shadow-xl shadow-primary/10"
		>
			<img src="/api/v1/stream" alt="Live camera preview" class="aspect-video w-full object-contain" />
		</div>

		<div
			class="flex flex-col gap-5 overflow-hidden rounded-[min(var(--radius-4xl),24px)] bg-card py-5 text-sm text-card-foreground shadow-sm ring-1 ring-foreground/5 dark:ring-foreground/10"
		>
			<div class="grid auto-rows-min items-start gap-1.5 px-5">
				<div class="text-base font-medium">Capture controls</div>
				<p class="text-sm text-muted-foreground">
					Optional course names make lectures easier to find later.
				</p>
			</div>
			<div class="space-y-4 px-5">
				<div class="grid gap-2">
					<label
						for="course"
						class="flex items-center gap-2 text-sm font-medium leading-none select-none"
					>
						Course
					</label>
					<input
						id="course"
						bind:value={course}
						placeholder="Optional"
						class="h-8 w-full min-w-0 rounded-2xl border border-transparent bg-input/50 px-2.5 py-1 text-base outline-none transition-[color,box-shadow] duration-200 placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
					/>
				</div>

				<div class="rounded-3xl bg-muted/70 p-3">
					<div class="mb-3 flex flex-wrap gap-1.5">
						{#if g?.messages?.length}
							{#each g.messages as m}
								<span
									class="{badgeBase} {g.ready
										? 'bg-primary text-primary-foreground'
										: 'bg-secondary text-secondary-foreground'}"
								>
									{m}
								</span>
							{/each}
						{:else}
							<span class="{badgeBase} bg-secondary text-secondary-foreground">
								Waiting for camera guidance
							</span>
						{/if}
					</div>
					<dl class="grid grid-cols-2 gap-2 text-sm">
						<div class="rounded-2xl bg-background/70 p-2">
							<dt class="text-muted-foreground">Sharpness</dt>
							<dd class="font-mono tabular-nums">{fmt(g?.sharpness)}</dd>
						</div>
						<div class="rounded-2xl bg-background/70 p-2">
							<dt class="text-muted-foreground">Distance</dt>
							<dd class="font-mono tabular-nums">{fmt(g?.distance_m, ' m')}</dd>
						</div>
						<div class="rounded-2xl bg-background/70 p-2">
							<dt class="text-muted-foreground">Skew</dt>
							<dd class="font-mono tabular-nums">{fmt(g?.skew_deg, ' deg')}</dd>
						</div>
						<div class="rounded-2xl bg-background/70 p-2">
							<dt class="text-muted-foreground">Coverage</dt>
							<dd class="font-mono tabular-nums">{fmt(g?.coverage)}</dd>
						</div>
					</dl>
				</div>

				{#if status}
					<p class="rounded-2xl bg-muted px-3 py-2 text-sm text-muted-foreground">{status}</p>
				{/if}
			</div>
			<div class="flex items-center px-5">
				<button
					onclick={capture}
					disabled={capturing}
					class="inline-flex h-8 w-full shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-2xl border border-transparent px-3 text-sm font-medium outline-none transition-all focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 disabled:pointer-events-none disabled:opacity-50 {g?.ready
						? 'bg-primary text-primary-foreground hover:bg-primary/80'
						: 'bg-secondary text-secondary-foreground hover:bg-[color-mix(in_oklch,var(--secondary),var(--foreground)_5%)]'}"
				>
					{#if capturing}
						<CircleNotch size={16} class="animate-spin" />
					{:else}
						<Camera size={16} />
					{/if}
					{capturing ? 'Processing...' : 'Capture board'}
				</button>
			</div>
		</div>
	</div>
</section>
