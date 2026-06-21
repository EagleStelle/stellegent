<script lang="ts" module>
	import { tv, type VariantProps } from 'tailwind-variants';

	export const cardVariants = tv({
		base: 'block rounded-xl border border-gray-200 bg-white text-left dark:border-gray-800 dark:bg-gray-900',
		variants: {
			interactive: {
				true: 'transition-all duration-200 hover:-translate-y-0.5 hover:border-secondary hover:shadow-lg hover:shadow-primary/5 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/25 active:translate-y-0',
				false: ''
			},
			padding: {
				none: '',
				sm: 'p-3',
				default: 'p-4'
			}
		},
		defaultVariants: { interactive: false, padding: 'default' }
	});
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAnchorAttributes, HTMLAttributes, HTMLButtonAttributes } from 'svelte/elements';
	import { cn } from '$lib/utils';

	type CardAttributes = HTMLAnchorAttributes & HTMLButtonAttributes & HTMLAttributes<HTMLDivElement>;

	type Props = Omit<CardAttributes, 'onkeydown'> & {
		padding?: 'none' | 'sm' | 'default';
		href?: string;
		as?: 'button' | 'div';
		onclick?: (e: MouseEvent) => void;
		onkeydown?: (e: KeyboardEvent) => void;
		children: Snippet;
	};

	let { padding = 'default', href, as = 'button', onclick, onkeydown, tabindex, class: className, children, ...rest }: Props =
		$props();

	function handleDivKeydown(event: KeyboardEvent) {
		onkeydown?.(event);
		if (event.defaultPrevented) return;
		if (event.target !== event.currentTarget) return;
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			(event.currentTarget as HTMLElement).click();
		}
	}
</script>

{#if href}
	<a {href} {onclick} {tabindex} class={cn(cardVariants({ interactive: true, padding }), className)} {...rest as HTMLAnchorAttributes}>
		{@render children()}
	</a>
{:else if onclick && as === 'div'}
	<div
		role="button"
		tabindex={tabindex ?? 0}
		{onclick}
		onkeydown={handleDivKeydown}
		class={cn(cardVariants({ interactive: true, padding }), className)}
		{...rest as HTMLAttributes<HTMLDivElement>}
	>
		{@render children()}
	</div>
{:else if onclick}
	<button {onclick} {tabindex} class={cn(cardVariants({ interactive: true, padding }), className)} {...rest as HTMLButtonAttributes}>
		{@render children()}
	</button>
{:else}
	<div
		class={cn(cardVariants({ interactive: false, padding }), className)}
		{...rest as HTMLAttributes<HTMLDivElement>}
	>
		{@render children()}
	</div>
{/if}
