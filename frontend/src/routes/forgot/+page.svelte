<script lang="ts">
	import { apiPost } from '$lib/api/client';
	import type { MessageResponse } from '$lib/types';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Logo from '$lib/components/ui/Logo.svelte';
	import { toast } from 'svelte-sonner';
	import { ArrowLeft, CircleNotch, EnvelopeSimple } from 'phosphor-svelte';

	let email = $state('');
	let loading = $state(false);
	let devToken = $state('');

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		loading = true;
		devToken = '';
		try {
			const res = await apiPost<MessageResponse>('/api/v1/forgot-password', { email });
			toast.success(res.message ?? 'Reset link sent');
			devToken = res.reset_token ?? '';
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Could not send reset email');
		} finally {
			loading = false;
		}
	}
</script>

<div class="grid min-h-dvh place-items-center bg-gray-50 px-6 py-10 dark:bg-gray-950">
	<div class="w-full max-w-sm">
		<a href="/" class="mb-8 flex w-max items-center gap-2.5">
			<Logo size={36} />
			<span class="text-base font-bold tracking-tight text-zinc-900 dark:text-white">Stellegent</span>
		</a>

		<h1 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">Reset password</h1>
		<p class="mt-1 text-sm font-medium text-gray-500 dark:text-gray-400">
			Enter your email and we will send a reset link.
		</p>

		<form onsubmit={submit} class="mt-5 grid gap-3">
			<Input
				id="forgot-email"
				label="Email"
				type="email"
				bind:value={email}
				icon={EnvelopeSimple}
				autocomplete="email"
				required
			/>

			{#if devToken}
				<a
					href={`/reset?token=${encodeURIComponent(devToken)}`}
					class="rounded-lg bg-gray-100 px-3.5 py-2.5 text-sm font-bold text-primary transition-colors hover:text-secondary dark:bg-gray-900 dark:text-gray-50"
				>
					Open dev reset link
				</a>
			{/if}

			<Button type="submit" disabled={loading} class="w-full text-sm font-semibold">
				{#if loading}
					<CircleNotch size={18} class="animate-spin" />
					<span>Sending...</span>
				{:else}
					<span>Send reset link</span>
				{/if}
			</Button>
		</form>

		<a
			href="/"
			class="group mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-zinc-500 transition-colors hover:text-secondary dark:text-zinc-400"
		>
			<ArrowLeft size={15} weight="bold" class="transition-transform duration-300 group-hover:-translate-x-1" />
			Back to sign in
		</a>
	</div>
</div>
