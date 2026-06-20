<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { apiGet, apiPost } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import type { LectureDetail, User } from '$lib/types';

	const qc = useQueryClient();
	const id = $derived(page.params.id);

	const me = createQuery(() => ({ queryKey: ['me'], queryFn: () => apiGet<User>('/api/v1/me') }));
	const lecture = createQuery(() => ({
		queryKey: ['lecture', id],
		queryFn: () => apiGet<LectureDetail>(`/api/v1/lectures/${id}`)
	}));

	let note = $state('');
	const canManage = $derived(me.data?.role === 'prof' || me.data?.role === 'admin');

	async function addNote(e: SubmitEvent) {
		e.preventDefault();
		if (!note.trim()) return;
		await apiPost(`/api/v1/lectures/${id}/annotate`, { note });
		note = '';
		qc.invalidateQueries({ queryKey: ['lecture', id] });
	}

	async function remove() {
		if (!confirm('Delete this lecture?')) return;
		await fetch(`/api/v1/lectures/${id}`, { method: 'DELETE', credentials: 'include' });
		qc.invalidateQueries({ queryKey: ['lectures'] });
		goto('/');
	}

	const fileUrl = (type: string) => `/api/v1/lectures/${id}/file?type=${type}`;
</script>

{#if lecture.isLoading}
	<p class="text-muted-foreground">Loading…</p>
{:else if lecture.isError}
	<p class="text-destructive">Not found.</p>
{:else if lecture.data}
	{@const lec = lecture.data}
	<div class="mb-6 flex items-start justify-between">
		<div>
			<h1 class="text-2xl font-semibold">{lec.course_name ?? 'Lecture'}</h1>
			<p class="text-sm text-muted-foreground">{new Date(lec.captured_at).toLocaleString()}</p>
		</div>
		{#if canManage}
			<Button variant="destructive" size="sm" onclick={remove}>Delete</Button>
		{/if}
	</div>

	<img src={fileUrl('image')} alt="board" class="mb-6 w-full rounded-lg border border-border" />

	<div class="mb-6 flex flex-wrap gap-2 text-sm">
		<a href={fileUrl('pdf')} class="rounded-md border border-input px-3 py-1 hover:bg-secondary">PDF</a>
		<a href={fileUrl('docx')} class="rounded-md border border-input px-3 py-1 hover:bg-secondary">DOCX</a>
		<a href={fileUrl('txt')} class="rounded-md border border-input px-3 py-1 hover:bg-secondary">TXT</a>
		<a href={fileUrl('manifest')} class="rounded-md border border-input px-3 py-1 hover:bg-secondary">JSON</a>
	</div>

	<section class="mb-6">
		<h2 class="mb-2 text-lg font-medium">Summary</h2>
		<pre class="whitespace-pre-wrap rounded-lg bg-secondary p-4 text-sm">{lec.summary ?? ''}</pre>
	</section>

	<section class="mb-6">
		<h2 class="mb-2 text-lg font-medium">Corrected transcript</h2>
		<pre class="whitespace-pre-wrap rounded-lg bg-secondary p-4 text-sm">{lec.corrected_text ?? ''}</pre>
	</section>

	<section>
		<h2 class="mb-2 text-lg font-medium">Notes</h2>
		<div class="mb-3 space-y-2">
			{#each lec.annotations as a (a.id)}
				<div class="rounded-md border border-border p-3 text-sm">
					<span class="font-medium">{a.username ?? 'user'}</span>
					<span class="text-muted-foreground"> · {new Date(a.created_at).toLocaleString()}</span>
					<p class="mt-1">{a.note_text}</p>
				</div>
			{/each}
		</div>
		<form onsubmit={addNote} class="flex gap-2">
			<input
				bind:value={note}
				placeholder="Add a note…"
				class="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
			/>
			<Button type="submit">Add</Button>
		</form>
	</section>
{/if}
