<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { createQuery } from '@tanstack/svelte-query';
	import { apiGet, apiPost } from '$lib/api/client';
	import type { CapturePayload, Course, Guidance, PipelineResult, Visibility } from '$lib/types';
	import Select from '$lib/components/ui/Select.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { ArrowsIn, ArrowsOut, Camera, CircleNotch, Pulse } from 'phosphor-svelte';

	let g = $state<Guidance | null>(null);
	let capturing = $state(false);
	let status = $state('');
	let isFullscreen = $state(false);
	let cameraShell: HTMLElement | null = null;
	let selectedCourseId = $state('');
	let visibility = $state<Visibility>('public');

	const courses = createQuery(() => ({
		queryKey: ['courses'],
		queryFn: () => apiGet<Course[]>('/api/v1/courses')
	}));

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
			const payload: CapturePayload = {
				visibility,
				course_id: selectedCourseId ? Number(selectedCourseId) : null
			};
			const res = await apiPost<PipelineResult>('/api/v1/capture', payload);
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
		class="relative h-full overflow-hidden rounded-lg bg-black shadow-xl shadow-primary/10 [&:fullscreen]:h-screen [&:fullscreen]:w-screen [&:fullscreen]:rounded-none"
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

		<Button
			variant="icon"
			onclick={toggleFullscreen}
			aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
			class="{overlayPanel} absolute right-3 top-3 z-10 !bg-black/55 shadow-none"
		>
			{#snippet icon()}
				{#if isFullscreen}
					<ArrowsIn size={22} />
				{:else}
					<ArrowsOut size={22} />
				{/if}
			{/snippet}
		</Button>

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

			<div class="flex flex-col gap-2 sm:items-end">
				<div class="flex flex-col gap-2 sm:flex-row">
					<Select
						bind:value={selectedCourseId}
						placeholder="No course"
						class="{overlayPanel} h-10 min-w-40 border-0 !text-white !bg-transparent px-3 text-sm font-medium focus:ring-3 focus:ring-secondary/40"
						options={(courses.data ?? []).map((c) => ({
							value: String(c.id),
							label: c.name,
						}))}
					/>
					<div class="{overlayPanel} grid h-10 grid-cols-2 p-1 text-sm font-semibold">
						<Button
							type="button"
							onclick={() => (visibility = 'public')}
							class="h-8 {visibility === 'public'
								? ''
								: '!bg-transparent !text-zinc-300 hover:!text-white'}"
						>
							Public
						</Button>
						<Button
							type="button"
							onclick={() => (visibility = 'private')}
							class="h-8 {visibility === 'private'
								? ''
								: '!bg-transparent !text-zinc-300 hover:!text-white'}"
						>
							Private
						</Button>
					</div>
				</div>

				<Button
					onclick={capture}
					disabled={capturing}
					class="h-12 px-5 text-base shadow-lg shadow-black/20"
				>
					{#if capturing}
						<CircleNotch size={22} class="animate-spin" />
					{:else}
						<Camera size={22} />
					{/if}
					{capturing ? 'Processing...' : 'Capture'}
				</Button>
			</div>
		</div>
	</div>
</section>
