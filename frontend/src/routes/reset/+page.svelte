<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { apiPost } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import InputPassword from '$lib/components/ui/InputPassword.svelte';
	import Logo from '$lib/components/ui/Logo.svelte';
	import { toast } from 'svelte-sonner';
	import { ArrowLeft, CircleNotch, Key } from 'phosphor-svelte';

	let password = $state('');
	let loading = $state(false);
	const token = $derived(page.url.searchParams.get('token') ?? '');

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		loading = true;
		try {
			await apiPost('/api/v1/reset-password', { token, password });
			toast.success('Password updated');
			setTimeout(() => goto('/'), 900);
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Password reset failed');
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

		<h1 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">Choose new password</h1>
		<p class="mt-1 text-sm font-medium text-gray-500 dark:text-gray-400">
			Reset links expire after 30 minutes.
		</p>

		<form onsubmit={submit} class="mt-5 grid gap-3">
			<InputPassword
				id="reset-password"
				label="New password"
				bind:value={password}
				icon={Key}
				autocomplete="new-password"
				minlength={8}
				required
				disabled={!token}
			/>

			{#if !token}
				<p class="rounded-lg bg-red-500/10 px-3.5 py-2.5 text-sm font-medium text-red-600 dark:text-red-400" role="alert">
					Reset token missing
				</p>
			{/if}

			<Button type="submit" disabled={loading || !token} class="w-full text-sm font-semibold">
				{#if loading}
					<CircleNotch size={18} class="animate-spin" />
					<span>Updating...</span>
				{:else}
					<span>Update password</span>
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
