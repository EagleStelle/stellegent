<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { apiGet, apiPatch, apiPost } from '$lib/api/client';
	import type { Account, MessageResponse, TotpEnableResponse, TotpSetup } from '$lib/types';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import InputPassword from '$lib/components/ui/InputPassword.svelte';
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
	let profileMessage = $state('');
	let profileError = $state('');
	let verificationLoading = $state(false);
	let verificationMessage = $state('');
	let verificationError = $state('');
	let verificationToken = $state('');

	let currentPassword = $state('');
	let newPassword = $state('');
	let passwordLoading = $state(false);
	let passwordMessage = $state('');
	let passwordError = $state('');

	let setup = $state<TotpSetup | null>(null);
	let setupCode = $state('');
	let setupLoading = $state(false);
	let confirmLoading = $state(false);
	let twoFactorError = $state('');
	let twoFactorMessage = $state('');
	let recoveryCodes = $state<string[]>([]);
	let copiedCodes = $state(false);

	let disablePassword = $state('');
	let disableCode = $state('');
	let disableLoading = $state(false);

	let googleLoading = $state(false);
	let googleError = $state('');

	$effect(() => {
		if (account.data && account.data.uid !== hydratedUid) {
			hydratedUid = account.data.uid;
			fullName = account.data.username;
			email = account.data.email ?? '';
		}
	});

	const googleStatus = $derived(page.url.searchParams.get('google'));
	const googleNotice = $derived.by(() => {
		if (googleStatus === 'linked') return 'Google account connected';
		if (googleStatus === 'conflict') return 'That Google account is already connected elsewhere';
		if (googleStatus === 'failed') return 'Google connection failed';
		if (googleStatus === 'login_required') return 'Sign in again before connecting Google';
		if (googleStatus === 'invalid_state') return 'Google connection expired';
		if (googleStatus === 'cancelled') return 'Google connection was cancelled';
		return '';
	});
	const googleNoticeError = $derived(
		['conflict', 'failed', 'login_required', 'invalid_state', 'cancelled'].includes(googleStatus ?? '')
	);

	const panel =
		'rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900';
	const panelTitle = 'text-base font-bold tracking-tight text-primary dark:text-gray-50';
	const panelSub = 'text-sm font-medium text-gray-500 dark:text-gray-400';
	const okNotice =
		'rounded-lg bg-emerald-500/10 px-3 py-2 text-sm font-medium text-emerald-700 dark:text-emerald-300';
	const errorNotice =
		'rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400';

	async function refreshAccount() {
		await qc.invalidateQueries({ queryKey: ['account'] });
		await qc.invalidateQueries({ queryKey: ['me'] });
	}

	async function saveProfile(e: SubmitEvent) {
		e.preventDefault();
		profileLoading = true;
		profileMessage = '';
		profileError = '';
		try {
			const updated = await apiPatch<Account>('/api/v1/account', {
				username: fullName.trim(),
				email: email.trim()
			});
			fullName = updated.username;
			email = updated.email ?? '';
			profileMessage = updated.email_verified ? 'Account updated' : 'Account updated. Verification email sent.';
			await refreshAccount();
		} catch (err) {
			profileError = err instanceof Error ? err.message : 'Update failed';
		} finally {
			profileLoading = false;
		}
	}

	async function sendVerificationEmail() {
		verificationLoading = true;
		verificationMessage = '';
		verificationError = '';
		verificationToken = '';
		try {
			const res = await apiPost<MessageResponse>('/api/v1/account/email/verification');
			verificationMessage = res.message ?? 'Verification email sent';
			verificationToken = res.verification_token ?? '';
		} catch (err) {
			verificationError = err instanceof Error ? err.message : 'Could not send verification email';
		} finally {
			verificationLoading = false;
		}
	}

	async function changePassword(e: SubmitEvent) {
		e.preventDefault();
		passwordLoading = true;
		passwordMessage = '';
		passwordError = '';
		try {
			await apiPost('/api/v1/account/password', {
				current_password: currentPassword,
				new_password: newPassword
			});
			currentPassword = '';
			newPassword = '';
			passwordMessage = account.data?.has_password ? 'Password changed' : 'Password added';
			await refreshAccount();
		} catch (err) {
			passwordError = err instanceof Error ? err.message : 'Password update failed';
		} finally {
			passwordLoading = false;
		}
	}

	async function startTotpSetup() {
		setupLoading = true;
		twoFactorError = '';
		twoFactorMessage = '';
		recoveryCodes = [];
		try {
			setup = await apiPost<TotpSetup>('/api/v1/account/2fa/setup');
			setupCode = '';
		} catch (err) {
			twoFactorError = err instanceof Error ? err.message : 'Setup failed';
		} finally {
			setupLoading = false;
		}
	}

	async function confirmTotp(e: SubmitEvent) {
		e.preventDefault();
		confirmLoading = true;
		twoFactorError = '';
		twoFactorMessage = '';
		try {
			const res = await apiPost<TotpEnableResponse>('/api/v1/account/2fa/enable', {
				code: setupCode
			});
			recoveryCodes = res.recovery_codes;
			setup = null;
			setupCode = '';
			twoFactorMessage = 'Two-factor authentication enabled';
			await refreshAccount();
		} catch (err) {
			twoFactorError = err instanceof Error ? err.message : 'Verification failed';
		} finally {
			confirmLoading = false;
		}
	}

	async function disableTotp(e: SubmitEvent) {
		e.preventDefault();
		disableLoading = true;
		twoFactorError = '';
		twoFactorMessage = '';
		try {
			await apiPost('/api/v1/account/2fa/disable', {
				current_password: disablePassword || undefined,
				code: disableCode
			});
			disablePassword = '';
			disableCode = '';
			recoveryCodes = [];
			setup = null;
			twoFactorMessage = 'Two-factor authentication disabled';
			await refreshAccount();
		} catch (err) {
			twoFactorError = err instanceof Error ? err.message : 'Disable failed';
		} finally {
			disableLoading = false;
		}
	}

	async function unlinkGoogle() {
		googleLoading = true;
		googleError = '';
		try {
			await apiPost<Account>('/api/v1/account/google/unlink');
			await refreshAccount();
		} catch (err) {
			googleError = err instanceof Error ? err.message : 'Disconnect failed';
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

<section class="mx-auto grid w-full max-w-5xl gap-4">
	<div>
		<h1 class="text-2xl font-bold tracking-tight text-primary dark:text-gray-50">Settings</h1>
		<p class="mt-1 text-sm font-medium text-gray-500 dark:text-gray-400">
			Account identity, password, sign-in providers, and two-factor protection.
		</p>
	</div>

	{#if account.isLoading}
		<div class="{panel} grid min-h-40 place-items-center">
			<CircleNotch size={24} class="animate-spin text-secondary" />
		</div>
	{:else if account.data}
		<div class="grid gap-4 lg:grid-cols-[1fr_0.95fr]">
			<form onsubmit={saveProfile} class="{panel} grid gap-3">
				<div class="flex items-start gap-3">
					<div class="grid size-10 shrink-0 place-items-center rounded-lg bg-secondary/10 text-secondary">
						<User size={21} weight="bold" />
					</div>
					<div>
						<h2 class={panelTitle}>Profile</h2>
						<p class={panelSub}>Name and email shown across the app.</p>
					</div>
				</div>

				<Input id="settings-name" label="Full name" bind:value={fullName} icon={User} required />
				<Input
					id="settings-email"
					label="Email"
					type="email"
					bind:value={email}
					icon={EnvelopeSimple}
					required
				/>

				<div class="flex flex-wrap items-center gap-2">
					{#if account.data.email_verified}
						<span class="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-700 dark:text-emerald-300">
							<CheckCircle size={14} weight="fill" />
							Email verified
						</span>
					{:else}
						<span class="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/10 px-2.5 py-1 text-xs font-bold text-amber-700 dark:text-amber-300">
							<WarningCircle size={14} weight="fill" />
							Email unverified
						</span>
						<Button
							variant="icon+text"
							ghost
							type="button"
							onclick={sendVerificationEmail}
							disabled={verificationLoading}
							class="h-8"
						>
							{#snippet icon()}
								{#if verificationLoading}
									<CircleNotch size={16} class="animate-spin" />
								{:else}
									<EnvelopeSimple size={16} />
								{/if}
							{/snippet}
							Send verification
						</Button>
					{/if}
				</div>

				{#if profileError}
					<p class={errorNotice} role="alert">{profileError}</p>
				{:else if profileMessage}
					<p class={okNotice}>{profileMessage}</p>
				{/if}

				{#if verificationError}
					<p class={errorNotice} role="alert">{verificationError}</p>
				{:else if verificationMessage}
					<p class={okNotice}>{verificationMessage}</p>
				{/if}

				{#if verificationToken}
					<a
						href={`/verify-email?token=${encodeURIComponent(verificationToken)}`}
						class="rounded-lg bg-gray-100 px-3 py-2 text-sm font-bold text-primary transition-colors hover:text-secondary dark:bg-gray-950 dark:text-gray-50"
					>
						Open dev verification link
					</a>
				{/if}

				<Button variant="icon+text" type="submit" disabled={profileLoading} class="mt-1 w-max">
					{#snippet icon()}
						{#if profileLoading}
							<CircleNotch size={18} class="animate-spin" />
						{:else}
							<FloppyDisk size={18} />
						{/if}
					{/snippet}
					Save profile
				</Button>
			</form>

			<form onsubmit={changePassword} class="{panel} grid gap-3">
				<div class="flex items-start gap-3">
					<div class="grid size-10 shrink-0 place-items-center rounded-lg bg-secondary/10 text-secondary">
						<Password size={21} weight="bold" />
					</div>
					<div>
						<h2 class={panelTitle}>Password</h2>
						<p class={panelSub}>
							{account.data.has_password ? 'Change your local password.' : 'Add a local password to this account.'}
						</p>
					</div>
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

				{#if passwordError}
					<p class={errorNotice} role="alert">{passwordError}</p>
				{:else if passwordMessage}
					<p class={okNotice}>{passwordMessage}</p>
				{/if}

				<Button variant="icon+text" type="submit" disabled={passwordLoading} class="mt-1 w-max">
					{#snippet icon()}
						{#if passwordLoading}
							<CircleNotch size={18} class="animate-spin" />
						{:else}
							<Key size={18} />
						{/if}
					{/snippet}
					{account.data.has_password ? 'Change password' : 'Add password'}
				</Button>
			</form>
		</div>

		<div class="grid gap-4 lg:grid-cols-[0.95fr_1fr]">
			<div class="{panel} grid gap-3">
				<div class="flex items-start gap-3">
					<div class="grid size-10 shrink-0 place-items-center rounded-lg bg-secondary/10 text-secondary">
						<GoogleLogoIcon size={22} weight="bold" />
					</div>
					<div>
						<h2 class={panelTitle}>Google</h2>
						<p class={panelSub}>
							{account.data.google_linked ? 'Google sign-in is connected.' : 'Connect Google sign-in to this account.'}
						</p>
					</div>
				</div>

				<div class="flex items-center gap-2 text-sm font-semibold">
					{#if account.data.google_linked}
						<CheckCircle size={17} weight="fill" class="text-emerald-500" />
						<span class="text-emerald-700 dark:text-emerald-300">Connected</span>
					{:else}
						<WarningCircle size={17} weight="fill" class="text-amber-500" />
						<span class="text-gray-500 dark:text-gray-400">Not connected</span>
					{/if}
				</div>

				{#if googleNotice}
					<p class={googleNoticeError ? errorNotice : okNotice}>{googleNotice}</p>
				{/if}
				{#if googleError}
					<p class={errorNotice} role="alert">{googleError}</p>
				{/if}

				{#if account.data.google_linked}
					<Button
						variant="icon+text"
						ghost
						danger
						type="button"
						onclick={unlinkGoogle}
						disabled={googleLoading}
						class="w-max"
					>
						{#snippet icon()}
							{#if googleLoading}
								<CircleNotch size={18} class="animate-spin" />
							{:else}
								<LinkBreak size={18} />
							{/if}
						{/snippet}
						Disconnect Google
					</Button>
				{:else}
					<a
						href="/api/v1/auth/google/start?mode=link&next=/settings"
						class="inline-flex h-10 w-max items-center justify-center gap-2 rounded-lg bg-secondary px-3.5 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:bg-secondary/90 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/30 active:scale-[0.98]"
					>
						<GoogleLogoIcon size={18} weight="bold" />
						<span>Connect Google</span>
					</a>
				{/if}
			</div>

			<div class="{panel} grid gap-3">
				<div class="flex items-start gap-3">
					<div class="grid size-10 shrink-0 place-items-center rounded-lg bg-secondary/10 text-secondary">
						<ShieldCheck size={22} weight="fill" />
					</div>
					<div>
						<h2 class={panelTitle}>Authenticator</h2>
						<p class={panelSub}>
							{account.data.two_factor_enabled ? 'Two-factor authentication is enabled.' : 'Protect sign-ins with a six-digit code.'}
						</p>
					</div>
				</div>

				<div class="flex items-center gap-2 text-sm font-semibold">
					{#if account.data.two_factor_enabled}
						<CheckCircle size={17} weight="fill" class="text-emerald-500" />
						<span class="text-emerald-700 dark:text-emerald-300">Enabled</span>
					{:else}
						<WarningCircle size={17} weight="fill" class="text-amber-500" />
						<span class="text-gray-500 dark:text-gray-400">Disabled</span>
					{/if}
				</div>

				{#if twoFactorError}
					<p class={errorNotice} role="alert">{twoFactorError}</p>
				{:else if twoFactorMessage}
					<p class={okNotice}>{twoFactorMessage}</p>
				{/if}

				{#if recoveryCodes.length}
					<div class="grid gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3">
						<div class="flex items-center justify-between gap-3">
							<h3 class="text-sm font-bold text-emerald-800 dark:text-emerald-200">Recovery codes</h3>
							<Button variant="icon+text" ghost type="button" onclick={copyRecoveryCodes} class="h-8">
								{#snippet icon()}
									<CopySimple size={16} />
								{/snippet}
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
							<Button variant="icon+text" type="submit" disabled={confirmLoading} class="w-max">
								{#snippet icon()}
									{#if confirmLoading}
										<CircleNotch size={18} class="animate-spin" />
									{:else}
										<ShieldCheck size={18} />
									{/if}
								{/snippet}
								Enable 2FA
							</Button>
						</form>
					{:else}
						<Button variant="icon+text" type="button" onclick={startTotpSetup} disabled={setupLoading} class="w-max">
							{#snippet icon()}
								{#if setupLoading}
									<CircleNotch size={18} class="animate-spin" />
								{:else}
									<QrCode size={18} />
								{/if}
							{/snippet}
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
						<Button
							variant="icon+text"
							ghost
							danger
							type="submit"
							disabled={disableLoading}
							class="w-max"
						>
							{#snippet icon()}
								{#if disableLoading}
									<CircleNotch size={18} class="animate-spin" />
								{:else}
									<LinkBreak size={18} />
								{/if}
							{/snippet}
							Disable 2FA
						</Button>
					</form>
				{/if}
			</div>
		</div>
	{/if}
</section>
