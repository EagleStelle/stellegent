<script lang="ts">
	import { Button } from "bits-ui";
	import type { Snippet } from "svelte";
	import type { HTMLButtonAttributes } from "svelte/elements";
	import { cn } from "$lib/utils";

	type Variant = "text" | "icon" | "icon+text";

	type Props = HTMLButtonAttributes & {
		variant?: Variant;
		ghost?: boolean;
		danger?: boolean;
		secondary?: boolean;
		icon?: Snippet;
		children?: Snippet;
	};

	let {
		variant = "text",
		ghost = false,
		danger = false,
		secondary = false,
		class: className,
		icon,
		children,
		...rest
	}: Props = $props();

	const tone = $derived(
		ghost
			? danger
				? "bg-transparent text-red-600 hover:bg-red-500/10"
				: secondary
					? "bg-transparent text-primary hover:bg-primary/10"
					: "bg-transparent text-secondary hover:bg-secondary/10"
			: secondary
				? "bg-white text-primary border border-primary/20 shadow-sm hover:bg-primary/5"
			: danger
				? "bg-red-600 text-white shadow-sm hover:bg-red-600/90"
				: "bg-secondary text-white shadow-sm hover:bg-secondary/90",
	);
</script>

<Button.Root
	class={cn(
		"inline-flex shrink-0 items-center justify-center rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/30 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-60",
			tone,
			variant === "icon" 
				? (ghost ? "h-8 w-8" : "h-10 w-10") 
				: (ghost ? "h-8 px-3" : "h-10 px-3.5"),
		variant === "icon+text" ? "gap-2" : "",
		className,
	)}
	{...rest}
>
	{#if variant === "icon"}
		{@render icon?.()}
	{:else if variant === "icon+text"}
		{#if icon}
			{@render icon()}
		{/if}
		{#if children}
			<span class="truncate">{@render children()}</span>
		{/if}
	{:else}
		{#if children}
			{@render children()}
		{/if}
	{/if}
</Button.Root>
