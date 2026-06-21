<script lang="ts">
	import { Button } from "bits-ui";
	import type { Snippet } from "svelte";
	import { cn } from "$lib/utils";

	type Variant = "text" | "icon" | "icon+text";

	type Props = Button.RootProps & {
		variant?: Variant;
		ghost?: boolean;
		danger?: boolean;
		secondary?: boolean;
		nav?: boolean;
		active?: boolean;
		icon?: Snippet;
	};

	let {
		variant = "text",
		ghost = false,
		danger = false,
		secondary = false,
		nav = false,
		active = false,
		class: className,
		icon,
		children,
		...rest
	}: Props = $props();

	const tone = $derived.by(() => {
		if (nav) {
			if (danger)
				return "bg-transparent text-red-400 hover:bg-red-500/10 hover:text-red-300";
			if (active)
				return "bg-secondary text-white shadow-sm";
			return "bg-transparent text-gray-300 hover:bg-white/10 hover:text-white";
		}

		if (ghost) {
			if (danger)
				return "bg-transparent text-red-500 hover:bg-red-500/10";
			return "bg-transparent text-secondary hover:bg-secondary/10";
		}

		if (danger)
			return "bg-red-600 text-white shadow-sm hover:bg-red-600/90";

		if (secondary) {
			return "bg-primary text-white shadow-sm hover:bg-primary/90";
		}
		return "bg-secondary text-white shadow-sm hover:bg-secondary/90";
	});
</script>

<Button.Root
	class={cn(
		"inline-flex shrink-0 items-center justify-center rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/30 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-60",
		tone,
		nav
			? "h-auto w-full justify-start gap-3 px-3.5 py-2.5"
			: variant === "icon"
				? ghost
					? "h-8 w-8"
					: "h-10 w-10"
				: ghost
					? "h-8 px-3"
					: "h-10 px-3.5",
		variant === "icon+text" && !nav ? "gap-2" : "",
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
	{:else if children}
		{@render children()}
	{/if}
</Button.Root>
