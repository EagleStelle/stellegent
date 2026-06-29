<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { useQueryClient } from '@tanstack/svelte-query';
	import { apiPost } from '$lib/api/client';
	import type { MfaChallenge, TokenResponse } from '$lib/types';
	import { theme } from '$lib/theme.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import InputPassword from '$lib/components/ui/InputPassword.svelte';
	import Logo from '$lib/components/ui/Logo.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { toast } from 'svelte-sonner';
	import {
		CircleNotch,
		EnvelopeSimple,
		Lock,
		ArrowRight,
		Sun,
		Moon,
		GoogleLogoIcon,
		GithubLogo
	} from 'phosphor-svelte';

	const qc = useQueryClient();
	let email = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);
	let mounted = $state(false);

	onMount(() => {
		mounted = true;
	});

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		loading = true;
		try {
			const res = await apiPost<TokenResponse | MfaChallenge>('/api/v1/login', { email, password });
			if ('mfa_required' in res && res.mfa_required) {
				goto('/mfa');
				return;
			}
			await qc.invalidateQueries({ queryKey: ['me'] });
			goto('/courses');
		} catch (err) {
			const msg = err instanceof Error ? err.message : 'Sign in failed';
			error = msg;
			toast.error(msg);
		} finally {
			loading = false;
		}
	}

	const ease = 'transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)]';

	// Google OAuth bounces back with a status query param. Surface it once.
	let googleNotified = false;
	$effect(() => {
		const status = page.url.searchParams.get('google');
		if (!status || googleNotified) return;
		googleNotified = true;
		const messages: Record<string, string> = {
			failed: 'Google sign in failed',
			disabled: 'That account is disabled',
			invalid_state: 'Google sign in expired. Try again',
			cancelled: 'Google sign in cancelled'
		};
		if (messages[status]) toast.error(messages[status]);
	});
</script>

<Button
	variant="icon"
	onclick={() => theme.toggle()}
	aria-label={theme.dark ? 'Switch to light mode' : 'Switch to dark mode'}
	class="fixed right-12 top-12 z-20 hidden shadow-lg shadow-secondary/30 lg:right-16 lg:top-16 md:grid"
>
	{#snippet icon()}
		{#if theme.dark}
			<Sun size={20} weight="fill" />
		{:else}
			<Moon size={20} />
		{/if}
	{/snippet}
</Button>

<div class="grid min-h-dvh md:grid-cols-2">
	<!-- Brand showcase (navy) -->
	<aside
		class="relative hidden flex-col justify-between overflow-hidden bg-primary p-12 text-white lg:p-16 md:flex"
	>
		<div
			class="pointer-events-none absolute -right-24 -top-32 size-96 rounded-lg bg-secondary/40 blur-[120px]"
		></div>
		<div
			class="pointer-events-none absolute -bottom-32 -left-16 size-96 rounded-lg bg-secondary/20 blur-[130px]"
		></div>
		<a href="/" class="relative flex w-max items-center gap-3">
			<Logo size={44} />
			<span class="text-lg font-bold tracking-tight">Stellegent</span>
		</a>

		<footer class="relative flex flex-col gap-2 text-sm text-white/70">
			<span>&copy; Stellegent 2026</span>
			<a
				href="https://github.com/EagleStelle"
				target="_blank"
				rel="noopener noreferrer"
				class="flex w-max items-center gap-2 transition-colors hover:text-white"
			>
				<GithubLogo size={18} weight="fill" />
				<span>EagleStelle</span>
			</a>
		</footer>
	</aside>

	<!-- Form panel -->
	<div class="flex flex-col px-6 py-10 sm:px-10">
		<div class="flex items-center justify-between md:hidden">
			<a href="/" class="flex w-max items-center gap-2.5">
				<Logo size={36} />
				<span class="text-base font-bold tracking-tight text-zinc-900 dark:text-white">Stellegent</span>
			</a>
			<Button
				variant="icon"
				onclick={() => theme.toggle()}
				aria-label={theme.dark ? 'Switch to light mode' : 'Switch to dark mode'}
				class="shadow-lg shadow-secondary/30"
			>
				{#snippet icon()}
					{#if theme.dark}
						<Sun size={20} weight="fill" />
					{:else}
						<Moon size={20} />
					{/if}
				{/snippet}
			</Button>
		</div>

		<div
			class="{ease} mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-6 {mounted
				? 'translate-y-0 opacity-100'
				: 'translate-y-6 opacity-0'}"
		>
			<h1 class="text-center text-2xl font-bold tracking-tight text-zinc-900 md:text-3xl dark:text-white">Sign in</h1>

			<form onsubmit={submit} class="mt-5 flex flex-col gap-3">
				<Input
					id="email"
					label="Email"
					type="email"
					bind:value={email}
					icon={EnvelopeSimple}
					autocomplete="email"
					required
					error={!!error}
				/>

				<InputPassword
					id="password"
					label="Password"
					bind:value={password}
					icon={Lock}
					autocomplete="current-password"
					required
					error={!!error}
				/>

				<!-- Magnetic CTA with button-in-button icon -->
				<Button
					type="submit"
					disabled={loading}
					class="mt-1 w-full text-sm font-semibold shadow-md shadow-primary/20"
				>
					{#if loading}
						<CircleNotch size={18} class="animate-spin" />
						<span>Signing in…</span>
					{:else}
						<span>Sign in</span>
					{/if}
				</Button>
			</form>

			<div class="my-5 flex items-center gap-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
				<span class="h-px flex-1 bg-gray-200 dark:bg-gray-800"></span>
				<span>or</span>
				<span class="h-px flex-1 bg-gray-200 dark:bg-gray-800"></span>
			</div>

			<a
				href="/api/v1/auth/google/start?mode=login"
				class="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-3.5 text-sm font-semibold text-primary transition-all duration-200 hover:border-secondary/40 hover:text-secondary focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/25 active:scale-[0.98] dark:border-gray-800 dark:bg-gray-900 dark:text-gray-50"
			>
				<GoogleLogoIcon size={18} weight="bold" />
				<span>Continue with Google</span>
			</a>

			<a
				href="/register"
				class="group mt-8 inline-flex items-center gap-1.5 self-start text-sm font-semibold text-zinc-500 transition-colors hover:text-secondary dark:text-zinc-400"
			>
				Create an account
				<ArrowRight
					size={15}
					weight="bold"
					class="transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:translate-x-1"
				/>
			</a>
			<a
				href="/forgot"
				class="mt-3 inline-flex self-start text-sm font-semibold text-zinc-500 transition-colors hover:text-secondary dark:text-zinc-400"
			>
				Forgot password?
			</a>
		</div>
	</div>
</div>
