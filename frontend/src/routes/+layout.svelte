<script lang="ts">
	import '../app.css';
	import { QueryClient, setQueryClientContext, createQuery } from '@tanstack/svelte-query';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { apiGet, apiPost } from '$lib/api/client';
	import type { User } from '$lib/types';
	import { theme } from '$lib/theme.svelte';
	import {
		Chalkboard,
		Broadcast,
		BookOpen,
		UsersThree,
		Sun,
		Moon,
		SignOut,
		Gear
	} from 'phosphor-svelte';
	import Logo from '$lib/components/ui/Logo.svelte';
	import Button from '$lib/components/ui/Button.svelte';

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
		goto('/');
	}

	const isAuthRoute = $derived(
		['/', '/register', '/forgot', '/reset', '/verify-email', '/mfa'].includes(page.url.pathname)
	);

	const canTeach = $derived(me.data?.role === 'prof' || me.data?.role === 'admin');
	const isAdmin = $derived(me.data?.role === 'admin');

	const links = $derived(
		[
			{ href: '/courses', label: 'Courses', icon: BookOpen, show: canTeach },
			{ href: '/lectures', label: 'Lectures', icon: Chalkboard, show: true },
			{ href: '/live', label: 'Live', icon: Broadcast, show: canTeach },
			{ href: '/admin', label: 'Admin', icon: UsersThree, show: isAdmin }
		].filter((l) => l.show)
	);

	function isActive(href: string) {
		return page.url.pathname.startsWith(href);
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
		class="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-primary p-4 text-white md:flex border-r border-white/5 shadow-2xl"
	>
		<a
			href="/lectures"
			class="{navMotion} mb-2 flex items-center gap-3 rounded-lg px-3.5 py-2 text-xl font-bold tracking-tight text-white hover:opacity-80"
		>
			<Logo size={40} />
			<span>Stellegent</span>
		</a>

		{#if me.data}
			<nav class="grid gap-1" aria-label="Primary">
				{#each links as link (link.href)}
					{@const active = isActive(link.href)}
					<Button
						variant="icon+text"
						nav
						{active}
						href={link.href}
						aria-current={active ? 'page' : undefined}
					>
						{#snippet icon()}
							<link.icon size={18} weight={active ? 'fill' : 'regular'} />
						{/snippet}
						<span>{link.label}</span>
					</Button>
				{/each}
			</nav>

			<div class="mt-auto grid gap-1">
				<Button
					variant="icon+text"
					nav
					onclick={() => theme.toggle()}
					aria-label={theme.dark ? 'Switch to light mode' : 'Switch to dark mode'}
				>
					{#snippet icon()}
						{#if theme.dark}
							<Sun size={18} weight="fill" />
						{:else}
							<Moon size={18} />
						{/if}
					{/snippet}
					<span>{theme.dark ? 'Light mode' : 'Dark mode'}</span>
				</Button>

				<Button
					variant="icon+text"
					nav
					active={isActive('/settings')}
					href="/settings"
					aria-current={isActive('/settings') ? 'page' : undefined}
					aria-label="Settings"
				>
					{#snippet icon()}
						<Gear size={18} weight={isActive('/settings') ? 'fill' : 'regular'} />
					{/snippet}
					<span>Settings</span>
				</Button>

				<Button
					variant="icon+text"
					ghost
					danger
					onclick={logout}
					aria-label="Log out"
					class="h-auto! w-full justify-start gap-3 px-3.5 py-2.5"
				>
					{#snippet icon()}
						<SignOut size={18} />
					{/snippet}
					<span>Log out</span>
				</Button>
			</div>
		{/if}
	</aside>

	{#if me.data}
		<nav
			class="fixed inset-x-0 bottom-0 z-30 flex items-stretch gap-1 bg-primary px-2 pt-2 text-white shadow-[0_-4px_20px_rgba(0,0,0,0.2)] md:hidden border-t border-white/5"
			style="padding-bottom: max(0.75rem, env(safe-area-inset-bottom));"
			aria-label="Primary"
		>
			{#each links as link (link.href)}
				{@const active = isActive(link.href)}
				<a
					href={link.href}
					onclick={() => (mobileMenuOpen = false)}
					aria-current={active ? 'page' : undefined}
					class="{navMotion} flex min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-lg px-1 py-2 text-[10px] font-medium {active
						? 'text-secondary'
						: 'text-gray-400 hover:text-white'}"
				>
					<div class="grid size-8 place-items-center rounded-lg {active ? 'bg-secondary/15' : 'bg-transparent'}">
						<link.icon size={22} weight={active ? 'fill' : 'regular'} />
					</div>
					<span class="max-w-full truncate">{link.label}</span>
				</a>
			{/each}

			<div class="relative flex min-w-0 flex-1" use:clickOutsideMobile>
				<Button
					onclick={() => (mobileMenuOpen = !mobileMenuOpen)}
					aria-haspopup="menu"
					aria-expanded={mobileMenuOpen}
					class="{navMotion} flex w-full min-w-0 flex-col items-center justify-center gap-1 rounded-lg px-1 py-2 text-[10px] font-medium !text-gray-400 hover:!text-white focus-visible:outline-none !bg-transparent !shadow-none !h-auto"
				>
					<div class="grid size-8 place-items-center">
						<span class="grid size-6 place-items-center rounded-lg bg-secondary text-[10px] font-bold text-white shadow-sm ring-2 ring-primary">
							{initials}
						</span>
					</div>
					<span class="max-w-full truncate">Me</span>
				</Button>

				{#if mobileMenuOpen}
					<div
						role="menu"
						class="absolute bottom-full right-0 mb-3 w-48 rounded-lg bg-primary p-1.5 text-white shadow-xl ring-1 ring-white/10"
					>
						<Button
							variant="icon+text"
							onclick={() => theme.toggle()}
							role="menuitem"
							class="{navMotion} flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium !text-gray-300 hover:!bg-white/10 hover:!text-white !bg-transparent !shadow-none !h-auto !justify-start"
						>
							{#snippet icon()}
								{#if theme.dark}
									<Sun size={18} weight="fill" />
								{:else}
									<Moon size={18} />
								{/if}
							{/snippet}
							<span>{theme.dark ? 'Light mode' : 'Dark mode'}</span>
						</Button>
						<Button
							variant="icon+text"
							href="/settings"
							onclick={() => (mobileMenuOpen = false)}
							role="menuitem"
							class="{navMotion} flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium !text-gray-300 hover:!bg-white/10 hover:!text-white !bg-transparent !shadow-none !h-auto !justify-start"
						>
							{#snippet icon()}
								<Gear size={18} />
							{/snippet}
							<span>Settings</span>
						</Button>
						<Button
							variant="icon+text"
							onclick={logout}
							role="menuitem"
							class="{navMotion} flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium !text-gray-300 hover:!bg-white/10 hover:!text-white !bg-transparent !shadow-none !h-auto !justify-start"
						>
							{#snippet icon()}
								<SignOut size={18} />
							{/snippet}
							<span>Log out</span>
						</Button>
					</div>
				{/if}
			</div>
		</nav>
	{/if}
{/if}

{#if isAuthRoute}
	<main class="min-h-[100dvh] bg-gray-50 text-primary dark:bg-gray-950 dark:text-gray-50">
		{@render children()}
	</main>
{:else}
	<main
		class="min-h-[100dvh] bg-gray-50 p-4 text-primary dark:bg-gray-950 dark:text-gray-50 md:ml-64"
	>
		{@render children()}
		{#if me.data}
			<div class="h-20 md:hidden" aria-hidden="true"></div>
		{/if}
	</main>
{/if}
