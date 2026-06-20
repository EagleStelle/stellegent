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
		menuOpen = false;
		await apiPost('/api/v1/logout');
		await queryClient.invalidateQueries({ queryKey: ['me'] });
		goto('/login');
	}

	const isAuthRoute = $derived(
		['/login', '/register', '/forgot', '/reset'].includes(page.url.pathname)
	);

	const canTeach = $derived(me.data?.role === 'prof' || me.data?.role === 'admin');

	// Nav links, filtered by role at render time.
	const links = $derived(
		[
			{ href: '/', label: 'Lectures', icon: House, show: true },
			{ href: '/live', label: 'Live', icon: Broadcast, show: canTeach },
			{ href: '/upload', label: 'Upload', icon: UploadSimple, show: canTeach }
		].filter((l) => l.show)
	);

	function isActive(href: string) {
		return href === '/' ? page.url.pathname === '/' : page.url.pathname.startsWith(href);
	}

	let menuOpen = $state(false);

	const initials = $derived((me.data?.username ?? '?').slice(0, 1).toUpperCase());

	// Close the user menu on outside click / Escape.
	function clickOutside(node: HTMLElement) {
		const onClick = (e: MouseEvent) => {
			if (!node.contains(e.target as Node)) menuOpen = false;
		};
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') menuOpen = false;
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
	<header
		class="sticky top-0 z-40 bg-[hsl(348_80%_40%)] shadow-md"
	>
		<div class="flex h-14 w-full items-center gap-4 px-6">
			<!-- Brand -->
			<a href="/" class="flex items-center gap-2 font-semibold tracking-tight">
				<GraduationCap size={26} weight="fill" class="text-[hsl(42_95%_55%)]" />
				<span class="text-base text-[hsl(42_95%_60%)]">Stellegent</span>
			</a>

			<!-- Primary nav -->
			{#if me.data}
				<nav class="ml-2 flex items-center gap-1 text-sm">
					{#each links as link (link.href)}
						{@const active = isActive(link.href)}
						<a
							href={link.href}
							aria-current={active ? 'page' : undefined}
							class="flex items-center gap-2 rounded-md px-3 py-2 font-medium transition-colors {active
								? 'bg-[hsl(42_95%_55%)] text-[hsl(0_0%_10%)]'
								: 'text-[hsl(40_30%_82%)] hover:bg-white/10 hover:text-white'}"
						>
							<link.icon size={18} weight={active ? 'fill' : 'regular'} />
							<span>{link.label}</span>
						</a>
					{/each}
				</nav>
			{/if}

			<!-- Right cluster -->
			<div class="ml-auto flex items-center gap-1">
				<button
					onclick={() => theme.toggle()}
					aria-label={theme.dark ? 'Switch to light mode' : 'Switch to dark mode'}
					title={theme.dark ? 'Light mode' : 'Dark mode'}
					class="grid h-9 w-9 place-items-center rounded-md text-[hsl(40_30%_82%)] transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
				>
					{#if theme.dark}
						<Sun size={20} weight="fill" />
					{:else}
						<Moon size={20} />
					{/if}
				</button>

				{#if me.data}
					<div class="relative" use:clickOutside>
						<button
							onclick={() => (menuOpen = !menuOpen)}
							aria-haspopup="menu"
							aria-expanded={menuOpen}
							class="flex items-center gap-2 rounded-md py-1 pl-1 pr-2 text-white transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
						>
							<span
								class="grid h-8 w-8 place-items-center rounded-full bg-[hsl(0_0%_10%)] text-sm font-semibold text-[hsl(42_95%_60%)] ring-1 ring-[hsl(42_80%_50%)]"
							>
								{initials}
							</span>
							<span class="hidden text-sm font-medium sm:block">{me.data.username}</span>
							<CaretDown
								size={14}
								class="text-[hsl(40_30%_82%)] transition-transform {menuOpen ? 'rotate-180' : ''}"
							/>
						</button>

						{#if menuOpen}
							<div
								role="menu"
								class="absolute right-0 mt-2 w-56 overflow-hidden rounded-lg border border-border bg-card p-1 shadow-lg shadow-black/5"
							>
								<div class="px-3 py-2.5">
									<p class="truncate text-sm font-medium text-card-foreground">
										{me.data.username}
									</p>
									<span
										class="mt-1 inline-block rounded bg-accent/15 px-1.5 py-0.5 text-xs font-medium uppercase tracking-wide text-accent"
									>
										{me.data.role}
									</span>
								</div>
								<div class="my-1 h-px bg-border"></div>
								<button
									onclick={logout}
									role="menuitem"
									class="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-card-foreground transition-colors hover:bg-secondary"
								>
									<SignOut size={18} />
									<span>Log out</span>
								</button>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</header>
{/if}

<main class="mx-auto max-w-5xl px-6 py-8">
	{@render children()}
</main>
