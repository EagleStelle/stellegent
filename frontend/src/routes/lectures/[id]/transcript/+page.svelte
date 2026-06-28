<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import { createQuery } from "@tanstack/svelte-query";
	import { apiGet } from "$lib/api/client";
	import type { LectureDetail } from "$lib/types";
	import { ArrowLeft } from "phosphor-svelte";
	import Button from "$lib/components/ui/Button.svelte";

	const id = $derived(page.params.id);

	const lecture = createQuery(() => ({
		queryKey: ["lecture", id],
		queryFn: () => apiGet<LectureDetail>(`/api/v1/lectures/${id}`),
	}));

	const body = $derived(
		lecture.data?.raw_ocr_text?.trim()
			? lecture.data.raw_ocr_text
			: "No OCR text yet.",
	);
</script>

{#if lecture.data}
	<div
		class="relative flex h-[calc(100dvh-7rem)] max-h-[calc(100dvh-7rem)] flex-col gap-4 md:h-[calc(100dvh-2rem)] md:max-h-[calc(100dvh-2rem)]"
	>
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
					OCR
				</h1>
			</div>
		</header>

		<div class="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto pr-2">
			<p
				class="whitespace-pre-wrap text-base leading-relaxed text-gray-700 dark:text-gray-300"
			>
				{body}
			</p>
		</div>
	</div>
{/if}
