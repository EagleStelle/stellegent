<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { apiPost } from '$lib/api/client';
	import Logo from '$lib/components/ui/Logo.svelte';
	import { ArrowLeft, CheckCircle, CircleNotch, WarningCircle } from 'phosphor-svelte';

	const token = $derived(page.url.searchParams.get('token') ?? '');
	const verified = $derived(page.url.searchParams.get('verified') === '1');
	const error = $derived(page.url.searchParams.get('error') ?? '');
	let loading = $state(true);
	let ok = $state(false);
	let message = $state('');

	onMount(async () => {
		if (verified) {
			ok = true;
			loading = false;
			message = 'Email verified';
			return;
		}
		if (error) {
			loading = false;
			message = error === 'invalid' ? 'Invalid or expired token.' : 'Verification failed';
			return;
		}
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
	<div class="w-full max-w-sm">
		<a href="/" class="mb-8 flex w-max items-center gap-2.5">
			<Logo size={36} />
			<span class="text-base font-bold tracking-tight text-zinc-900 dark:text-white">Stellegent</span>
		</a>

		<div class="mb-5 flex items-center gap-3">
			{#if loading}
				<CircleNotch size={24} class="text-secondary shrink-0 animate-spin" />
			{:else if ok}
				<CheckCircle size={24} weight="fill" class="text-secondary shrink-0" />
			{:else}
				<WarningCircle size={24} weight="fill" class="text-secondary shrink-0" />
			{/if}
			<h1 class="text-xl font-bold tracking-tight text-primary dark:text-gray-50">
				{loading ? 'Verifying email' : ok ? 'Email verified' : 'Verification failed'}
			</h1>
		</div>

		{#if !ok}
			<p class="text-sm font-medium text-gray-500 dark:text-gray-400">{message}</p>
		{/if}

		<a
			href="/settings"
			class="group mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-zinc-500 transition-colors hover:text-secondary dark:text-zinc-400"
		>
			<ArrowLeft
				size={15}
				weight="bold"
				class="transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:-translate-x-1"
			/>
			Back to settings
		</a>
	</div>
</div>
