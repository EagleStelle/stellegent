<script lang="ts" module>
	import type { Component } from 'svelte';

	type IconWeight = 'thin' | 'light' | 'regular' | 'bold' | 'fill' | 'duotone';

	export type PhosphorIcon = Component<{
		size?: number | string;
		weight?: IconWeight;
		color?: string;
		mirrored?: boolean;
		class?: string;
	}>;
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLInputAttributes } from 'svelte/elements';

	type Props = HTMLInputAttributes & {
		id: string;
		label?: string;
		value: string;
		icon?: PhosphorIcon;
		error?: boolean;
		trailing?: Snippet;
	};

	let {
		id,
		label,
		value = $bindable(''),
		icon: Icon,
		error = false,
		trailing,
		type = 'text',
		...rest
	}: Props = $props();
</script>

<div class="space-y-1.5">
	{#if label}
		<label
			for={id}
			class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400"
		>
			{label}
		</label>
	{/if}
	<div class="group relative">
		{#if Icon}
			<Icon
				size={18}
				class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 transition-colors group-focus-within:text-secondary"
			/>
		{/if}
		<input
			{id}
			{...rest}
			{type}
			bind:value
			aria-invalid={error ? 'true' : undefined}
			class="h-11 w-full rounded-lg border border-gray-200 bg-white text-base text-primary outline-none transition-all duration-200 md:h-14 md:text-lg placeholder:text-gray-400 focus:border-secondary/60 focus:ring-4 focus:ring-secondary/15 aria-invalid:border-red-500 aria-invalid:ring-4 aria-invalid:ring-red-500/15 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-50 dark:placeholder:text-gray-500 {Icon
				? 'pl-11'
				: 'pl-3.5'} {trailing ? 'pr-11' : 'pr-3.5'}"
		/>
		{#if trailing}
			{@render trailing()}
		{/if}
	</div>
</div>
