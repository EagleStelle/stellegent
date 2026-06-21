<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { useQueryClient } from '@tanstack/svelte-query';
	import { apiPost } from '$lib/api/client';
	import type { TokenResponse } from '$lib/types';
	import {
		CircleNotch,
		User,
		Lock,
		Eye,
		EyeSlash,
		ArrowRight,
		GraduationCap
	} from 'phosphor-svelte';

	const qc = useQueryClient();
	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);
	let showPassword = $state(false);
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

<div class="grid min-h-dvh md:grid-cols-2">
	<!-- Brand showcase (navy) -->
	<aside
		class="relative hidden flex-col justify-between overflow-hidden bg-primary p-12 text-white lg:p-16 md:flex"
	>
		<div
			class="pointer-events-none absolute -right-24 -top-32 size-96 rounded-full bg-secondary/40 blur-[120px]"
		></div>
		<div
			class="pointer-events-none absolute -bottom-32 -left-16 size-96 rounded-full bg-secondary/20 blur-[130px]"
		></div>
		<div
			class="pointer-events-none absolute inset-0 opacity-[0.06]"
			style="background-image:radial-gradient(circle at 1px 1px,#fff 1px,transparent 0);background-size:24px 24px;"
		></div>

		<a href="/" class="relative flex w-max items-center gap-3">
			<span class="grid size-11 place-items-center rounded-2xl bg-secondary shadow-lg shadow-secondary/30">
				<GraduationCap size={24} weight="fill" />
			</span>
			<span class="text-lg font-bold tracking-tight">Stellegent</span>
		</a>
	</aside>

	<!-- Form panel -->
	<div class="flex flex-col px-6 py-10 sm:px-10">
		<!-- compact logo (mobile only) -->
		<a href="/" class="flex w-max items-center gap-2.5 md:hidden">
			<span class="grid size-9 place-items-center rounded-xl bg-secondary text-white shadow-lg shadow-secondary/30">
				<GraduationCap size={20} weight="fill" />
			</span>
			<span class="text-base font-bold tracking-tight text-zinc-900 dark:text-white">Stellegent</span>
		</a>

		<div
			class="{ease} mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-8 md:max-w-md md:py-10 {mounted
				? 'translate-y-0 opacity-100'
				: 'translate-y-6 opacity-0'}"
		>
			<h2 class="text-2xl font-bold tracking-tight text-zinc-900 md:text-4xl dark:text-white">Sign in</h2>

			<form onsubmit={submit} class="mt-6 space-y-4 md:mt-10 md:space-y-5">
				<!-- Username -->
				<div class="space-y-1.5">
					<label
						for="username"
						class="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 md:text-xs dark:text-zinc-400"
					>
						Username
					</label>
					<div class="group relative">
						<User
							size={18}
							class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400 transition-colors group-focus-within:text-secondary"
						/>
						<input
							id="username"
							bind:value={username}
							autocomplete="username"
							aria-invalid={error ? 'true' : undefined}
							required
							class="h-11 w-full rounded-2xl border border-zinc-200 bg-zinc-50 pl-11 md:h-14 pr-3.5 text-base text-zinc-900 outline-none transition-all duration-200 md:text-lg placeholder:text-zinc-400 focus:border-secondary/60 focus:bg-white focus:ring-4 focus:ring-secondary/15 aria-invalid:border-red-500 aria-invalid:ring-4 aria-invalid:ring-red-500/15 dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-white dark:focus:bg-zinc-800"
						/>
					</div>
				</div>

				<!-- Password -->
				<div class="space-y-1.5">
					<label
						for="password"
						class="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 md:text-xs dark:text-zinc-400"
					>
						Password
					</label>
					<div class="group relative">
						<Lock
							size={18}
							class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400 transition-colors group-focus-within:text-secondary"
						/>
						<input
							id="password"
							bind:value={password}
							type={showPassword ? 'text' : 'password'}
							autocomplete="current-password"
							aria-invalid={error ? 'true' : undefined}
							required
							class="h-11 w-full rounded-2xl border border-zinc-200 bg-zinc-50 pl-11 md:h-14 pr-11 text-base text-zinc-900 outline-none transition-all duration-200 md:text-lg placeholder:text-zinc-400 focus:border-secondary/60 focus:bg-white focus:ring-4 focus:ring-secondary/15 aria-invalid:border-red-500 aria-invalid:ring-4 aria-invalid:ring-red-500/15 dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-white dark:focus:bg-zinc-800"
						/>
						<button
							type="button"
							onclick={() => (showPassword = !showPassword)}
							aria-label={showPassword ? 'Hide password' : 'Show password'}
							class="absolute right-2 top-1/2 grid size-8 -translate-y-1/2 place-items-center rounded-lg text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-700/60 dark:hover:text-zinc-200"
						>
							{#if showPassword}
								<EyeSlash size={18} />
							{:else}
								<Eye size={18} />
							{/if}
						</button>
					</div>
				</div>

				{#if error}
					<p
						class="rounded-2xl bg-red-500/10 px-3.5 py-2.5 text-sm font-medium text-red-600 dark:text-red-400"
						role="alert"
					>
						{error}
					</p>
				{/if}

				<!-- Magnetic CTA with button-in-button icon -->
				<button
					type="submit"
					disabled={loading}
					class="group relative mt-2 flex h-11 w-full items-center justify-center gap-2 rounded-full bg-primary px-6 text-sm font-semibold text-white shadow-lg shadow-primary/25 md:h-14 md:text-base outline-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] hover:shadow-xl hover:shadow-primary/30 focus-visible:ring-4 focus-visible:ring-secondary/30 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-60"
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
