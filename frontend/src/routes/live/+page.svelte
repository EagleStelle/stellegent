<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { createQuery } from '@tanstack/svelte-query';
	import { apiGet, apiPost } from '$lib/api/client';
	import type { CapturePayload, Course, PipelineResult, Visibility } from '$lib/types';
	import ComboBox, { type ComboBoxOption } from '$lib/components/ui/ComboBox.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { ArrowsIn, ArrowsOut, Camera, CircleNotch, ArrowsClockwise } from 'phosphor-svelte';

	// Camera source:
	//  - 'client': the browser's own camera via getUserMedia (laptop/phone webcam).
	//    Captured frames are uploaded to /api/v1/upload for the pipeline.
	//  - 'server': the backend's camera via the MJPEG /stream + /capture endpoints.
	//    This is the path a Raspberry Pi uses for the CSI Camera Module 3 (imx708),
	//    which is reachable only through libcamera/picamera2 on the Pi, never through
	//    the browser. When the backend runs on the Pi, 'server' == the Pi's camera.
	// We try 'client' first and fall back to 'server' when getUserMedia is
	// unavailable (no device, denied, or insecure context), so a Pi browser that
	// can't see its CSI camera automatically uses the Pi-side capture path.
	type Source = 'client' | 'server';

	let source = $state<Source>('server');
	let initializing = $state(true);
	let capturing = $state(false);
	let status = $state('');
	let isFullscreen = $state(false);
	let cameraShell = $state<HTMLElement | null>(null);
	let videoEl = $state<HTMLVideoElement | null>(null);
	let canvasEl = $state<HTMLCanvasElement | null>(null);
	let stream: MediaStream | null = null;
	let selectedCourseId = $state('');
	let visibility = $state<string>('public');

	// Framing guidance for the browser-camera path. We ship downscaled frames to
	// /api/v1/guidance/analyze; the backend does the board detection and returns
	// JSON (corners + messages). We draw the overlay on a canvas over the live
	// <video>, so the video stays smooth and only the lightweight JSON round-trips.
	type Guidance = {
		width: number;
		height: number;
		corners: [number, number][] | null;
		messages: string[];
		ready: boolean;
	};
	const GUIDE_WIDTH = 960;
	const GUIDE_INTERVAL_MS = 180;
	let guideRunning = false;
	let guideTimer: ReturnType<typeof setTimeout> | null = null;

	const visibilityOptions: ComboBoxOption[] = [
		{ value: 'public', label: 'Public' },
		{ value: 'private', label: 'Private' }
	];

	const courses = createQuery(() => ({
		queryKey: ['courses'],
		queryFn: () => apiGet<Course[]>('/api/v1/courses')
	}));

	function stopClientCamera() {
		stream?.getTracks().forEach((t) => t.stop());
		stream = null;
		if (videoEl) videoEl.srcObject = null;
	}

	async function startClientCamera(): Promise<boolean> {
		if (!navigator.mediaDevices?.getUserMedia) return false;
		try {
			stream = await navigator.mediaDevices.getUserMedia({
				video: {
					facingMode: 'environment',
					width: { ideal: 1920 },
					height: { ideal: 1080 }
				},
				audio: false
			});
			if (videoEl) videoEl.srcObject = stream;
			return true;
		} catch {
			stopClientCamera();
			return false;
		}
	}

	async function useSource(next: Source) {
		status = '';
		if (next === 'client') {
			const ok = await startClientCamera();
			if (!ok) {
				stopGuidance();
				stopClientCamera();
				source = 'server';
				return;
			}
			source = 'client';
			startGuidance();
		} else {
			stopGuidance();
			stopClientCamera();
			source = 'server';
		}
	}

	function grabClientFrame(maxWidth?: number): Promise<Blob> {
		return new Promise((resolve, reject) => {
			const v = videoEl;
			if (!v || !v.videoWidth || !v.videoHeight) {
				reject(new Error('Camera not ready'));
				return;
			}
			let cw = v.videoWidth;
			let ch = v.videoHeight;
			if (maxWidth && cw > maxWidth) {
				const s = maxWidth / cw;
				cw = Math.round(cw * s);
				ch = Math.round(ch * s);
			}
			const canvas = document.createElement('canvas');
			canvas.width = cw;
			canvas.height = ch;
			const ctx = canvas.getContext('2d');
			if (!ctx) {
				reject(new Error('Canvas unavailable'));
				return;
			}
			ctx.drawImage(v, 0, 0, cw, ch);
			canvas.toBlob(
				(blob) => (blob ? resolve(blob) : reject(new Error('Frame encode failed'))),
				'image/jpeg',
				0.92
			);
		});
	}

	function drawGuidance(g: Guidance) {
		const canvas = canvasEl;
		const v = videoEl;
		if (!canvas || !v || !v.videoWidth) return;
		const boxW = canvas.clientWidth;
		const boxH = canvas.clientHeight;
		if (canvas.width !== boxW) canvas.width = boxW;
		if (canvas.height !== boxH) canvas.height = boxH;
		const ctx = canvas.getContext('2d');
		if (!ctx) return;
		ctx.clearRect(0, 0, boxW, boxH);

		// The video is object-contain inside the box; compute the letterboxed rect
		// so overlay coords land exactly on the displayed image.
		const scale = Math.min(boxW / v.videoWidth, boxH / v.videoHeight);
		const dispW = v.videoWidth * scale;
		const dispH = v.videoHeight * scale;
		const offX = (boxW - dispW) / 2;
		const offY = (boxH - dispH) / 2;

		if (g.corners && g.width && g.height) {
			const sx = dispW / g.width;
			const sy = dispH / g.height;
			ctx.beginPath();
			g.corners.forEach(([x, y], i) => {
				const px = offX + x * sx;
				const py = offY + y * sy;
				if (i) ctx.lineTo(px, py);
				else ctx.moveTo(px, py);
			});
			ctx.closePath();
			ctx.lineWidth = 3;
			ctx.strokeStyle = g.ready ? '#22c55e' : '#f97316';
			ctx.stroke();
		}

		ctx.font = '600 20px system-ui, sans-serif';
		ctx.textBaseline = 'top';
		let ty = offY + 12;
		for (const m of g.messages) {
			ctx.lineWidth = 4;
			ctx.strokeStyle = 'rgba(0,0,0,0.85)';
			ctx.strokeText(m, offX + 14, ty);
			ctx.fillStyle = '#fff';
			ctx.fillText(m, offX + 14, ty);
			ty += 30;
		}
	}

	function clearGuidance() {
		const canvas = canvasEl;
		const ctx = canvas?.getContext('2d');
		if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
	}

	async function guidanceTick() {
		if (!guideRunning || source !== 'client') return;
		try {
			if (videoEl?.videoWidth) {
				const blob = await grabClientFrame(GUIDE_WIDTH);
				const form = new FormData();
				form.append('image', blob, 'frame.jpg');
				const res = await fetch('/api/v1/guidance/analyze', {
					method: 'POST',
					credentials: 'include',
					body: form
				});
				if (res.ok) drawGuidance((await res.json()) as Guidance);
			}
		} catch {
			/* transient frame/network error — keep last overlay, retry next tick */
		}
		if (guideRunning) guideTimer = setTimeout(guidanceTick, GUIDE_INTERVAL_MS);
	}

	function startGuidance() {
		if (guideRunning) return;
		guideRunning = true;
		guideTimer = setTimeout(guidanceTick, GUIDE_INTERVAL_MS);
	}

	function stopGuidance() {
		guideRunning = false;
		if (guideTimer) clearTimeout(guideTimer);
		guideTimer = null;
		clearGuidance();
	}

	async function captureClient(): Promise<PipelineResult> {
		const blob = await grabClientFrame();
		const form = new FormData();
		form.append('image', blob, 'capture.jpg');
		if (selectedCourseId) form.append('course_id', selectedCourseId);
		form.append('visibility', visibility);
		const res = await fetch('/api/v1/upload', {
			method: 'POST',
			credentials: 'include',
			body: form
		});
		if (!res.ok) {
			let detail = res.statusText;
			try {
				detail = (await res.json()).detail ?? detail;
			} catch {
				/* ignore */
			}
			throw new Error(detail);
		}
		return res.json() as Promise<PipelineResult>;
	}

	async function captureServer(): Promise<PipelineResult> {
		const payload: CapturePayload = {
			visibility: visibility as Visibility,
			course_id: selectedCourseId ? Number(selectedCourseId) : null
		};
		return apiPost<PipelineResult>('/api/v1/capture', payload);
	}

	async function capture() {
		capturing = true;
		status = 'Processing...';
		try {
			const res = source === 'client' ? await captureClient() : await captureServer();
			goto(`/lectures/${res.lecture_id}`);
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
		void (async () => {
			await useSource('client');
			initializing = false;
		})();

		const syncFullscreen = () => {
			isFullscreen = document.fullscreenElement === cameraShell;
		};
		document.addEventListener('fullscreenchange', syncFullscreen);
		return () => {
			document.removeEventListener('fullscreenchange', syncFullscreen);
			stopGuidance();
			stopClientCamera();
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
		<!-- Live browser camera. The canvas overlays the guidance (board box +
		     messages) computed by the backend, so the video itself stays smooth. -->
		<!-- svelte-ignore a11y_media_has_caption -->
		<video
			bind:this={videoEl}
			autoplay
			playsinline
			muted
			class="h-full w-full object-contain {source === 'client' ? '' : 'hidden'}"
		></video>
		{#if source === 'client'}
			<canvas
				bind:this={canvasEl}
				class="pointer-events-none absolute inset-0 h-full w-full"
			></canvas>
		{:else if source === 'server'}
			<img src="/api/v1/stream" alt="Live camera preview" class="h-full w-full object-contain" />
		{/if}

		{#if status}
			<span
				class="{overlayPanel} absolute left-3 top-3 z-10 max-w-[calc(100%-5rem)] px-3 py-2 text-sm"
			>
				{status}
			</span>
		{/if}

		<div class="absolute right-3 top-3 z-10 flex items-center gap-2">
			<Button
				variant="icon"
				disabled={initializing || capturing}
				onclick={() => useSource(source === 'client' ? 'server' : 'client')}
				aria-label={source === 'client' ? 'Switch to server camera' : 'Switch to my camera'}
				title={source === 'client' ? 'Using my camera — switch to server/Pi camera' : 'Using server camera — switch to my camera'}
				class="{overlayPanel} !bg-black/55 shadow-none"
			>
				{#snippet icon()}
					<ArrowsClockwise size={22} />
				{/snippet}
			</Button>
			<Button
				variant="icon"
				onclick={toggleFullscreen}
				aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
				class="{overlayPanel} !bg-black/55 shadow-none"
			>
				{#snippet icon()}
					{#if isFullscreen}
						<ArrowsIn size={22} />
					{:else}
						<ArrowsOut size={22} />
					{/if}
				{/snippet}
			</Button>
		</div>

		<div class="absolute bottom-3 right-3 z-10 flex flex-wrap items-end justify-end gap-2">
			<div class="w-40">
				<ComboBox
					bind:value={selectedCourseId}
					placeholder="No course"
					portalTo={cameraShell}
					options={(courses.data ?? []).map((c) => ({
						value: String(c.id),
						label: c.name,
					}))}
				/>
			</div>
			<div class="w-32">
				<ComboBox bind:value={visibility} placeholder="Visibility" portalTo={cameraShell} options={visibilityOptions} />
			</div>
			<Button onclick={capture} disabled={capturing || initializing} class="h-10 px-5 shadow-lg shadow-black/20">
				{#if capturing}
					<CircleNotch size={22} class="animate-spin" />
				{:else}
					<Camera size={22} />
				{/if}
				{capturing ? 'Processing...' : 'Capture'}
			</Button>
		</div>
	</div>
</section>
