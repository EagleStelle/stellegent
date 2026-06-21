<script lang="ts" module>
	export type SelectOption = {
		value: string;
		label: string;
	};
</script>

<script lang="ts">
	import { Select } from "bits-ui";
	import { CaretDown, Check } from "phosphor-svelte";
	import { twMerge } from "tailwind-merge";

	let {
		value = $bindable(""),
		options = [] as SelectOption[],
		placeholder = "Select an option",
		class: className = "",
		disabled = false,
	} = $props<{
		value?: string;
		options: SelectOption[];
		placeholder?: string;
		class?: string;
		disabled?: boolean;
	}>();
</script>

<Select.Root type="single" bind:value {disabled}>
	<Select.Trigger
		class={twMerge("flex h-10 w-full items-center justify-between gap-2 rounded-lg border border-gray-200 bg-white px-3 text-sm font-medium text-primary outline-none transition-all duration-200 focus:border-secondary/60 focus:ring-3 focus:ring-secondary/15 disabled:pointer-events-none disabled:opacity-60 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-50", className)}
	>
		<span class="truncate leading-none translate-y-[1px]">
			{#if value !== "" && value !== null && value !== undefined}
				{options.find((opt: SelectOption) => opt.value === String(value))?.label ?? placeholder}
			{:else}
				<span class="text-gray-500">{placeholder}</span>
			{/if}
		</span>
		<CaretDown size={16} class="shrink-0 text-gray-500 mt-[1px]" />
	</Select.Trigger>
	<Select.Portal>
		<Select.Content
			class="z-50 max-h-96 min-w-[var(--bits-select-anchor-width)] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg outline-none dark:border-gray-800 dark:bg-gray-900"
		>
			<Select.Viewport class="p-1">
				{#each options as option (option.value)}
					<Select.Item
						value={option.value}
						label={option.label}
						class="relative flex w-full cursor-default select-none items-center rounded-lg py-2 pl-8 pr-2 text-sm text-gray-700 outline-none hover:bg-gray-100 focus:bg-gray-100 data-[highlighted]:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800 dark:focus:bg-gray-800 dark:data-[highlighted]:bg-gray-800"
					>
						<span class="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
							{#if String(value) === String(option.value)}
								<Check size={16} weight="bold" />
							{/if}
						</span>
						{option.label}
					</Select.Item>
				{/each}
			</Select.Viewport>
		</Select.Content>
	</Select.Portal>
</Select.Root>
