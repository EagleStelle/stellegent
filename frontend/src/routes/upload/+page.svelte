<script lang="ts">
	import { goto } from '$app/navigation';
	import type { PipelineResult } from '$lib/types';
	import { UploadSimple, CircleNotch } from 'phosphor-svelte';

	let file = $state<File | null>(null);
	let course = $state('');
	let error = $state('');
	let status = $state('');
	let busy = $state(false);

	function onFile(e: Event) {
		const input = e.target as HTMLInputElement;
		file = input.files?.[0] ?? null;
	}

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		if (!file) {
			error = 'Choose an image';
			return;
		}
		error = '';
		busy = true;
		status = 'Uploading and processing...';
		const fd = new FormData();
		fd.append('image', file);
		if (course.trim()) fd.append('course', course.trim());
		try {
			const res = await fetch('/api/v1/upload', {
				method: 'POST',
				credentials: 'include',
				body: fd
			});
			if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
			const data: PipelineResult = await res.json();
			goto(`/lecture/${data.lecture_id}`);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Upload failed';
			busy = false;
			status = '';
		}
	}
</script>

<section class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
	<div class="space-y-2">
		<p class="text-sm font-medium text-primary">Upload</p>
		<h1 class="text-3xl font-semibold tracking-tight text-balance">Process a board image</h1>
		<p class="max-w-2xl text-sm leading-6 text-muted-foreground">
			Add a whiteboard photo and Stellegent will extract text, clean it up, summarize it, and save the lecture.
		</p>
	</div>

	<div
		class="flex flex-col gap-5 overflow-hidden rounded-[min(var(--radius-4xl),24px)] bg-card py-5 text-sm text-card-foreground shadow-sm ring-1 ring-foreground/5 lg:row-span-2 dark:ring-foreground/10"
	>
		<div class="grid auto-rows-min items-start gap-1.5 px-5">
			<div class="text-base font-medium">Image details</div>
			<p class="text-sm text-muted-foreground">PNG, JPG, WebP, BMP, or TIFF files work best.</p>
		</div>
		<div class="px-5">
			<form id="upload-form" onsubmit={submit} class="space-y-4">
				<div class="grid gap-2">
					<label
						for="board-image"
						class="flex items-center gap-2 text-sm font-medium leading-none select-none"
					>
						Board image
					</label>
					<input
						id="board-image"
						type="file"
						accept=".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
						onchange={onFile}
						aria-invalid={error && !file ? 'true' : undefined}
						class="h-8 w-full min-w-0 rounded-2xl border border-transparent bg-input/50 px-2.5 py-1 text-base outline-none transition-[color,box-shadow] duration-200 file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
					/>
				</div>
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
						placeholder="Optional, e.g. CS101"
						class="h-8 w-full min-w-0 rounded-2xl border border-transparent bg-input/50 px-2.5 py-1 text-base outline-none transition-[color,box-shadow] duration-200 placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
					/>
				</div>
				{#if file}
					<span
						class="inline-flex h-5 w-fit max-w-full shrink-0 items-center justify-center gap-1 truncate rounded-2xl border border-transparent bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground"
					>
						{file.name}
					</span>
				{/if}
				{#if error}
					<p class="rounded-2xl bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
						{error}
					</p>
				{/if}
				{#if status}
					<p class="rounded-2xl bg-muted px-3 py-2 text-sm text-muted-foreground">{status}</p>
				{/if}
			</form>
		</div>
		<div class="flex items-center px-5">
			<button
				type="submit"
				form="upload-form"
				disabled={busy}
				class="inline-flex h-8 w-full shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-2xl border border-transparent bg-primary px-3 text-sm font-medium text-primary-foreground outline-none transition-all hover:bg-primary/80 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 disabled:pointer-events-none disabled:opacity-50"
			>
				{#if busy}
					<CircleNotch size={16} class="animate-spin" />
				{:else}
					<UploadSimple size={16} />
				{/if}
				{busy ? 'Processing...' : 'Process image'}
			</button>
		</div>
	</div>

	<div
		class="flex flex-col gap-5 overflow-hidden rounded-[min(var(--radius-4xl),24px)] border border-dashed border-border/80 bg-card/70 py-5 text-sm text-card-foreground shadow-sm ring-1 ring-foreground/5 lg:col-start-1 dark:ring-foreground/10"
	>
		<div class="px-5 py-8">
			<div class="grid gap-3 sm:grid-cols-3">
				<div>
					<p class="text-sm font-medium">1. Upload</p>
					<p class="mt-1 text-sm leading-6 text-muted-foreground">Send a clear photo of the board.</p>
				</div>
				<div>
					<p class="text-sm font-medium">2. Extract</p>
					<p class="mt-1 text-sm leading-6 text-muted-foreground">OCR and cleanup run in the backend.</p>
				</div>
				<div>
					<p class="text-sm font-medium">3. Review</p>
					<p class="mt-1 text-sm leading-6 text-muted-foreground">Open the generated lecture record.</p>
				</div>
			</div>
		</div>
	</div>
</section>
