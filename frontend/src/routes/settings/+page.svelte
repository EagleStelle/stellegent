<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { apiGet, apiPatch, apiPost } from '$lib/api/client';
	import type { Account, MessageResponse, TotpEnableResponse, TotpSetup } from '$lib/types';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import InputPassword from '$lib/components/ui/InputPassword.svelte';
	import MfaModal from '$lib/components/ui/MfaModal.svelte';
	import { toast } from 'svelte-sonner';
	import {
		CheckCircle,
		CircleNotch,
		CopySimple,
		EnvelopeSimple,
		FloppyDisk,
		GoogleLogoIcon,
		Key,
		LinkBreak,
		LockKey,
		Password,
		QrCode,
		ShieldCheck,
		User,
		WarningCircle
	} from 'phosphor-svelte';

	const qc = useQueryClient();
	const account = createQuery(() => ({
		queryKey: ['account'],
		queryFn: () => apiGet<Account>('/api/v1/account')
	}));

	$effect(() => {
		if (account.isError) goto('/');
	});

	let hydratedUid = $state<number | null>(null);
	let fullName = $state('');
	let email = $state('');

	let profileLoading = $state(false);
	let verificationLoading = $state(false);

	let currentPassword = $state('');
	let newPassword = $state('');
	let passwordLoading = $state(false);

	let setup = $state<TotpSetup | null>(null);
	let setupCode = $state('');
	let setupLoading = $state(false);
	let confirmLoading = $state(false);
	let recoveryCodes = $state<string[]>([]);
	let copiedCodes = $state(false);

	let disablePassword = $state('');
	let disableCode = $state('');
	let disableLoading = $state(false);

	let googleLoading = $state(false);

	// Authenticator step-up: when 2FA is on, sensitive changes route through the
	// MFA modal, which calls back into the pending action with the entered code.
	let mfaOpen = $state(false);
	let pendingMfa = $state<((code: string) => Promise<void>) | null>(null);

	$effect(() => {
		if (account.data && account.data.uid !== hydratedUid) {
			hydratedUid = account.data.uid;
			fullName = account.data.username;
			email = account.data.email ?? '';
		}
	});

	const profileChanged = $derived(
		account.data &&
			(fullName.trim() !== account.data.username || email.trim() !== (account.data.email ?? ''))
	);
	const passwordChanged = $derived(currentPassword.length > 0 || newPassword.length > 0);
	const disableTotpChanged = $derived(disableCode.length > 0 || disablePassword.length > 0);

	// Google OAuth redirects back with a status query param. Surface it once as a
	// toast, then move on.
	let googleNotified = false;
	$effect(() => {
		const status = page.url.searchParams.get('google');
		if (!status || googleNotified) return;
		googleNotified = true;
		const messages: Record<string, { text: string; error: boolean }> = {
			linked: { text: 'Google account connected', error: false },
			conflict: { text: 'That Google account is already connected to another user', error: true },
			failed: { text: 'Google connection failed', error: true },
			login_required: { text: 'Sign in again to connect Google', error: true },
			invalid_state: { text: 'Google connection expired. Try again', error: true },
			cancelled: { text: 'Google connection cancelled', error: true }
		};
		const notice = messages[status];
		if (!notice) return;
		if (notice.error) toast.error(notice.text);
		else toast.success(notice.text);
	});

	async function refreshAccount() {
		await qc.invalidateQueries({ queryKey: ['account'] });
		await qc.invalidateQueries({ queryKey: ['me'] });
	}

	async function submitProfile(code?: string) {
		const updated = await apiPatch<Account>('/api/v1/account', {
			username: fullName.trim(),
			email: email.trim(),
			code
		});
		fullName = updated.username;
		email = updated.email ?? '';
		toast.success(
			updated.email_verified ? 'Account updated' : 'Account updated. Verification email sent.'
		);
		await refreshAccount();
	}

	async function saveProfile(e: SubmitEvent) {
		e.preventDefault();
		if (account.data?.two_factor_enabled) {
			pendingMfa = submitProfile;
			mfaOpen = true;
			return;
		}
		profileLoading = true;
		try {
			await submitProfile();
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Update failed');
		} finally {
			profileLoading = false;
		}
	}

	async function sendVerificationEmail() {
		verificationLoading = true;
		try {
			const res = await apiPost<MessageResponse>('/api/v1/account/email/verification');
			toast.success(res.message ?? 'Verification email sent');
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Could not send verification email');
		} finally {
			verificationLoading = false;
		}
	}

	async function submitPassword(code?: string) {
		await apiPost('/api/v1/account/password', {
			current_password: currentPassword,
			new_password: newPassword,
			code
		});
		const hadPassword = account.data?.has_password;
		currentPassword = '';
		newPassword = '';
		toast.success(hadPassword ? 'Password changed' : 'Password added');
		await refreshAccount();
	}

	async function changePassword(e: SubmitEvent) {
		e.preventDefault();
		if (account.data?.two_factor_enabled) {
			pendingMfa = submitPassword;
			mfaOpen = true;
			return;
		}
		passwordLoading = true;
		try {
			await submitPassword();
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Password update failed');
		} finally {
			passwordLoading = false;
		}
	}

	async function handleMfaConfirm(code: string) {
		if (!pendingMfa) return;
		// Throws on failure so the modal surfaces the error and stays open.
		await pendingMfa(code);
		pendingMfa = null;
	}

	async function startTotpSetup() {
		setupLoading = true;
		recoveryCodes = [];
		try {
			setup = await apiPost<TotpSetup>('/api/v1/account/2fa/setup');
			setupCode = '';
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Setup failed');
		} finally {
			setupLoading = false;
		}
	}

	async function confirmTotp(e: SubmitEvent) {
		e.preventDefault();
		confirmLoading = true;
		try {
			const res = await apiPost<TotpEnableResponse>('/api/v1/account/2fa/enable', {
				code: setupCode
			});
			recoveryCodes = res.recovery_codes;
			setup = null;
			setupCode = '';
			toast.success('Authenticator enabled');
			await refreshAccount();
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Verification failed');
		} finally {
			confirmLoading = false;
		}
	}

	async function disableTotp(e: SubmitEvent) {
		e.preventDefault();
		disableLoading = true;
		try {
			await apiPost('/api/v1/account/2fa/disable', {
				current_password: disablePassword || undefined,
				code: disableCode
			});
			disablePassword = '';
			disableCode = '';
			recoveryCodes = [];
			setup = null;
			toast.success('Authenticator disabled');
			await refreshAccount();
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Disable failed');
		} finally {
			disableLoading = false;
		}
	}

	async function unlinkGoogle() {
		googleLoading = true;
		try {
			await apiPost<Account>('/api/v1/account/google/unlink');
			toast.success('Google account disconnected');
			await refreshAccount();
		} catch (err) {
			toast.error(err instanceof Error ? err.message : 'Disconnect failed');
		} finally {
			googleLoading = false;
		}
	}

	async function copyRecoveryCodes() {
		if (!recoveryCodes.length) return;
		await navigator.clipboard?.writeText(recoveryCodes.join('\n'));
		copiedCodes = true;
		setTimeout(() => (copiedCodes = false), 1800);
	}
