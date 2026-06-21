<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { useQueryClient } from '@tanstack/svelte-query';
	import { apiPost } from '$lib/api/client';
	import type { TokenResponse } from '$lib/types';
	import { theme } from '$lib/theme.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import InputPassword from '$lib/components/ui/InputPassword.svelte';
	import {
		CircleNotch,
		User,
		Lock,
		ArrowRight,
		GraduationCap,
		Sun,
		Moon
	} from 'phosphor-svelte';

	const qc = useQueryClient();
	let username = $state('');
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
			await apiPost<TokenResponse>('/api/v1/login', { username, password });
			await qc.invalidateQueries({ queryKey: ['me'] });
			goto('/');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Sign in failed';
		} finally {
			loading = false;
		}
	}

	const ease = 'transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)]';
</script>

<button
	onclick={() => theme.toggle()}
	aria-label={theme.dark ? 'Switch to light mode' : 'Switch to dark mode'}
	title={theme.dark ? 'Light mode' : 'Dark mode'}
	class="fixed bottom-6 left-6 z-20 hidden size-11 place-items-center rounded-lg bg-secondary text-white shadow-lg shadow-secondary/30 transition-all hover:bg-secondary/90 active:scale-[0.96] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary md:grid"
>
	{#if theme.dark}
		<Sun size={20} weight="fill" />
	{:else}
		<Moon size={20} />
	{/if}
</button>

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
		<div
			class="pointer-events-none absolute inset-0 opacity-[0.06]"
			style="background-image:radial-gradient(circle at 1px 1px,#fff 1px,transparent 0);background-size:24px 24px;"
		></div>

		<a href="/" class="relative flex w-max items-center gap-3">
			<span class="grid size-11 place-items-center rounded-lg bg-secondary shadow-lg shadow-secondary/30">
				<GraduationCap size={24} weight="fill" />
			</span>
			<span class="text-lg font-bold tracking-tight">Stellegent</span>
		</a>
	</aside>

	<!-- Form panel -->
	<div class="flex flex-col px-6 py-10 sm:px-10">
		<div class="flex items-center justify-between md:hidden">
			<a href="/" class="flex w-max items-center gap-2.5">
				<span class="grid size-9 place-items-center rounded-lg bg-secondary text-white shadow-lg shadow-secondary/30">
					<GraduationCap size={20} weight="fill" />
				</span>
				<span class="text-base font-bold tracking-tight text-zinc-900 dark:text-white">Stellegent</span>
			</a>
			<button
				onclick={() => theme.toggle()}
				aria-label={theme.dark ? 'Switch to light mode' : 'Switch to dark mode'}
				class="grid size-9 place-items-center rounded-lg bg-secondary text-white shadow-lg shadow-secondary/30 transition-all hover:bg-secondary/90 active:scale-[0.96] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
			>
				{#if theme.dark}
					<Sun size={20} weight="fill" />
				{:else}
					<Moon size={20} />
				{/if}
			</button>
		</div>

		<div
			class="{ease} mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-8 md:max-w-lg md:py-10 {mounted
				? 'translate-y-0 opacity-100'
				: 'translate-y-6 opacity-0'}"
		>
			<h1 class="text-center text-2xl font-bold tracking-tight text-zinc-900 md:text-4xl dark:text-white">Sign in</h1>

			<form onsubmit={submit} class="mt-6 flex flex-col gap-4 md:mt-10 md:gap-5">
				<Input
					id="username"
					label="Username"
					bind:value={username}
					icon={User}
					autocomplete="username"
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

				{#if error}
					<p
						class="rounded-lg bg-red-500/10 px-3.5 py-2.5 text-sm font-medium text-red-600 dark:text-red-400"
						role="alert"
					>
						{error}
					</p>
				{/if}

				<!-- Magnetic CTA with button-in-button icon -->
				<button
					type="submit"
					disabled={loading}
					class="group relative mt-2 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary px-6 text-sm font-semibold text-white shadow-lg shadow-primary/25 md:h-14 md:text-base outline-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] hover:shadow-xl hover:shadow-primary/30 focus-visible:ring-4 focus-visible:ring-secondary/30 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-60"
				>
					{#if loading}
						<CircleNotch size={18} class="animate-spin" />
						<span>Signing in…</span>
					{:else}
						<span>Sign in</span>
					{/if}
				</button>
			</form>

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
		</div>
	</div>
</div>
