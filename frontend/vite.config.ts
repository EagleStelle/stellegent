import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env;
const apiTarget = env?.STELLEGENT_DEV_API_TARGET || 'http://localhost:8000';
const apiProxy = {
	target: apiTarget,
	changeOrigin: true
};

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			// SPA: emit a static fallback shell, all routing happens client-side.
			adapter: adapter({ fallback: 'index.html' })
		})
	],
	server: {
		// During `vite dev`, proxy API + stream to the FastAPI backend.
		proxy: {
			'/api': apiProxy,
			'/docs': apiProxy,
			'/openapi.json': apiProxy,
			'/redoc': apiProxy
		}
	}
});
