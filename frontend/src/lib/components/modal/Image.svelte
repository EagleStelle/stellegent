<script lang="ts">
	import { MagnifyingGlassPlus } from 'phosphor-svelte';
	import { cn } from '$lib/utils';
	import Modal from '$lib/components/ui/Modal.svelte';

	let {
		src,
		alt = '',
		class: className = ''
	}: { src: string; alt?: string; class?: string } = $props();

	let open = $state(false);

	const ease = 'transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]';
</script>

<div
	role="button"
	tabindex="0"
	onclick={() => (open = true)}
	onkeydown={(e) => e.key === 'Enter' && (open = true)}
	aria-label="Enlarge image"
	class={cn('group relative block cursor-zoom-in overflow-hidden', className)}
>
	<img {src} {alt} class="block h-auto w-full object-contain {ease} group-hover:scale-[1.015]" />
	<span
		class="pointer-events-none absolute bottom-3 right-3 grid size-9 place-items-center rounded-full bg-primary/70 text-white opacity-0 backdrop-blur-sm {ease} group-hover:opacity-100"
	>
		<MagnifyingGlassPlus size={18} />
	</span>
</div>

<Modal bind:open label={alt || 'Image preview'}>
	<img {src} {alt} class="relative max-h-full max-w-full rounded-xl object-contain shadow-2xl" />
</Modal>
