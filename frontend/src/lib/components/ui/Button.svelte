<script lang="ts" module>
	import { tv, type VariantProps } from 'tailwind-variants';

	export const buttonVariants = tv({
		base: 'inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary disabled:pointer-events-none disabled:opacity-50',
		variants: {
			variant: {
				default: 'bg-primary text-zinc-50 hover:bg-primary/90',
				destructive: 'bg-red-600 text-zinc-50 hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600',
				outline: 'border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-700',
				secondary: 'bg-secondary text-zinc-900 hover:bg-secondary/90',
				ghost: 'hover:bg-zinc-100 dark:hover:bg-zinc-700'
			},
			size: {
				default: 'h-10 px-4',
				sm: 'h-9 px-3',
				lg: 'h-11 px-6',
				icon: 'h-10 w-10'
			}
		},
		defaultVariants: { variant: 'default', size: 'default' }
	});

	export type ButtonVariant = VariantProps<typeof buttonVariants>['variant'];
	export type ButtonSize = VariantProps<typeof buttonVariants>['size'];
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';
	import { cn } from '$lib/utils';

	type Props = HTMLButtonAttributes & {
		variant?: ButtonVariant;
		size?: ButtonSize;
		children: Snippet;
	};

	let { variant = 'default', size = 'default', class: className, children, ...rest }: Props =
		$props();
</script>

<button class={cn(buttonVariants({ variant, size }), className)} {...rest}>
	{@render children()}
</button>
