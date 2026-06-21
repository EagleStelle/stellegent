<script lang="ts">
	import { ArrowsOutSimple } from "phosphor-svelte";
	import { cardVariants } from "$lib/components/ui/Card.svelte";
	import { cn } from "$lib/utils";
	import Modal from "$lib/components/ui/Modal.svelte";

	let {
		title,
		text,
		fallback = "Nothing here yet.",
		lines = 4,
	}: {
		title: string;
		text?: string | null;
		fallback?: string;
		lines?: number;
	} = $props();

	let open = $state(false);
	const body = $derived(text?.trim() ? text : fallback);
</script>

<button
	type="button"
	onclick={() => (open = true)}
	class={cn(
		cardVariants({ interactive: true }),
		"group flex w-full flex-col gap-2",
	)}
>
	<div class="flex w-full items-center justify-between gap-2">
		<h2
			class="text-sm font-semibold text-primary transition-colors group-hover:text-secondary dark:text-gray-50"
		>
			{title}
		</h2>
		<ArrowsOutSimple
			size={16}
			class="shrink-0 text-gray-400 transition-colors duration-200 group-hover:text-secondary"
		/>
	</div>
	<p
		class="whitespace-pre-wrap text-sm leading-6 text-gray-600 dark:text-gray-300"
		style="display:-webkit-box;-webkit-line-clamp:{lines};-webkit-box-orient:vertical;overflow:hidden;"
	>
		{body}
	</p>
</button>

<Modal bind:open label={title}>
	<div class="relative flex h-full w-full max-w-5xl flex-col">
		<h2
			class="mb-6 mt-1 text-2xl font-bold text-white shadow-black drop-shadow-md pr-12"
		>
			{title}
		</h2>
		<div class="overflow-y-auto pr-4">
			<p
				class="whitespace-pre-wrap text-base leading-relaxed text-gray-100 drop-shadow-sm"
			>
				{body}
			</p>
		</div>
	</div>
</Modal>
