<script lang="ts" module>
	import { tv, type VariantProps } from 'tailwind-variants';

	export const cardVariants = tv({
		base: 'block rounded-xl border bg-white text-left dark:bg-gray-900',
		variants: {
			variant: {
				default: 'border-gray-200 dark:border-gray-800',
				accent: 'border-gray-200 border-l-4 border-l-secondary dark:border-gray-800 dark:border-l-secondary'
			},
			interactive: {
				true: 'transition-all duration-200 hover:-translate-y-0.5 hover:border-secondary/40 hover:shadow-lg hover:shadow-primary/5 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/25 active:translate-y-0',
				false: ''
			},
			padding: {
				none: '',
				sm: 'p-3',
				default: 'p-4'
			}
		},
		defaultVariants: { variant: 'default', interactive: false, padding: 'default' }
	});

	export type CardVariant = VariantProps<typeof cardVariants>['variant'];
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAnchorAttributes, HTMLAttributes } from 'svelte/elements';
	import { cn } from '$lib/utils';

	type Props = HTMLAnchorAttributes & {
		variant?: CardVariant;
		padding?: 'none' | 'sm' | 'default';
		href?: string;
		children: Snippet;
	};

	let { variant = 'default', padding = 'default', href, class: className, children, ...rest }: Props =
		$props();
</script>

{#if href}
	<a {href} class={cn(cardVariants({ variant, interactive: true, padding }), className)} {...rest}>
		{@render children()}
	</a>
{:else}
	<div
		class={cn(cardVariants({ variant, interactive: false, padding }), className)}
		{...rest as HTMLAttributes<HTMLDivElement>}
	>
		{@render children()}
	</div>
{/if}
