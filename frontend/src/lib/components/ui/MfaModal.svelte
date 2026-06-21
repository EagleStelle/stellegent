<script lang="ts">
	import Modal from '$lib/components/ui/Modal.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { Key, ShieldCheck } from 'phosphor-svelte';

	let {
		open = $bindable(false),
		onconfirm,
		title = 'Confirm with two-factor',
		description = 'Enter your authenticator code to continue.'
	}: {
		open?: boolean;
		/** Called with the entered code. Throw to keep the modal open and show the error. */
		onconfirm: (code: string) => Promise<void>;
		title?: string;
		description?: string;
	} = $props();

	let code = $state('');
	let loading = $state(false);
	let error = $state('');

	// Reset transient state whenever the modal is (re)opened or closed.
	$effect(() => {
		if (!open) {
			code = '';
			error = '';
			loading = false;
		}
	});

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		loading = true;
		try {
			await onconfirm(code.trim());
			open = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Verification failed';
		} finally {
			loading = false;
		}
	}
</script>

<Modal bind:open label={title}>
	<div class="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-900">
		<div class="mb-5 flex items-center gap-3">
			<ShieldCheck size={24} weight="fill" class="text-secondary shrink-0" />
			<h2 class="text-lg font-bold tracking-tight text-primary dark:text-gray-50">{title}</h2>
		</div>

		<p class="mb-4 text-sm text-primary/70 dark:text-gray-400">{description}</p>

		<form onsubmit={submit} class="grid gap-3">
			<Input
				id="mfa-modal-code"
				label="Verification code"
				bind:value={code}
				icon={Key}
				autocomplete="one-time-code"
				inputmode="numeric"
				required
				error={!!error}
			/>

			{#if error}
				<p
					class="rounded-lg bg-red-500/10 px-3.5 py-2.5 text-sm font-medium text-red-600 dark:text-red-400"
					role="alert"
				>
					{error}
				</p>
			{/if}

			<Button type="submit" disabled={loading} class="w-full text-sm font-semibold">
				{loading ? 'Verifying...' : 'Verify'}
			</Button>
		</form>
	</div>
</Modal>
