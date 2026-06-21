<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import {
		createMutation,
		createQuery,
		useQueryClient,
	} from "@tanstack/svelte-query";
	import { apiGet, apiPost } from "$lib/api/client";
	import type { LectureDetail, User } from "$lib/types";
	import { ArrowLeft, Sparkle, CircleNotch } from "phosphor-svelte";
	import Button from "$lib/components/ui/Button.svelte";

	const qc = useQueryClient();
	const id = $derived(page.params.id);

	const me = createQuery(() => ({
		queryKey: ["me"],
		queryFn: () => apiGet<User>("/api/v1/me"),
	}));
	const lecture = createQuery(() => ({
		queryKey: ["lecture", id],
		queryFn: () => apiGet<LectureDetail>(`/api/v1/lectures/${id}`),
	}));

	const canManage = $derived(
		me.data?.role === "admin" ||
			(me.data?.role === "prof" &&
				lecture.data?.owner_user_id === me.data.uid),
	);

	const generateSummary = createMutation(() => ({
		mutationFn: () =>
			apiPost<LectureDetail>(`/api/v1/lectures/${id}/summarize`),
		onSuccess: (data) => {
			qc.setQueryData(["lecture", id], data);
		},
	}));

	const body = $derived(
		lecture.data?.summary?.trim()
			? lecture.data.summary
			: "No summary yet.",
	);
</script>

{#if lecture.data}
	<div class="relative flex h-[calc(100dvh-2rem)] max-h-[calc(100dvh-2rem)] flex-col">
		<header
			class="shrink-0 flex items-center gap-4 border-b border-gray-200 pb-2 dark:border-gray-800"
		>
			<Button
				variant="icon"
				ghost
				onclick={() => goto(`/lectures/${id}`)}
				title="Back to lecture"
			>
				{#snippet icon()}
					<ArrowLeft size={20} />
				{/snippet}
			</Button>
			<div>
				<h1
					class="text-2xl font-bold tracking-tight text-primary dark:text-gray-50"
				>
					Summary
				</h1>
			</div>
			{#if canManage}
				<Button
					variant="icon+text"
					class="ml-auto"
					onclick={() => generateSummary.mutate()}
					disabled={generateSummary.isPending}
					title="Generate summary"
				>
					{#snippet icon()}
						{#if generateSummary.isPending}
							<CircleNotch size={16} class="animate-spin" />
						{:else}
							<Sparkle size={16} />
						{/if}
					{/snippet}
					{generateSummary.isPending ? "Generating…" : "Generate"}
				</Button>
			{/if}
		</header>

		<div class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto py-4 pr-2">
			{#each body.split('\n') as line}
				{#if line.trim().startsWith('- ')}
					<div class="flex items-start gap-3">
						<div class="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-secondary"></div>
						<p class="text-base leading-relaxed text-gray-700 dark:text-gray-300">
							{line.replace(/^- /, '').trim()}
						</p>
					</div>
				{:else if line.trim() !== ''}
					<p class="text-base leading-relaxed text-gray-700 dark:text-gray-300">
						{line}
					</p>
				{/if}
			{/each}
		</div>
	</div>
{/if}
