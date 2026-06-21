<script lang="ts">
	import { goto } from "$app/navigation";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiDelete, apiGet, apiPatch, apiPost } from "$lib/api/client";
	import type { EditableRole, ManagedUser, User } from "$lib/types";
	import Card from "$lib/components/ui/Card.svelte";
	import Input from "$lib/components/ui/Input.svelte";
	import InputPassword from "$lib/components/ui/InputPassword.svelte";
	import {
		CircleNotch,
		FloppyDisk,
		Plus,
		ShieldCheck,
		Trash,
		User as UserIcon,
		UsersThree,
	} from "phosphor-svelte";

	const qc = useQueryClient();

	const me = createQuery(() => ({
		queryKey: ["me"],
		queryFn: () => apiGet<User>("/api/v1/me"),
	}));
	const users = createQuery(() => ({
		queryKey: ["admin-users"],
		queryFn: () => apiGet<ManagedUser[]>("/api/v1/admin/users"),
	}));

	$effect(() => {
		if (me.isError || users.isError) goto("/login");
		if (me.data && me.data.role !== "admin") goto("/");
	});

	let selectedUser = $state<ManagedUser | null>(null);
	let autoSelected = $state(false);
	let newUsername = $state("");
	let newEmail = $state("");
	let newPassword = $state("");
	let newRole = $state<EditableRole>("prof");
	let draftUsername = $state("");
	let draftEmail = $state("");
	let draftPassword = $state("");
	let draftRole = $state<EditableRole>("prof");
	let creating = $state(false);
	let saving = $state(false);
	let error = $state("");

	$effect(() => {
		if (!autoSelected && users.data?.length) {
			autoSelected = true;
			selectUser(users.data[0]);
		}
	});

	function roleLabel(role: string) {
		if (role === "admin") return "Superadmin";
		if (role === "prof") return "Faculty";
		return "Student";
	}

	function selectUser(user: ManagedUser) {
		selectedUser = user;
		draftUsername = user.username;
		draftEmail = user.email ?? "";
		draftPassword = "";
		draftRole = user.role === "student" ? "student" : "prof";
		error = "";
	}

	async function refreshUsers() {
		await qc.invalidateQueries({ queryKey: ["admin-users"] });
		await qc.invalidateQueries({ queryKey: ["course-options"] });
	}

	async function createUser(e: SubmitEvent) {
		e.preventDefault();
		creating = true;
		error = "";
		try {
			const created = await apiPost<ManagedUser>("/api/v1/admin/users", {
				username: newUsername.trim(),
				email: newEmail.trim() || null,
				password: newPassword,
				role: newRole,
			});
			newUsername = "";
			newEmail = "";
			newPassword = "";
			newRole = "prof";
			await refreshUsers();
			selectUser(created);
		} catch (err) {
			error = err instanceof Error ? err.message : "Create failed";
		} finally {
			creating = false;
		}
	}

	async function saveUser() {
		if (!selectedUser) return;
		saving = true;
		error = "";
		const body: Record<string, unknown> = {
			username: draftUsername.trim(),
		};
		if (draftEmail.trim()) body.email = draftEmail.trim();
		if (draftPassword) body.password = draftPassword;
		if (selectedUser.role !== "admin") body.role = draftRole;
		try {
			const saved = await apiPatch<ManagedUser>(
				`/api/v1/admin/users/${selectedUser.id}`,
				body,
			);
			await refreshUsers();
			selectUser(saved);
		} catch (err) {
			error = err instanceof Error ? err.message : "Save failed";
		} finally {
			saving = false;
		}
	}

	async function removeUser() {
		if (!selectedUser || selectedUser.role === "admin") return;
		if (!confirm(`Delete ${selectedUser.username}?`)) return;
		error = "";
		try {
			await apiDelete(`/api/v1/admin/users/${selectedUser.id}`);
			selectedUser = null;
			autoSelected = false;
			await refreshUsers();
		} catch (err) {
			error = err instanceof Error ? err.message : "Delete failed";
		}
	}
</script>

