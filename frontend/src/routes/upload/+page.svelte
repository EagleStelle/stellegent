<script lang="ts">
	import { goto } from '$app/navigation';
	import Button from '$lib/components/ui/Button.svelte';
	import type { PipelineResult } from '$lib/types';

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
			error = 'choose an image';
			return;
		}
		error = '';
		busy = true;
		status = 'Uploading + processing…';
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
			error = err instanceof Error ? err.message : 'upload failed';
			busy = false;
			status = '';
		}
	}
</script>

<h1 class="mb-6 text-2xl font-semibold">Upload whiteboard image</h1>
<form onsubmit={submit} class="max-w-md space-y-4">
	<input
		type="file"
		accept=".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
		onchange={onFile}
		class="block w-full text-sm"
	/>
	<input
		bind:value={course}
		placeholder="Course (optional, e.g. CS101)"
		class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
	/>
	{#if error}<p class="text-sm text-destructive">{error}</p>{/if}
	{#if status}<p class="text-sm text-muted-foreground">{status}</p>{/if}
	<Button type="submit" disabled={busy}>{busy ? 'Processing…' : 'Process'}</Button>
</form>
