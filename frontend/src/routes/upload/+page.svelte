<script lang="ts">
	import { goto } from '$app/navigation';
	import type { PipelineResult } from '$lib/types';
	import { CircleNotch, UploadSimple } from 'phosphor-svelte';

	let file = $state<File | null>(null);
	let error = $state('');
	let status = $state('');
	let busy = $state(false);

	async function onFile(e: Event) {
		const input = e.target as HTMLInputElement;
		const selected = input.files?.[0];
		if (!selected) return;
		file = selected;
		await upload(selected);
		input.value = '';
	}

	async function upload(selected: File) {
		error = '';
		busy = true;
		status = 'Processing...';
		const fd = new FormData();
		fd.append('image', selected);
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

<section class="grid h-[calc(100dvh-8rem)] min-h-[30rem] place-items-stretch md:h-[calc(100dvh-2rem)]">
	<input
		id="board-image"
		type="file"
		accept=".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
		onchange={onFile}
		disabled={busy}
		class="sr-only"
	/>

	<label
		for="board-image"
		class="group grid cursor-pointer place-items-center rounded-lg border border-dashed border-zinc-300 bg-white p-6 text-center shadow-sm transition-all duration-200 hover:border-primary hover:bg-zinc-50 active:scale-[0.995] dark:border-zinc-700 dark:bg-zinc-800 dark:hover:bg-zinc-800/80"
	>
		<span class="grid gap-5 justify-items-center">
			<span class="grid size-24 place-items-center rounded-lg bg-primary text-zinc-50 shadow-lg shadow-primary/20 transition-transform duration-200 group-hover:scale-105">
				{#if busy}
					<CircleNotch size={44} class="animate-spin" />
				{:else}
					<UploadSimple size={44} />
				{/if}
			</span>
			<span class="text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
				{busy ? 'Processing...' : 'Upload board image'}
			</span>
			{#if file || status || error}
				<span class="max-w-xl text-base text-zinc-500 dark:text-zinc-400">
					{error || status || file?.name}
				</span>
			{/if}
		</span>
	</label>
</section>
