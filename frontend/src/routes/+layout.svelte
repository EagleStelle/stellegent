<script lang="ts">
	import '../app.css';
	import { QueryClient, QueryClientProvider, createQuery } from '@tanstack/svelte-query';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { apiGet, apiPost } from '$lib/api/client';
	import type { User } from '$lib/types';

	let { children } = $props();

	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } }
	});

	const me = createQuery(() => ({
		queryKey: ['me'],
		queryFn: () => apiGet<User>('/api/v1/me')
	}));

	async function logout() {
		await apiPost('/api/v1/logout');
		await queryClient.invalidateQueries({ queryKey: ['me'] });
		goto('/login');
	}

	const isAuthRoute = $derived(
		['/login', '/register', '/forgot', '/reset'].includes(page.url.pathname)
	);
</script>

<QueryClientProvider client={queryClient}>
	{#if !isAuthRoute}
		<header class="flex items-center justify-between border-b border-border px-6 py-3">
			<a href="/" class="text-lg font-semibold">Stellegent</a>
			<nav class="flex items-center gap-4 text-sm">
				{#if me.data}
					{#if me.data.role === 'prof' || me.data.role === 'admin'}
						<a href="/live" class="hover:underline">Live</a>
						<a href="/upload" class="hover:underline">Upload</a>
					{/if}
					<span class="text-muted-foreground">{me.data.username} ({me.data.role})</span>
					<button onclick={logout} class="hover:underline">Logout</button>
				{/if}
			</nav>
		</header>
	{/if}
	<main class="mx-auto max-w-5xl px-6 py-8">
		{@render children()}
	</main>
</QueryClientProvider>
