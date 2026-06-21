<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { apiGet, apiPost } from '$lib/api/client';
	import type { LectureDetail, User } from '$lib/types';
	import { DownloadSimple, Trash, ChatText } from 'phosphor-svelte';

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

	function formatDate(value: string) {
		return new Date(value).toLocaleString(undefined, {
			weekday: 'short',
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit'
		});
	}

	const cardRoot =
		'flex flex-col gap-5 overflow-hidden rounded-[min(var(--radius-4xl),24px)] bg-white dark:bg-zinc-800 py-5 text-sm text-zinc-900 dark:text-zinc-50 shadow-sm ring-1 ring-zinc-900/5 dark:ring-zinc-50/10';
</script>

{#if lecture.isLoading}
	<section class="space-y-5">
		<div class="space-y-2">
			<div class="h-4 w-28 animate-pulse rounded-2xl bg-zinc-100 dark:bg-zinc-700"></div>
			<div class="h-9 w-72 max-w-full animate-pulse rounded-2xl bg-zinc-100 dark:bg-zinc-700"></div>
			<div class="h-4 w-48 animate-pulse rounded-2xl bg-zinc-100 dark:bg-zinc-700"></div>
		</div>
		<div class="aspect-video w-full animate-pulse rounded-[min(var(--radius-4xl),24px)] bg-zinc-100 dark:bg-zinc-700"></div>
		<div class="grid gap-4 lg:grid-cols-2">
			<div class="h-44 animate-pulse rounded-[min(var(--radius-4xl),24px)] bg-zinc-100 dark:bg-zinc-700"></div>
			<div class="h-44 animate-pulse rounded-[min(var(--radius-4xl),24px)] bg-zinc-100 dark:bg-zinc-700"></div>
		</div>
	</section>
{:else if lecture.isError}
	<div class="{cardRoot} border border-dashed border-zinc-200/80 dark:border-zinc-700/80 bg-white/70 dark:bg-zinc-800/70">
		<div class="px-5 py-12 text-center">
			<h1 class="text-lg font-medium">Lecture not found</h1>
			<p class="mt-2 text-sm text-zinc-500 dark:text-zinc-400">The lecture may have been removed.</p>
			<a
				href="/"
				class="mt-5 inline-flex h-8 shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-2xl border border-transparent bg-zinc-100 dark:bg-zinc-700 px-3 text-sm font-medium text-zinc-900 dark:text-zinc-50 outline-none transition-all hover:bg-zinc-200 dark:hover:bg-zinc-600 focus-visible:border-secondary focus-visible:ring-3 focus-visible:ring-secondary/30"
			>
				Back to lectures
			</a>
		</div>
	</div>
{:else if lecture.data}
	{@const lec = lecture.data}
	<section class="space-y-5">
		<div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
			<div class="space-y-2">
				<span
					class="inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden whitespace-nowrap rounded-2xl border border-transparent bg-zinc-100 dark:bg-zinc-700 px-2 py-0.5 text-xs font-medium text-zinc-900 dark:text-zinc-50"
				>
					{formatDate(lec.captured_at)}
				</span>
				<h1 class="text-3xl font-semibold tracking-tight text-balance">
					{lec.course_name ?? 'Lecture'}
				</h1>
				<p class="max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
					Review the board image, generated summary, transcript, and class notes.
				</p>
			</div>
			{#if canManage}
				<button
					onclick={remove}
					class="inline-flex h-7 shrink-0 items-center justify-center gap-1 whitespace-nowrap rounded-2xl border border-transparent bg-red-600/10 px-3 text-sm font-medium text-red-600 outline-none transition-all hover:bg-red-600/20 focus-visible:ring-3 focus-visible:ring-red-600/20 dark:text-red-400 dark:hover:bg-red-500/20"
				>
					<Trash size={16} />
					Delete
				</button>
			{/if}
		</div>

		<div
			class="overflow-hidden rounded-[min(var(--radius-4xl),24px)] border border-zinc-200/70 dark:border-zinc-700/70 bg-white dark:bg-zinc-800 shadow-xl shadow-primary/10"
		>
			<img
				src={fileUrl('image')}
				alt={`Board capture for ${lec.course_name ?? 'lecture'}`}
				class="w-full"
			/>
		</div>

		<div class="flex flex-wrap gap-2">
			{#each ['pdf', 'docx', 'txt', 'manifest'] as type}
				<a
					href={fileUrl(type)}
					class="inline-flex h-7 shrink-0 items-center justify-center gap-1 whitespace-nowrap rounded-2xl border border-zinc-200 bg-zinc-50 px-3 text-sm font-medium outline-none transition-all hover:bg-zinc-100 hover:text-zinc-900 focus-visible:border-secondary focus-visible:ring-3 focus-visible:ring-secondary/30 dark:border-zinc-700 dark:bg-transparent dark:text-zinc-50 dark:hover:bg-zinc-700/30"
				>
					<DownloadSimple size={16} />
					{type === 'manifest' ? 'JSON' : type.toUpperCase()}
				</a>
			{/each}
		</div>

		<div class="grid gap-4 lg:grid-cols-2">
			<div class={cardRoot}>
				<div class="grid auto-rows-min items-start gap-1.5 px-5">
					<div class="text-base font-medium">Summary</div>
					<p class="text-sm text-zinc-500 dark:text-zinc-400">Condensed notes generated from the board capture.</p>
				</div>
				<div class="px-5">
					<pre class="whitespace-pre-wrap rounded-3xl bg-zinc-100/70 dark:bg-zinc-700/70 p-4 text-sm leading-6">{lec.summary ??
							'No summary available.'}</pre>
				</div>
			</div>

			<div class={cardRoot}>
				<div class="grid auto-rows-min items-start gap-1.5 px-5">
					<div class="text-base font-medium">Corrected transcript</div>
					<p class="text-sm text-zinc-500 dark:text-zinc-400">Cleaned OCR text used to build the summary.</p>
				</div>
				<div class="px-5">
					<pre
						class="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-3xl bg-zinc-100/70 dark:bg-zinc-700/70 p-4 text-sm leading-6">{lec.corrected_text ??
							'No corrected transcript available.'}</pre>
				</div>
			</div>
		</div>

		<div class={cardRoot}>
			<div class="grid auto-rows-min items-start gap-1.5 px-5">
				<div class="text-base font-medium">Notes</div>
				<p class="text-sm text-zinc-500 dark:text-zinc-400">Shared annotations for this lecture.</p>
			</div>
			<div class="space-y-4 px-5">
				{#if lec.annotations.length}
					<div class="space-y-3">
						{#each lec.annotations as a (a.id)}
							<article class="rounded-3xl bg-zinc-100/70 dark:bg-zinc-700/70 p-3 text-sm">
								<div class="flex flex-wrap items-center gap-2">
									<span class="font-medium">{a.username ?? 'User'}</span>
									<span class="text-zinc-500 dark:text-zinc-400">{formatDate(a.created_at)}</span>
								</div>
								<p class="mt-2 leading-6">{a.note_text}</p>
							</article>
						{/each}
					</div>
					<div class="h-px w-full shrink-0 bg-zinc-200 dark:bg-zinc-700"></div>
				{:else}
					<div class="flex items-center gap-3 rounded-3xl bg-zinc-100/70 dark:bg-zinc-700/70 p-4">
						<span
							class="grid size-10 place-items-center rounded-2xl bg-zinc-50 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400"
						>
							<ChatText size={20} />
						</span>
						<p class="text-sm text-zinc-500 dark:text-zinc-400">No notes have been added yet.</p>
					</div>
				{/if}

				<form onsubmit={addNote} class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
					<textarea
						bind:value={note}
						placeholder="Add a note"
						class="flex field-sizing-content min-h-20 w-full resize-none rounded-2xl border border-transparent bg-zinc-200/50 dark:bg-zinc-700/50 px-2.5 py-2 text-base outline-none transition-[color,box-shadow] duration-200 placeholder:text-zinc-500 dark:placeholder:text-zinc-400 focus-visible:border-secondary focus-visible:ring-3 focus-visible:ring-secondary/30 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
					></textarea>
					<button
						type="submit"
						disabled={!note.trim()}
						class="inline-flex h-8 shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-2xl border border-transparent bg-primary px-3 text-sm font-medium text-zinc-50 outline-none transition-all hover:bg-primary/80 focus-visible:border-secondary focus-visible:ring-3 focus-visible:ring-secondary/30 disabled:pointer-events-none disabled:opacity-50"
					>
						Add note
					</button>
				</form>
			</div>
		</div>
	</section>
{/if}
