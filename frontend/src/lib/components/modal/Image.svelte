<script lang="ts">
	import { Sparkle, ImageSquare } from 'phosphor-svelte';
	import { cn } from '$lib/utils';
	import Modal from '$lib/components/ui/Modal.svelte';

	let {
		src,
		rawSrc = '',
		alt = '',
		class: className = ''
	}: { src: string; rawSrc?: string; alt?: string; class?: string } = $props();

	let open = $state(false);
	let showRaw = $state(false);

	const hasRaw = $derived(!!rawSrc);
	const current = $derived(showRaw && hasRaw ? rawSrc : src);

	const ease = 'transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]';
	const toggleCls =
		'inline-flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1.5 text-xs font-semibold text-white shadow-sm backdrop-blur-sm transition-all duration-200 hover:bg-secondary/90 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/30';
</script>

<div
	role="button"
	tabindex="0"
	onclick={() => (open = true)}
	onkeydown={(e) => e.key === 'Enter' && (open = true)}
	aria-label="Enlarge image"
	class={cn(
		'group relative block cursor-zoom-in overflow-hidden rounded-xl bg-gray-50 object-contain ring-1 ring-gray-900/5 dark:bg-gray-800/50 dark:ring-white/10',
		className
	)}
>
	<img src={current} {alt} class="block h-auto w-full object-contain {ease} group-hover:scale-[1.015]" />
	{#if hasRaw}
		<button
			type="button"
			onclick={(e) => {
				e.stopPropagation();
				showRaw = !showRaw;
			}}
			class="absolute left-3 top-3 {toggleCls}"
			title={showRaw ? 'Show processed image' : 'Show raw image'}
		>
			{#if showRaw}
				<ImageSquare size={14} /> Raw
			{:else}
				<Sparkle size={14} /> Processed
			{/if}
		</button>
	{/if}
</div>

<Modal bind:open label={alt || 'Image preview'}>
	<div class="relative flex h-full w-full items-center justify-center p-4">
		<img src={current} {alt} class="max-h-[calc(100dvh-2rem)] max-w-[calc(100vw-2rem)] rounded-xl object-contain shadow-2xl" />
		{#if hasRaw}
			<button
				type="button"
				onclick={() => (showRaw = !showRaw)}
				class="absolute left-3 top-3 {toggleCls}"
				title={showRaw ? 'Show processed image' : 'Show raw image'}
			>
				{#if showRaw}
					<ImageSquare size={14} /> Raw
				{:else}
					<Sparkle size={14} /> Processed
				{/if}
			</button>
		{/if}
	</div>
</Modal>
