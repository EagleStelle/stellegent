<script lang="ts" module>
	export type ComboBoxOption = {
		value: string;
		label: string;
	};
</script>

<script lang="ts">
	import { Combobox } from "bits-ui";
	import { CaretUpDown, Check } from "phosphor-svelte";
	import { twMerge } from "tailwind-merge";
	import type { Component } from 'svelte';

	let {
		value = $bindable(""),
		options = [] as ComboBoxOption[],
		placeholder = "Select or type an option",
		class: className = "",
		disabled = false,
		icon: Icon,
	} = $props<{
		value?: string;
		options: ComboBoxOption[];
		placeholder?: string;
		class?: string;
		disabled?: boolean;
		icon?: Component<any>;
	}>();

	let open = $state(false);
	let inputValue = $state("");

	// Label that corresponds to the committed value (or "" when nothing selected).
	const selectedLabel = $derived.by(() => {
		const matched = options.find((opt: ComboBoxOption) => opt.value === value);
		return matched ? matched.label : "";
	});

	// Drive the displayed text from `open` and the selected value, NOT from
	// typing. This effect only re-runs when `open` or `selectedLabel` change, so
	// it never clobbers what the user types mid-search.
	//  - just opened  -> clear the box: fresh search, all options visible
	//    (bits-ui still highlights/scrolls to the current value)
	//  - closed / value changed -> show the selected value's label
	$effect(() => {
		// Note: do NOT read inputValue here, or typing would re-trigger this
		// effect and wipe the search text. Only `open`/`selectedLabel` are deps.
		inputValue = open ? "" : selectedLabel;
	});

	// Filter by the current search text. Empty search shows every option.
	const filtered = $derived.by(() => {
		const q = inputValue.trim().toLowerCase();
		if (!q) return options;
		return options.filter((opt: ComboBoxOption) => opt.label.toLowerCase().includes(q));
	});

	function onOpenChange(next: boolean) {
		open = next;
	}

	function onInput(event: Event) {
		const next = (event.currentTarget as HTMLInputElement).value;
		if (inputValue !== next) inputValue = next;
		// Typing the field empty clears the selection (selecting an item does
		// not call this, so picking an option is unaffected).
		if (next === "" && value !== "") value = "";
	}
</script>

<Combobox.Root type="single" bind:value inputValue={inputValue} bind:open {disabled} {onOpenChange}>
	<div
		class={twMerge(
			"relative flex h-10 w-full items-center rounded-lg border border-gray-200 bg-white text-sm font-medium text-primary outline-none transition-all duration-200 focus-within:border-secondary/60 focus-within:ring-3 focus-within:ring-secondary/15 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-50",
			disabled && "pointer-events-none opacity-60",
			className,
		)}
	>
		{#if Icon}
			<div class="pointer-events-none absolute left-3 z-10 flex items-center text-gray-500">
				<Icon size={18} />
			</div>
		{/if}
		<Combobox.Input
			{placeholder}
			onclick={() => (open = true)}
			oninput={onInput}
			class={twMerge(
				"h-full w-full rounded-lg bg-transparent leading-none outline-none placeholder:text-gray-500",
				Icon ? "pl-9" : "pl-3",
				"pr-8"
			)}
		/>
		<Combobox.Trigger class="absolute right-3 z-10 flex shrink-0 items-center text-gray-500">
			<CaretUpDown size={16} />
		</Combobox.Trigger>
	</div>

	<Combobox.Portal>
		<Combobox.Content
			sideOffset={6}
			class="z-50 max-h-96 w-(--bits-floating-anchor-width) overflow-hidden rounded-lg border border-gray-200 bg-white p-1 shadow-lg outline-none dark:border-gray-800 dark:bg-gray-900"
		>
			<Combobox.Viewport>
				{#each filtered as option (option.value)}
					<Combobox.Item
						value={option.value}
						label={option.label}
						class="flex w-full cursor-pointer select-none items-center justify-between gap-2 rounded-sm px-2 py-1.5 text-sm text-gray-700 outline-none data-highlighted:bg-secondary data-highlighted:text-white dark:text-gray-200"
					>
						{#snippet children({ selected })}
							<span class="truncate">{option.label}</span>
							{#if selected}
								<Check size={16} weight="bold" class="shrink-0" />
							{/if}
						{/snippet}
					</Combobox.Item>
				{:else}
					<div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No results</div>
				{/each}
			</Combobox.Viewport>
		</Combobox.Content>
	</Combobox.Portal>
</Combobox.Root>
