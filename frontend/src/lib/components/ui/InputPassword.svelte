<script lang="ts">
	import type { ComponentProps } from 'svelte';
	import { Eye, EyeSlash } from 'phosphor-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from './Input.svelte';

	type Props = Omit<ComponentProps<typeof Input>, 'type' | 'trailing'>;

	let { value = $bindable(''), ...rest }: Props = $props();

	let show = $state(false);
</script>

<Input {...rest} bind:value type={show ? 'text' : 'password'}>
	{#snippet trailing()}
		<Button
			variant="icon"
			type="button"
			onclick={() => (show = !show)}
			aria-label={show ? 'Hide password' : 'Show password'}
			class="absolute right-2 top-1/2 grid size-7 -translate-y-1/2 place-items-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-primary dark:hover:bg-gray-800 dark:hover:text-gray-200 !bg-transparent !shadow-none !h-7 !w-7"
		>
			{#snippet icon()}
				{#if show}
					<EyeSlash size={17} />
				{:else}
					<Eye size={17} />
				{/if}
			{/snippet}
		</Button>
	{/snippet}
</Input>
