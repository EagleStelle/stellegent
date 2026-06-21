<script lang="ts">
	import type { Snippet } from 'svelte';
	import { X } from 'phosphor-svelte';
	import Button from '$lib/components/ui/Button.svelte';

	let {
		open = $bindable(false),
		children,
		label = 'Dialog'
	}: {
		open?: boolean;
		children: Snippet;
		label?: string;
	} = $props();

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') open = false;
	}
</script>

<svelte:window onkeydown={open ? onKey : undefined} />

{#if open}
	<div
		role="dialog"
		aria-modal="true"
		aria-label={label}
		class="dark fixed inset-0 z-50 flex items-center justify-center bg-primary p-4"
	>

		
		{@render children()}

		<Button
			variant="icon"
			type="button"
			onclick={() => (open = false)}
			aria-label="Close dialog"
			class="absolute right-4 top-4 z-10 grid size-10 place-items-center rounded-full !bg-secondary !text-white transition-colors duration-200 hover:!bg-secondary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
		>
			{#snippet icon()}
				<X size={20} />
			{/snippet}
		</Button>
	</div>
{/if}
