<script lang="ts">
	import { goto } from '$app/navigation';
	import { useQueryClient } from '@tanstack/svelte-query';
	import { apiPost } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import type { TokenResponse } from '$lib/types';

	const qc = useQueryClient();
	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		loading = true;
		try {
			await apiPost<TokenResponse>('/api/v1/login', { username, password });
			await qc.invalidateQueries({ queryKey: ['me'] });
			goto('/');
		} catch (err) {
			error = err instanceof Error ? err.message : 'login failed';
		} finally {
			loading = false;
		}
	}
</script>

<div class="mx-auto mt-16 max-w-sm">
	<h1 class="mb-6 text-2xl font-semibold">Sign in</h1>
	<form onsubmit={submit} class="space-y-4">
		<input
			bind:value={username}
			placeholder="Username"
			autocomplete="username"
			class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
		/>
		<input
			bind:value={password}
			type="password"
			placeholder="Password"
			autocomplete="current-password"
			class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
		/>
		{#if error}<p class="text-sm text-destructive">{error}</p>{/if}
		<Button type="submit" class="w-full" disabled={loading}>
			{loading ? 'Signing in…' : 'Sign in'}
		</Button>
	</form>
	<p class="mt-4 text-center text-sm text-muted-foreground">
		No account? <a href="/register" class="underline">Register</a>
	</p>
</div>
