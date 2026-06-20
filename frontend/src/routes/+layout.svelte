<script lang="ts">
	import '../app.css';
	import { QueryClient, setQueryClientContext, createQuery } from '@tanstack/svelte-query';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { apiGet, apiPost } from '$lib/api/client';
	import type { User } from '$lib/types';
	import { theme } from '$lib/theme.svelte';
	import {
		GraduationCap,
		House,
		Broadcast,
		UploadSimple,
		Sun,
		Moon,
		SignOut,
		CaretDown
	} from 'phosphor-svelte';

	let { children } = $props();

	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } }
	});
	setQueryClientContext(queryClient);

	const me = createQuery(() => ({
		queryKey: ['me'],
		queryFn: () => apiGet<User>('/api/v1/me')
	}));

	async function logout() {
		desktopMenuOpen = false;
		mobileMenuOpen = false;
		await apiPost('/api/v1/logout');
		await queryClient.invalidateQueries({ queryKey: ['me'] });
		goto('/login');
	}

	const isAuthRoute = $derived(
		['/login', '/register', '/forgot', '/reset'].includes(page.url.pathname)
	);

	const canTeach = $derived(me.data?.role === 'prof' || me.data?.role === 'admin');

	const links = $derived(
		[
			{ href: '/', label: 'Home', icon: House, show: true },
			{ href: '/live', label: 'Live', icon: Broadcast, show: canTeach },
			{ href: '/upload', label: 'Upload', icon: UploadSimple, show: canTeach }
		].filter((l) => l.show)
	);

	function isActive(href: string) {
		return href === '/' ? page.url.pathname === '/' : page.url.pathname.startsWith(href);
	}

	let desktopMenuOpen = $state(false);
	let mobileMenuOpen = $state(false);

	const initials = $derived((me.data?.username ?? '?').slice(0, 1).toUpperCase());
	const navMotion =
		'transition-[background-color,color,transform] duration-200 ease-out active:scale-[0.98]';

	function clickOutsideDesktop(node: HTMLElement) {
		const onClick = (e: MouseEvent) => {
			if (!node.contains(e.target as Node)) desktopMenuOpen = false;
		};
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') desktopMenuOpen = false;
		};
		document.addEventListener('click', onClick, true);
		document.addEventListener('keydown', onKey);
		return {
			destroy() {
				document.removeEventListener('click', onClick, true);
				document.removeEventListener('keydown', onKey);
			}
		};
	}

	function clickOutsideMobile(node: HTMLElement) {
		const onClick = (e: MouseEvent) => {
			if (!node.contains(e.target as Node)) mobileMenuOpen = false;
		};
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') mobileMenuOpen = false;
		};
		document.addEventListener('click', onClick, true);
		document.addEventListener('keydown', onKey);
		return {
			destroy() {
				document.removeEventListener('click', onClick, true);
				document.removeEventListener('keydown', onKey);
			}
		};
	}
</script>

