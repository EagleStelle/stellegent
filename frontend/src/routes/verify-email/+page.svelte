<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { apiPost } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Logo from '$lib/components/ui/Logo.svelte';
	import { CheckCircle, CircleNotch, WarningCircle } from 'phosphor-svelte';

	const token = $derived(page.url.searchParams.get('token') ?? '');
	let loading = $state(true);
	let ok = $state(false);
	let message = $state('');

	onMount(async () => {
		if (!token) {
			loading = false;
			message = 'Verification token missing.';
			return;
		}
		try {
			const res = await apiPost<{ message?: string }>('/api/v1/verify-email', { token });
			ok = true;
			message = res.message ?? 'Email verified';
		} catch (err) {
			message = err instanceof Error ? err.message : 'Verification failed';
		} finally {
			loading = false;
		}
	});
</script>

<div class="grid min-h-dvh place-items-center bg-gray-50 px-6 py-10 dark:bg-gray-950">
	<div class="w-full max-w-sm text-center">
		<a href="/" class="mx-auto mb-8 flex w-max items-center gap-2.5">
			<Logo size={36} />
			<span class="text-base font-bold tracking-tight text-zinc-900 dark:text-white">Stellegent</span>
		</a>

		<div class="mx-auto mb-4 grid size-12 place-items-center rounded-lg {ok ? 'bg-emerald-500/10 text-emerald-600' : 'bg-secondary/10 text-secondary'}">
			{#if loading}
				<CircleNotch size={24} class="animate-spin" />
			{:else if ok}
				<CheckCircle size={26} weight="fill" />
			{:else}
				<WarningCircle size={26} weight="fill" />
			{/if}
		</div>

		<h1 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">
			{loading ? 'Verifying email' : ok ? 'Email verified' : 'Verification failed'}
		</h1>
		<p class="mt-2 text-sm font-medium text-gray-500 dark:text-gray-400">{message}</p>

		<Button href="/settings" class="mt-6">Back to settings</Button>
	</div>
</div>
