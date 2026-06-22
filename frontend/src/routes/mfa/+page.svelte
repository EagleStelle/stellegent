<script lang="ts">
	import { goto } from '$app/navigation';
	import { useQueryClient } from '@tanstack/svelte-query';
	import { apiPost } from '$lib/api/client';
	import type { TokenResponse } from '$lib/types';
	import Input from '$lib/components/ui/Input.svelte';
	import Logo from '$lib/components/ui/Logo.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { toast } from 'svelte-sonner';
	import { ArrowLeft, CircleNotch, Key, ShieldCheck } from 'phosphor-svelte';

	const qc = useQueryClient();
	let code = $state('');
	let error = $state('');
	let loading = $state(false);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		loading = true;
		try {
			await apiPost<TokenResponse>('/api/v1/login/mfa', { code });
			await qc.invalidateQueries({ queryKey: ['me'] });
			goto('/courses');
		} catch (err) {
			const msg = err instanceof Error ? err.message : 'Verification failed';
			error = msg;
			toast.error(msg);
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

		<div class="mb-5 flex items-center gap-3">
			<ShieldCheck size={24} weight="fill" class="text-secondary shrink-0" />
			<h1 class="text-xl font-bold tracking-tight text-primary dark:text-gray-50">Two-factor code</h1>
		</div>

		<form onsubmit={submit} class="grid gap-3">
			<Input
				id="mfa-code"
				label="Verification code"
				bind:value={code}
				icon={Key}
				autocomplete="one-time-code"
				inputmode="numeric"
				required
				error={!!error}
			/>

			<Button type="submit" disabled={loading} class="w-full text-sm font-semibold shadow-md shadow-primary/20">
				{loading ? 'Verifying...' : 'Verify'}
			</Button>
		</form>

		<a
			href="/"
			class="group mt-6 inline-flex items-center gap-1.5 text-sm font-semibold text-zinc-500 transition-colors hover:text-secondary dark:text-zinc-400"
		>
			<ArrowLeft
				size={15}
				weight="bold"
				class="transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:-translate-x-1"
			/>
			Back to sign in
		</a>
	</div>
</div>