{#if !isAuthRoute}
	<aside
		class="fixed inset-y-0 left-0 z-30 hidden w-56 flex-col bg-primary p-3 text-zinc-50 md:flex"
	>
		<a
			href="/"
			class="{navMotion} flex items-center gap-3 rounded-lg px-2.5 py-2.5 text-base font-semibold tracking-tight text-zinc-100 hover:bg-white/15 hover:text-zinc-50"
		>
			<span class="grid size-10 place-items-center rounded-lg bg-accent text-zinc-900">
				<GraduationCap size={24} weight="fill" />
			</span>
			<span>Stellegent</span>
		</a>

		{#if me.data}
			<nav class="mt-4 grid gap-1.5" aria-label="Primary">
				{#each links as link (link.href)}
					{@const active = isActive(link.href)}
					<a
						href={link.href}
						aria-current={active ? 'page' : undefined}
						class="{navMotion} flex items-center gap-3 rounded-lg px-3 py-3 text-base font-medium {active
							? 'bg-secondary text-zinc-900'
							: 'text-zinc-100 hover:bg-white/15 hover:text-zinc-50'}"
					>
						<link.icon size={22} weight={active ? 'fill' : 'regular'} />
						<span>{link.label}</span>
					</a>
				{/each}
			</nav>

			<button
				onclick={() => theme.toggle()}
				aria-label={theme.dark ? 'Switch to light mode' : 'Switch to dark mode'}
				title={theme.dark ? 'Light mode' : 'Dark mode'}
				class="{navMotion} mt-4 flex items-center gap-3 rounded-lg px-3 py-3 text-base font-medium text-zinc-100 hover:bg-white/15 hover:text-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
			>
				{#if theme.dark}
					<Sun size={22} weight="fill" />
				{:else}
					<Moon size={22} />
				{/if}
				<span>{theme.dark ? 'Light mode' : 'Dark mode'}</span>
			</button>

			<div class="relative mt-auto" use:clickOutsideDesktop>
				<button
					onclick={() => (desktopMenuOpen = !desktopMenuOpen)}
					aria-haspopup="menu"
					aria-expanded={desktopMenuOpen}
					class="{navMotion} flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-base font-medium text-zinc-100 hover:bg-white/15 hover:text-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
				>
					<span class="grid size-10 shrink-0 place-items-center rounded-lg bg-accent text-base font-semibold text-zinc-900">
						{initials}
					</span>
					<span class="min-w-0 flex-1 truncate">{me.data.username}</span>
					<CaretDown
						size={18}
						class="{navMotion} shrink-0 text-zinc-100/80 {desktopMenuOpen ? 'rotate-180' : ''}"
					/>
				</button>

				{#if desktopMenuOpen}
					<div
						role="menu"
						class="absolute bottom-0 left-full ml-2 w-56 rounded-lg bg-primary p-1.5 text-zinc-50 shadow-lg shadow-zinc-950/20"
					>
						<button
							onclick={logout}
							role="menuitem"
							class="{navMotion} flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-base text-zinc-100 hover:bg-white/15 hover:text-zinc-50"
						>
							<SignOut size={22} />
							<span>Log out</span>
						</button>
					</div>
				{/if}
			</div>
		{/if}
	</aside>

	{#if me.data}
		<nav
			class="fixed inset-x-0 bottom-0 z-30 flex items-stretch gap-1.5 bg-primary px-2 pt-2 text-zinc-50 md:hidden"
			style="padding-bottom: max(0.5rem, env(safe-area-inset-bottom));"
			aria-label="Primary"
		>
			{#each links as link (link.href)}
				{@const active = isActive(link.href)}
				<a
					href={link.href}
					onclick={() => (mobileMenuOpen = false)}
					aria-current={active ? 'page' : undefined}
					class="{navMotion} flex min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-lg px-1 py-2.5 text-xs font-semibold {active
						? 'bg-secondary text-zinc-900'
						: 'text-zinc-100 hover:bg-white/15 hover:text-zinc-50'}"
				>
					<link.icon size={23} weight={active ? 'fill' : 'regular'} />
					<span class="max-w-full truncate">{link.label}</span>
				</a>
			{/each}

			<div class="relative flex min-w-0 flex-1" use:clickOutsideMobile>
				<button
					onclick={() => (mobileMenuOpen = !mobileMenuOpen)}
					aria-haspopup="menu"
					aria-expanded={mobileMenuOpen}
					class="{navMotion} flex w-full min-w-0 flex-col items-center justify-center gap-1 rounded-lg px-1 py-2.5 text-xs font-semibold text-zinc-100 hover:bg-white/15 hover:text-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
				>
					<span class="grid size-7 place-items-center rounded-lg bg-accent text-xs font-semibold text-zinc-900">
						{initials}
					</span>
					<span class="max-w-full truncate">Me</span>
				</button>

				{#if mobileMenuOpen}
					<div
						role="menu"
						class="absolute bottom-full right-0 mb-2 w-56 rounded-lg bg-primary p-1.5 text-zinc-50 shadow-lg shadow-zinc-950/20"
					>
						<button
							onclick={() => theme.toggle()}
							role="menuitem"
							class="{navMotion} flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-base text-zinc-100 hover:bg-white/15 hover:text-zinc-50"
						>
							{#if theme.dark}
								<Sun size={22} weight="fill" />
							{:else}
								<Moon size={22} />
							{/if}
							<span>{theme.dark ? 'Light mode' : 'Dark mode'}</span>
						</button>
						<button
							onclick={logout}
							role="menuitem"
							class="{navMotion} flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-base text-zinc-100 hover:bg-white/15 hover:text-zinc-50"
						>
							<SignOut size={22} />
							<span>Log out</span>
						</button>
					</div>
				{/if}
			</div>
		</nav>
	{/if}
{/if}

{#if isAuthRoute}
	<main class="min-h-[100dvh] bg-zinc-50 px-6 py-8 text-zinc-900 dark:bg-zinc-900 dark:text-zinc-50">
		<div class="mx-auto max-w-5xl">
			{@render children()}
		</div>
	</main>
{:else}
	<main
		class="min-h-[100dvh] bg-zinc-50 px-3 pb-28 pt-4 text-zinc-900 sm:px-4 md:pb-6 md:pl-60 md:pr-4 md:pt-4 dark:bg-zinc-900 dark:text-zinc-50"
	>
		{@render children()}
	</main>
{/if}
