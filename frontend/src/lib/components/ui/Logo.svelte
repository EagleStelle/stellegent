<script lang="ts">
	import { base } from '$app/paths';

	let {
		size = 24,
		alt = 'Stellegent logo',
		class: className = ''
	}: { size?: number; alt?: string; class?: string } = $props();
</script>

<img src="{base}/logo.svg" {alt} width={size} height={size} class={className} />