</script>

<section class="grid w-full gap-12">
	{#if account.isLoading}
		<div class="grid min-h-40 place-items-center">
			<CircleNotch size={24} class="animate-spin text-secondary" />
		</div>
	{:else if account.data}
		<div class="grid items-start gap-12 lg:grid-cols-2">
			<form onsubmit={saveProfile} class="grid gap-4">
				<div class="flex items-center gap-3 border-b border-gray-200 pb-4 dark:border-gray-800">
					<User size={24} weight="bold" class="text-secondary shrink-0" />
					<h2 class="text-xl font-bold tracking-tight text-primary dark:text-gray-50">Profile</h2>
					{#if account.data.email_verified}
						<span class="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-700 dark:text-emerald-300">
							<CheckCircle size={14} weight="fill" />
							Verified
						</span>
					{:else}
						<span class="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/10 px-2.5 py-1 text-xs font-bold text-amber-700 dark:text-amber-300">
							<WarningCircle size={14} weight="fill" />
							Unverified
						</span>
					{/if}
				</div>

				<Input id="settings-name" label="Full name" bind:value={fullName} icon={User} required />
				<Input
					id="settings-email"
					label="Email"
					type="email"
					bind:value={email}
					icon={EnvelopeSimple}
					required
					disabled={account.data.email_locked}
				/>

				<div class="mt-1 flex flex-wrap items-center gap-3">
					{#if profileChanged}
						<Button type="submit" disabled={profileLoading} class="w-max">
							Save profile
						</Button>
					{/if}

					{#if !account.data.email_verified}
						<Button
							ghost
							type="button"
							onclick={sendVerificationEmail}
							disabled={verificationLoading}
							class="w-max"
						>
							Send verification
						</Button>
					{/if}
				</div>
			</form>

			<form onsubmit={changePassword} class="grid gap-4">
				<div class="flex items-center gap-3 border-b border-gray-200 pb-4 dark:border-gray-800">
					<Password size={24} weight="bold" class="text-secondary shrink-0" />
					<h2 class="text-xl font-bold tracking-tight text-primary dark:text-gray-50">Password</h2>
				</div>

				{#if account.data.has_password}
					<InputPassword
						id="settings-current-password"
						label="Current password"
						bind:value={currentPassword}
						icon={LockKey}
						autocomplete="current-password"
						required
					/>
				{/if}
				<InputPassword
					id="settings-new-password"
					label="New password"
					bind:value={newPassword}
					icon={Key}
					autocomplete="new-password"
					minlength={8}
					required
				/>

				{#if passwordChanged}
					<Button type="submit" disabled={passwordLoading} class="mt-1 w-max">
						{account.data.has_password ? 'Change password' : 'Add password'}
					</Button>
				{/if}
			</form>
		</div>

		<div class="grid items-start gap-12 lg:grid-cols-2">
			<div class="grid gap-4">
				<div class="flex items-center gap-3 border-b border-gray-200 pb-4 dark:border-gray-800">
					<GoogleLogoIcon size={24} weight="bold" class="text-secondary shrink-0" />
					<h2 class="text-xl font-bold tracking-tight text-primary dark:text-gray-50">Google</h2>
					{#if account.data.google_linked}
						<span class="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-700 dark:text-emerald-300">
							<CheckCircle size={14} weight="fill" />
							Connected
						</span>
					{:else}
						<span class="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/10 px-2.5 py-1 text-xs font-bold text-amber-700 dark:text-amber-300">
							<WarningCircle size={14} weight="fill" />
							Not connected
						</span>
					{/if}
				</div>

				{#if account.data.google_linked}
					<Button
						type="button"
						onclick={unlinkGoogle}
						disabled={googleLoading}
						class="w-max"
					>
						Disconnect Google
					</Button>
				{:else}
					<a
						href="/api/v1/auth/google/start?mode=link&next=/settings"
						class="inline-flex h-10 w-max items-center justify-center gap-2 rounded-lg bg-secondary px-3.5 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:bg-secondary/90 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/30 active:scale-[0.98]"
					>
						<span>Connect Google</span>
					</a>
				{/if}
			</div>

			<div class="grid gap-4">
				<div class="flex items-center gap-3 border-b border-gray-200 pb-4 dark:border-gray-800">
					<ShieldCheck size={24} weight="fill" class="text-secondary shrink-0" />
					<h2 class="text-xl font-bold tracking-tight text-primary dark:text-gray-50">Authenticator</h2>
					{#if account.data.two_factor_enabled}
						<span class="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-700 dark:text-emerald-300">
							<CheckCircle size={14} weight="fill" />
							Enabled
						</span>
					{:else}
						<span class="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/10 px-2.5 py-1 text-xs font-bold text-amber-700 dark:text-amber-300">
							<WarningCircle size={14} weight="fill" />
							Disabled
						</span>
					{/if}
				</div>

				{#if recoveryCodes.length}
					<div class="grid gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3">
						<div class="flex items-center justify-between gap-3">
							<h3 class="text-sm font-bold text-emerald-800 dark:text-emerald-200">Recovery codes</h3>
							<Button ghost type="button" onclick={copyRecoveryCodes} class="h-8">
								{copiedCodes ? 'Copied' : 'Copy'}
							</Button>
						</div>
						<div class="grid grid-cols-2 gap-1.5 text-sm font-bold tracking-wide text-emerald-900 dark:text-emerald-100 sm:grid-cols-4">
							{#each recoveryCodes as code}
								<code class="rounded bg-white/70 px-2 py-1 text-center dark:bg-gray-950/60">{code}</code>
							{/each}
						</div>
					</div>
				{/if}

				{#if !account.data.two_factor_enabled}
					{#if setup}
						<form onsubmit={confirmTotp} class="grid gap-3">
							<div class="flex flex-col gap-3 sm:flex-row">
								{#if setup.qr_data_url}
									<img
										src={setup.qr_data_url}
										alt="Authenticator QR code"
										class="size-40 rounded-lg border border-gray-200 bg-white p-2 dark:border-gray-800"
									/>
								{:else}
									<div class="grid size-40 place-items-center rounded-lg border border-gray-200 bg-gray-50 text-gray-400 dark:border-gray-800 dark:bg-gray-950">
										<QrCode size={48} />
									</div>
								{/if}
								<div class="min-w-0 flex-1">
									<p class="mb-1 text-[11px] font-semibold uppercase tracking-wide text-primary/60 dark:text-gray-400">
										Setup key
									</p>
									<code class="block break-all rounded-lg bg-gray-100 p-3 text-sm font-bold text-primary dark:bg-gray-950 dark:text-gray-100">
										{setup.secret}
									</code>
								</div>
							</div>
							<Input
								id="settings-2fa-code"
								label="Verification code"
								bind:value={setupCode}
								icon={Key}
								autocomplete="one-time-code"
								inputmode="numeric"
								required
							/>
							<Button type="submit" disabled={confirmLoading} class="w-max">
								Enable 2FA
							</Button>
						</form>
					{:else}
						<Button type="button" onclick={startTotpSetup} disabled={setupLoading} class="w-max">
							Set up authenticator
						</Button>
					{/if}
				{:else}
					<form onsubmit={disableTotp} class="grid gap-3">
						{#if account.data.has_password}
							<InputPassword
								id="settings-disable-password"
								label="Current password"
								bind:value={disablePassword}
								icon={LockKey}
								autocomplete="current-password"
								required
							/>
						{/if}
						<Input
							id="settings-disable-code"
							label="Verification code"
							bind:value={disableCode}
							icon={Key}
							autocomplete="one-time-code"
							inputmode="numeric"
							required
						/>
						{#if disableTotpChanged}
							<Button
								type="submit"
								disabled={disableLoading}
								class="w-max"
							>
								Disable 2FA
							</Button>
						{/if}
					</form>
				{/if}
			</div>
		</div>

		<MfaModal bind:open={mfaOpen} onconfirm={handleMfaConfirm} />
	{/if}
</section>
