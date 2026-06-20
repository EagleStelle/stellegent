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

	const isFullWidthRoute = $derived(
		page.url.pathname.startsWith('/live') || page.url.pathname.startsWith('/upload')
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
		class="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-brand-nav px-4 py-6 text-white md:flex border-r border-white/5 shadow-2xl"
	>
		<a
			href="/"
			class="{navMotion} mb-6 flex items-center gap-3 rounded-xl px-3 py-2 text-xl font-bold tracking-tight text-white hover:opacity-80"
		>
			<span class="grid size-10 place-items-center rounded-xl bg-brand-accent text-white shadow-sm">
				<GraduationCap size={24} weight="fill" />
			</span>
			<span>Stellegent</span>
		</a>

		{#if me.data}
			<nav class="grid gap-1" aria-label="Primary">
				{#each links as link (link.href)}
					{@const active = isActive(link.href)}
					<a
						href={link.href}
						aria-current={active ? 'page' : undefined}
						class="{navMotion} flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium {active
							? 'bg-brand-accent text-white shadow-sm'
							: 'text-slate-300 hover:bg-white/10 hover:text-white'}"
					>
						<link.icon size={20} weight={active ? 'fill' : 'regular'} />
						<span>{link.label}</span>
					</a>
				{/each}
			</nav>

			<div class="mt-auto grid gap-1">
				<button
					onclick={() => theme.toggle()}
					aria-label={theme.dark ? 'Switch to light mode' : 'Switch to dark mode'}
					title={theme.dark ? 'Light mode' : 'Dark mode'}
					class="{navMotion} flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-300 hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-accent"
				>
					{#if theme.dark}
						<Sun size={20} weight="fill" />
					{:else}
						<Moon size={20} />
					{/if}
					<span>{theme.dark ? 'Light mode' : 'Dark mode'}</span>
				</button>

				<div class="relative" use:clickOutsideDesktop>
					<button
						onclick={() => (desktopMenuOpen = !desktopMenuOpen)}
						aria-haspopup="menu"
						aria-expanded={desktopMenuOpen}
						class="{navMotion} flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-slate-300 hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-accent"
					>
						<span class="grid size-8 shrink-0 place-items-center rounded-lg bg-brand-accent text-xs font-bold text-white shadow-sm">
							{initials}
						</span>
						<span class="min-w-0 flex-1 truncate">{me.data.username}</span>
						<CaretDown
							size={16}
							class="{navMotion} shrink-0 text-slate-400 {desktopMenuOpen ? 'rotate-180' : ''}"
						/>
					</button>

					{#if desktopMenuOpen}
						<div
							role="menu"
							class="absolute bottom-0 left-full ml-2 w-64 rounded-xl bg-brand-nav p-1.5 text-white shadow-xl ring-1 ring-white/10"
						>
							<button
								onclick={logout}
								role="menuitem"
								class="{navMotion} flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-300 hover:bg-white/10 hover:text-white"
							>
								<SignOut size={20} />
								<span>Log out</span>
							</button>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</aside>

	{#if me.data}
		<nav
			class="fixed inset-x-0 bottom-0 z-30 flex items-stretch gap-1 bg-brand-nav px-2 pt-2 text-white shadow-[0_-4px_20px_rgba(0,0,0,0.2)] md:hidden border-t border-white/5"
			style="padding-bottom: max(0.75rem, env(safe-area-inset-bottom));"
			aria-label="Primary"
		>
			{#each links as link (link.href)}
				{@const active = isActive(link.href)}
				<a
					href={link.href}
					onclick={() => (mobileMenuOpen = false)}
					aria-current={active ? 'page' : undefined}
					class="{navMotion} flex min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-xl px-1 py-2 text-[10px] font-medium {active
						? 'text-brand-accent'
						: 'text-slate-400 hover:text-white'}"
				>
					<div class="grid size-8 place-items-center rounded-full {active ? 'bg-brand-accent/15' : 'bg-transparent'}">
						<link.icon size={22} weight={active ? 'fill' : 'regular'} />
					</div>
					<span class="max-w-full truncate">{link.label}</span>
				</a>
			{/each}

			<div class="relative flex min-w-0 flex-1" use:clickOutsideMobile>
				<button
					onclick={() => (mobileMenuOpen = !mobileMenuOpen)}
					aria-haspopup="menu"
					aria-expanded={mobileMenuOpen}
					class="{navMotion} flex w-full min-w-0 flex-col items-center justify-center gap-1 rounded-xl px-1 py-2 text-[10px] font-medium text-slate-400 hover:text-white focus-visible:outline-none"
				>
					<div class="grid size-8 place-items-center">
						<span class="grid size-6 place-items-center rounded-full bg-brand-accent text-[10px] font-bold text-white shadow-sm ring-2 ring-brand-nav">
							{initials}
						</span>
					</div>
					<span class="max-w-full truncate">Me</span>
				</button>

				{#if mobileMenuOpen}
					<div
						role="menu"
						class="absolute bottom-full right-0 mb-3 w-48 rounded-xl bg-brand-nav p-1.5 text-white shadow-xl ring-1 ring-white/10"
					>
						<button
							onclick={() => theme.toggle()}
							role="menuitem"
							class="{navMotion} flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-300 hover:bg-white/10 hover:text-white"
						>
							{#if theme.dark}
								<Sun size={20} weight="fill" />
							{:else}
								<Moon size={20} />
							{/if}
							<span>{theme.dark ? 'Light mode' : 'Dark mode'}</span>
						</button>
						<button
							onclick={logout}
							role="menuitem"
							class="{navMotion} flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-300 hover:bg-white/10 hover:text-white"
						>
							<SignOut size={20} />
							<span>Log out</span>
						</button>
					</div>
				{/if}
			</div>
		</nav>
	{/if}
{/if}

{#if isAuthRoute}
	<main class="min-h-[100dvh] bg-slate-50 px-6 py-8 text-black dark:bg-black dark:text-white">
		<div class="mx-auto max-w-5xl">
			{@render children()}
		</div>
	</main>
{:else}
	<main
		class="min-h-[100dvh] bg-slate-50 text-black dark:bg-black dark:text-white {isFullWidthRoute
			? 'md:pl-64'
			: 'px-4 pb-24 pt-4 md:pb-8 md:pl-68 md:pr-4 md:pt-8'}"
	>
		{@render children()}
	</main>
{/if}
