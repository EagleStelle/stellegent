<script lang="ts">
	import { goto } from '$app/navigation';
	import { useQueryClient } from '@tanstack/svelte-query';
	import { apiPost } from '$lib/api/client';
	import type { TokenResponse } from '$lib/types';
	import { CircleNotch } from 'phosphor-svelte';

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
			error = err instanceof Error ? err.message : 'Registration failed';
		} finally {
			loading = false;
		}
	}
</script>

<section class="flex min-h-[calc(100dvh-4rem)] items-center justify-center py-10">
	<div
		class="flex w-full max-w-sm flex-col gap-5 overflow-hidden rounded-[min(var(--radius-4xl),24px)] border border-border/70 bg-card/90 py-5 text-sm text-card-foreground shadow-xl shadow-primary/10"
	>
		<div class="grid auto-rows-min grid-cols-[1fr_auto] items-start gap-1.5 px-5">
			<div class="text-xl font-medium">Create your account</div>
			<p class="text-sm text-muted-foreground">Start collecting searchable lecture captures.</p>
			<a
				href="/login"
				class="col-start-2 row-span-2 row-start-1 inline-flex items-center self-start justify-self-end text-sm font-medium text-primary underline-offset-4 hover:underline"
			>
				Sign in
			</a>
		</div>
		<div class="px-5">
			<form id="register-form" onsubmit={submit} class="space-y-4">
				<div class="grid gap-2">
					<label
						for="username"
						class="flex items-center gap-2 text-sm font-medium leading-none select-none"
					>
						Username
					</label>
					<input
						id="username"
						bind:value={username}
						autocomplete="username"
						aria-invalid={error ? 'true' : undefined}
						required
						class="h-8 w-full min-w-0 rounded-2xl border border-transparent bg-input/50 px-2.5 py-1 text-base outline-none transition-[color,box-shadow] duration-200 placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
					/>
				</div>
				<div class="grid gap-2">
					<label
						for="email"
						class="flex items-center gap-2 text-sm font-medium leading-none select-none"
					>
						Email
					</label>
					<input
						id="email"
						bind:value={email}
						type="email"
						autocomplete="email"
						aria-invalid={error ? 'true' : undefined}
						required
						class="h-8 w-full min-w-0 rounded-2xl border border-transparent bg-input/50 px-2.5 py-1 text-base outline-none transition-[color,box-shadow] duration-200 placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
					/>
				</div>
				<div class="grid gap-2">
					<label
						for="password"
						class="flex items-center gap-2 text-sm font-medium leading-none select-none"
					>
						Password
					</label>
					<input
						id="password"
						bind:value={password}
						type="password"
						autocomplete="new-password"
						minlength="8"
						aria-invalid={error ? 'true' : undefined}
						required
						class="h-8 w-full min-w-0 rounded-2xl border border-transparent bg-input/50 px-2.5 py-1 text-base outline-none transition-[color,box-shadow] duration-200 placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
					/>
				</div>
				{#if error}
					<p class="rounded-2xl bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
						{error}
					</p>
				{/if}
			</form>
		</div>
		<div class="flex items-center px-5">
			<button
				type="submit"
				form="register-form"
				disabled={loading}
				class="inline-flex h-8 w-full shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-2xl border border-transparent bg-primary px-3 text-sm font-medium text-primary-foreground outline-none transition-all hover:bg-primary/80 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 disabled:pointer-events-none disabled:opacity-50"
			>
				{#if loading}<CircleNotch size={16} class="animate-spin" />{/if}
				{loading ? 'Creating...' : 'Create account'}
			</button>
		</div>
	</div>
</section>