<section class="grid gap-4 xl:grid-cols-[24rem_minmax(0,1fr)]">
	<div class="grid content-start gap-4">
		<Card class="grid gap-3">
			<div class="flex items-center gap-2">
				<UsersThree size={18} class="text-secondary" />
				<h1 class="text-lg font-bold tracking-tight text-primary dark:text-gray-50">Accounts</h1>
			</div>

			<form onsubmit={createUser} class="grid gap-3">
				<Input id="new-username" label="Username" bind:value={newUsername} icon={UserIcon} required />
				<Input id="new-email" label="Email" type="email" bind:value={newEmail} />
				<InputPassword
					id="new-password"
					label="Password"
					bind:value={newPassword}
					minlength={8}
					required
				/>
				<label class="grid gap-1.5 text-sm font-semibold text-primary dark:text-gray-100">
					<span>Role</span>
					<select
						bind:value={newRole}
						class="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm font-medium outline-none focus:border-secondary/60 focus:ring-3 focus:ring-secondary/15 dark:border-gray-800 dark:bg-gray-950"
					>
						<option value="prof">Faculty</option>
						<option value="student">Student</option>
					</select>
				</label>
				<button
					type="submit"
					disabled={creating}
					class="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-3.5 text-sm font-semibold text-white transition-all hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/30 disabled:pointer-events-none disabled:opacity-60"
				>
					{#if creating}
						<CircleNotch size={18} class="animate-spin" />
					{:else}
						<Plus size={18} />
					{/if}
					Create
				</button>
			</form>
		</Card>

		<div class="grid gap-2">
			{#if users.isLoading}
				<p class="text-sm text-gray-500 dark:text-gray-400">Loading</p>
			{:else}
				{#each users.data ?? [] as user (user.id)}
					<button
						onclick={() => selectUser(user)}
						class="rounded-lg border p-3 text-left transition-all {selectedUser?.id === user.id
							? 'border-secondary bg-secondary/10'
							: 'border-gray-200 bg-white hover:border-secondary/40 dark:border-gray-800 dark:bg-gray-900'}"
					>
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<h2 class="truncate text-sm font-semibold text-primary dark:text-gray-50">
									{user.username}
								</h2>
								<p class="mt-1 truncate text-xs text-gray-500 dark:text-gray-400">
									{user.email ?? "No email"}
								</p>
							</div>
							<span class="rounded-lg bg-gray-100 px-2 py-1 text-xs font-semibold text-gray-600 dark:bg-gray-800 dark:text-gray-300">
								{roleLabel(user.role)}
							</span>
						</div>
					</button>
				{/each}
			{/if}
		</div>
	</div>

	<Card class="min-h-[32rem]">
		{#if selectedUser}
			<div class="grid gap-5">
				<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
					<div>
						<div class="flex items-center gap-2">
							{#if selectedUser.role === "admin"}
								<ShieldCheck size={20} class="text-secondary" />
							{/if}
							<h2 class="text-xl font-bold tracking-tight text-primary dark:text-gray-50">
								{selectedUser.username}
							</h2>
						</div>
						<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
							{roleLabel(selectedUser.role)}
						</p>
					</div>
					<div class="flex gap-2">
						<button
							onclick={saveUser}
							disabled={saving}
							class="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-3.5 text-sm font-semibold text-white transition-all hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/30 disabled:pointer-events-none disabled:opacity-60"
						>
							{#if saving}
								<CircleNotch size={18} class="animate-spin" />
							{:else}
								<FloppyDisk size={18} />
							{/if}
							Save
						</button>
						{#if selectedUser.role !== "admin"}
							<button
								onclick={removeUser}
								class="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-secondary/10 px-3.5 text-sm font-semibold text-secondary transition-all hover:bg-secondary/20 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-secondary/30"
							>
								<Trash size={18} />
								Delete
							</button>
						{/if}
					</div>
				</div>

				{#if error}
					<p class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400">
						{error}
					</p>
				{/if}

				<div class="grid gap-3 md:grid-cols-2">
					<Input id="draft-username" label="Username" bind:value={draftUsername} />
					<Input id="draft-email" label="Email" type="email" bind:value={draftEmail} />
					<InputPassword id="draft-password" label="New password" bind:value={draftPassword} />
					<label class="grid gap-1.5 text-sm font-semibold text-primary dark:text-gray-100">
						<span>Role</span>
						<select
							bind:value={draftRole}
							disabled={selectedUser.role === "admin"}
							class="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm font-medium outline-none focus:border-secondary/60 focus:ring-3 focus:ring-secondary/15 disabled:opacity-60 dark:border-gray-800 dark:bg-gray-950"
						>
							{#if selectedUser.role === "admin"}
								<option value="prof">Superadmin</option>
							{:else}
								<option value="prof">Faculty</option>
								<option value="student">Student</option>
							{/if}
						</select>
					</label>
				</div>
			</div>
		{:else}
			<div class="flex h-64 items-center justify-center text-sm text-gray-500 dark:text-gray-400">
				No account selected
			</div>
		{/if}
	</Card>
</section>
