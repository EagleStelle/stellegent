<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { apiGet, apiPost } from '$lib/api/client';
	import type { Guidance, PipelineResult } from '$lib/types';
	import { ArrowsIn, ArrowsOut, Camera, CircleNotch, Pulse } from 'phosphor-svelte';

	let g = $state<Guidance | null>(null);
	let capturing = $state(false);
	let status = $state('');
	let isFullscreen = $state(false);
	let cameraShell: HTMLElement | null = null;

	const fmt = (v: number | null | undefined, suffix = '') =>
		v == null ? '-' : `${typeof v === 'number' ? v.toFixed(2) : v}${suffix}`;

	async function poll() {
		try {
			g = await apiGet<Guidance>('/api/v1/guidance');
		} catch {
			status = 'Camera unavailable';
		}
	}

	async function capture() {
		capturing = true;
		status = 'Processing...';
		try {
			const res = await apiPost<PipelineResult>('/api/v1/capture', {});
			goto(`/lecture/${res.lecture_id}`);
		} catch (err) {
			status = err instanceof Error ? err.message : 'Capture failed';
			capturing = false;
		}
	}

	async function toggleFullscreen() {
		if (!cameraShell) return;
		if (document.fullscreenElement === cameraShell) {
			await document.exitFullscreen();
		} else {
			await cameraShell.requestFullscreen();
		}
	}

	onMount(() => {
		poll();
		const timer = setInterval(poll, 500);
		const syncFullscreen = () => {
			isFullscreen = document.fullscreenElement === cameraShell;
		};
		document.addEventListener('fullscreenchange', syncFullscreen);
		return () => {
			clearInterval(timer);
			document.removeEventListener('fullscreenchange', syncFullscreen);
		};
	});

	const overlayPanel =
		'rounded-lg bg-black/55 text-zinc-50 shadow-lg shadow-black/20 ring-1 ring-white/10 backdrop-blur-md';
</script>

<section class="h-[calc(100dvh-8rem)] min-h-[34rem] md:h-[calc(100dvh-2rem)]">
	<div
		bind:this={cameraShell}
		class="relative h-full overflow-hidden rounded-xl bg-black shadow-xl shadow-primary/10 [&:fullscreen]:h-screen [&:fullscreen]:w-screen [&:fullscreen]:rounded-none"
	>
		<img src="/api/v1/stream" alt="Live camera preview" class="h-full w-full object-contain" />

		<div class="absolute left-3 top-3 z-10 flex max-w-[calc(100%-5rem)] flex-wrap items-center gap-2">
			<span
				class="inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm font-medium {g?.ready
					? 'bg-primary text-zinc-50'
					: 'bg-black/55 text-zinc-50 ring-1 ring-white/10 backdrop-blur-md'}"
			>
				<Pulse size={16} weight={g?.ready ? 'fill' : 'regular'} />
				{g?.ready ? 'Ready' : 'Checking frame'}
			</span>
			{#if status}
				<span class="{overlayPanel} px-3 py-2 text-sm">{status}</span>
			{/if}
			{#each g?.messages ?? [] as message}
				<span class="{overlayPanel} px-3 py-2 text-sm">{message}</span>
			{/each}
		</div>

		<button
			onclick={toggleFullscreen}
			aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
			title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
			class="{overlayPanel} absolute right-3 top-3 z-10 grid size-11 place-items-center transition-transform duration-200 active:scale-[0.98]"
		>
			{#if isFullscreen}
				<ArrowsIn size={22} />
			{:else}
				<ArrowsOut size={22} />
			{/if}
		</button>

		<div class="absolute inset-x-3 bottom-3 z-10 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
			<dl class="grid max-w-2xl grid-cols-2 gap-2 text-sm text-zinc-50 sm:grid-cols-4">
				<div class="{overlayPanel} px-3 py-2">
					<dt class="text-zinc-300">Sharpness</dt>
					<dd class="font-mono tabular-nums">{fmt(g?.sharpness)}</dd>
				</div>
				<div class="{overlayPanel} px-3 py-2">
					<dt class="text-zinc-300">Distance</dt>
					<dd class="font-mono tabular-nums">{fmt(g?.distance_m, ' m')}</dd>
				</div>
				<div class="{overlayPanel} px-3 py-2">
					<dt class="text-zinc-300">Skew</dt>
					<dd class="font-mono tabular-nums">{fmt(g?.skew_deg, ' deg')}</dd>
				</div>
				<div class="{overlayPanel} px-3 py-2">
					<dt class="text-zinc-300">Coverage</dt>
					<dd class="font-mono tabular-nums">{fmt(g?.coverage)}</dd>
				</div>
			</dl>

			<button
				onclick={capture}
				disabled={capturing}
				class="inline-flex h-12 shrink-0 items-center justify-center gap-2 rounded-lg bg-primary px-5 text-base font-medium text-zinc-50 shadow-lg shadow-black/20 transition-all duration-200 hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/40 disabled:pointer-events-none disabled:opacity-60 active:scale-[0.98]"
			>
				{#if capturing}
					<CircleNotch size={22} class="animate-spin" />
				{:else}
					<Camera size={22} />
				{/if}
				{capturing ? 'Processing...' : 'Capture'}
			</button>
		</div>
	</div>
</section>
