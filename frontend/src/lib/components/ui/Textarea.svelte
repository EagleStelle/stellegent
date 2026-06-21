<script lang="ts">
	import type { HTMLTextareaAttributes } from 'svelte/elements';
	import type { PhosphorIcon } from './Input.svelte';

	type Props = HTMLTextareaAttributes & {
		id: string;
		label?: string;
		value: string;
		icon?: PhosphorIcon;
		error?: boolean;
		class?: string;
	};

	let {
		id,
		label,
		value = $bindable(''),
		icon: Icon,
		error = false,
		class: className = '',
		...rest
	}: Props = $props();
</script>

<div class="flex flex-col space-y-1.5 h-full {className}">
	{#if label}
		<label
			for={id}
			class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400 shrink-0"
		>
			{label}
		</label>
	{/if}
	<div class="group relative flex-1 flex flex-col">
		{#if Icon}
			<Icon
				size={18}
				class="pointer-events-none absolute left-3.5 top-3 text-gray-400 transition-colors group-focus-within:text-secondary"
			/>
		{/if}
		<textarea
			{id}
			{...rest}
			bind:value
			aria-invalid={error ? 'true' : undefined}
			class="w-full flex-1 rounded-lg border border-gray-200 bg-white text-sm text-primary outline-none transition-all duration-200 placeholder:text-gray-400 focus:border-secondary/60 focus:ring-3 focus:ring-secondary/15 aria-invalid:border-red-500 aria-invalid:ring-3 aria-invalid:ring-red-500/15 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-50 dark:placeholder:text-gray-500 {Icon ? 'pl-11' : 'pl-3.5'} pr-3.5 py-2.5 resize-y min-h-[5rem]"
		></textarea>
	</div>
</div>
