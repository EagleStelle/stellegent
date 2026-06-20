<script lang="ts">
	import { goto } from '$app/navigation';
	import { useQueryClient } from '@tanstack/svelte-query';
	import { apiPost } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import type { TokenResponse } from '$lib/types';

	const qc = useQueryClient();
	let username = $state('');
	let email = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		loading = true;
		try {
			await apiPost<TokenResponse>('/api/v1/register', { username, email, password });
			await qc.invalidateQueries({ queryKey: ['me'] });
			goto('/');
		} catch (err) {
			error = err instanceof Error ? err.message : 'registration failed';
		} finally {
			loading = false;
		}
	}
</script>

<div class="mx-auto mt-16 max-w-sm">
	<h1 class="mb-6 text-2xl font-semibold">Create account</h1>
	<form onsubmit={submit} class="space-y-4">
		<input
			bind:value={username}
			placeholder="Username"
			autocomplete="username"
			class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
		/>
		<input
			bind:value={email}
			type="email"
			placeholder="Email"
			autocomplete="email"
			class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
		/>
		<input
			bind:value={password}
			type="password"
			placeholder="Password (min 8 chars)"
			autocomplete="new-password"
			class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
		/>
		{#if error}<p class="text-sm text-destructive">{error}</p>{/if}
		<Button type="submit" class="w-full" disabled={loading}>
			{loading ? 'Creating…' : 'Create account'}
		</Button>
	</form>
	<p class="mt-4 text-center text-sm text-muted-foreground">
		Have an account? <a href="/login" class="underline">Sign in</a>
	</p>
</div>
