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

/**
 * FastAPI returns errors as `{ detail }`, where `detail` is a string for HTTP
 * exceptions but an array of `{ loc, msg, type }` objects for 422 validation
 * errors. Flatten both shapes to a readable string so callers never surface
 * "[object Object]".
 */
async function readError(res: Response): Promise<string> {
	try {
		const data = await res.json();
		const detail = data?.detail;
		if (typeof detail === 'string') return detail;
		if (Array.isArray(detail)) {
			const msg = detail.map((e) => e?.msg ?? String(e)).filter(Boolean).join(', ');
			if (msg) return msg;
		} else if (detail && typeof detail === 'object' && typeof detail.msg === 'string') {
			return detail.msg;
		}
	} catch {
		/* ignore */
	}
	return res.statusText;
}

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
	if (!res.ok) throw new Error(await readError(res));
	return res.json() as Promise<T>;
}

export async function apiPatch<T = unknown>(path: string, body?: unknown): Promise<T> {
	const res = await fetch(path, {
		method: 'PATCH',
		credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: body === undefined ? undefined : JSON.stringify(body)
	});
	if (!res.ok) throw new Error(await readError(res));
	return res.json() as Promise<T>;
}

export async function apiDelete<T = unknown>(path: string): Promise<T> {
	const res = await fetch(path, { method: 'DELETE', credentials: 'include' });
	if (!res.ok) throw new Error(await readError(res));
	return res.json() as Promise<T>;
}
