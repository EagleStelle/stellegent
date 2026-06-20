import createClient from 'openapi-fetch';
import type { paths } from './schema';

/**
 * Typed API client. `credentials: 'include'` sends the httponly auth cookie set
 * by /api/v1/login. In dev, Vite proxies /api to the FastAPI backend so the
 * cookie stays same-origin; in prod the SPA is served from the same origin.
 */
export const api = createClient<paths>({
	baseUrl: '/',
	credentials: 'include'
});

/** Convenience wrappers (untyped until `npm run gen:api` fills schema.d.ts). */
export async function apiGet<T = unknown>(path: string): Promise<T> {
	const res = await fetch(path, { credentials: 'include' });
	if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
	return res.json() as Promise<T>;
}

export async function apiPost<T = unknown>(path: string, body?: unknown): Promise<T> {
	const res = await fetch(path, {
		method: 'POST',
		credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: body === undefined ? undefined : JSON.stringify(body)
	});
	if (!res.ok) {
		let detail = res.statusText;
		try {
			detail = (await res.json()).detail ?? detail;
		} catch {
			/* ignore */
		}
		throw new Error(detail);
	}
	return res.json() as Promise<T>;
}
