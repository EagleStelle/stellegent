<script lang="ts">
	import { goto } from "$app/navigation";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiDelete, apiGet, apiPatch, apiPost } from "$lib/api/client";
	import type { EditableRole, ManagedUser, User } from "$lib/types";
	import Input from "$lib/components/ui/Input.svelte";
	import InputPassword from "$lib/components/ui/InputPassword.svelte";
	import Modal from "$lib/components/ui/Modal.svelte";
	import ComboBox from "$lib/components/ui/ComboBox.svelte";
	import Button from "$lib/components/ui/Button.svelte";
	import {
		CaretDown,
		CaretUp,
		CircleNotch,
		FloppyDisk,
		MagnifyingGlass,
		PencilSimple,
		Plus,
		Prohibit,
		ShieldCheck,
		Trash,
		User as UserIcon,
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
		if (me.isError || users.isError) goto("/");
		if (me.data && me.data.role !== "admin") goto("/lectures");
	});

	type RoleFilter = "all" | "prof" | "student";
	type SortCol = "username" | "email" | "role" | "status";

	let search = $state("");
	let roleFilter = $state<RoleFilter>("all");
	let sortCol = $state<SortCol>("username");
	let sortDir = $state<"asc" | "desc">("asc");

	let addOpen = $state(false);
	let newUsername = $state("");
	let newEmail = $state("");
	let newPassword = $state("");
	let newRole = $state<EditableRole>("prof");
	let creating = $state(false);
	let addError = $state("");

	let editing = $state<ManagedUser | null>(null);
	let editOpen = $state(false);
	let draftUsername = $state("");
	let draftEmail = $state("");
	let draftPassword = $state("");
	let draftRole = $state<EditableRole>("prof");
	let saving = $state(false);
	let editError = $state("");

	let busyId = $state<number | null>(null);
	let error = $state("");

	const visible = $derived.by(() => {
		const q = search.trim().toLowerCase();
		const rows = (users.data ?? []).filter((u) => {
			if (u.role === "admin") return false;
			if (roleFilter !== "all" && u.role !== roleFilter) return false;
			if (!q) return true;
			return (
				u.username.toLowerCase().includes(q) ||
				(u.email ?? "").toLowerCase().includes(q)
			);
		});
		const rank = (r: string) => (r === "admin" ? 0 : r === "prof" ? 1 : 2);
		const dir = sortDir === "asc" ? 1 : -1;
		return [...rows].sort((a, b) => {
			let cmp = 0;
			switch (sortCol) {
				case "email":
					cmp = (a.email ?? "").localeCompare(b.email ?? "");
					break;
				case "role":
					cmp = rank(a.role) - rank(b.role);
					break;
				case "status":
					cmp = Number(a.disabled) - Number(b.disabled);
					break;
				default:
					cmp = 0;
			}
			if (cmp === 0) cmp = a.username.localeCompare(b.username);
			return cmp * dir;
		});
	});

	function setSort(col: SortCol) {
		if (sortCol === col) {
			sortDir = sortDir === "asc" ? "desc" : "asc";
		} else {
			sortCol = col;
			sortDir = "asc";
		}
	}

	function roleLabel(role: string) {
		if (role === "admin") return "Superadmin";
		if (role === "prof") return "Faculty";
		return "Student";
	}

	async function refreshUsers() {
		await qc.invalidateQueries({ queryKey: ["admin-users"] });
		await qc.invalidateQueries({ queryKey: ["course-options"] });
	}

	function openAdd() {
		newUsername = "";
		newEmail = "";
		newPassword = "";
		newRole = "prof";
		addError = "";
		addOpen = true;
	}

	async function createUser(e: SubmitEvent) {
		e.preventDefault();
		creating = true;
		addError = "";
		try {
			await apiPost<ManagedUser>("/api/v1/admin/users", {
				username: newUsername.trim(),
				email: newEmail.trim(),
				password: newPassword,
				role: newRole,
			});
			await refreshUsers();
			addOpen = false;
		} catch (err) {
			addError = err instanceof Error ? err.message : "Create failed";
		} finally {
			creating = false;
		}
	}

	function openEdit(user: ManagedUser) {
		editing = user;
		draftUsername = user.username;
		draftEmail = user.email ?? "";
		draftPassword = "";
		draftRole = user.role === "student" ? "student" : "prof";
		editError = "";
		editOpen = true;
	}

	async function saveUser(e: SubmitEvent) {
		e.preventDefault();
		if (!editing) return;
		saving = true;
		editError = "";
		const body: Record<string, unknown> = { username: draftUsername.trim() };
		if (draftEmail.trim()) body.email = draftEmail.trim();
		if (draftPassword) body.password = draftPassword;
		if (editing.role !== "admin") body.role = draftRole;
		try {
			await apiPatch<ManagedUser>(`/api/v1/admin/users/${editing.id}`, body);
			await refreshUsers();
			editOpen = false;
		} catch (err) {
			editError = err instanceof Error ? err.message : "Save failed";
		} finally {
			saving = false;
		}
	}

	async function toggleDisabled(user: ManagedUser) {
		if (user.role === "admin") return;
		busyId = user.id;
		error = "";
		try {
			await apiPatch<ManagedUser>(`/api/v1/admin/users/${user.id}`, {
				disabled: !user.disabled,
			});
			await refreshUsers();
		} catch (err) {
			error = err instanceof Error ? err.message : "Update failed";
		} finally {
			busyId = null;
		}
	}

	async function removeUser(user: ManagedUser) {
		if (user.role === "admin") return;
		if (!confirm(`Delete ${user.username}?`)) return;
		busyId = user.id;
		error = "";
		try {
			await apiDelete(`/api/v1/admin/users/${user.id}`);
			await refreshUsers();
		} catch (err) {
			error = err instanceof Error ? err.message : "Delete failed";
		} finally {
			busyId = null;
		}
	}

	const selectClass =
		"h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm font-medium text-primary outline-none focus:border-secondary/60 focus:ring-3 focus:ring-secondary/15 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-50";
	const th =
		"cursor-pointer select-none py-2.5 pr-3 text-left text-[11px] font-semibold uppercase tracking-wide text-black dark:text-white";
</script>

<section class="grid gap-4">
	<div class="flex items-center gap-2">
		<div class="relative min-w-0 flex-1">
			<MagnifyingGlass
				size={18}
				class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400"
			/>
			<input
				type="search"
				bind:value={search}
				class="h-10 w-full rounded-lg border border-gray-200 bg-white pl-11 pr-3.5 text-sm text-primary outline-none placeholder:text-gray-400 focus:border-secondary/60 focus:ring-3 focus:ring-secondary/15 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-50"
			/>
		</div>

		<ComboBox
			bind:value={roleFilter}
			class="{selectClass} w-40 shrink-0"
			options={[
				{ value: "all", label: "All roles" },
				{ value: "prof", label: "Faculty" },
				{ value: "student", label: "Student" },
			]}
		/>

		<Button
			variant="icon+text"
			onclick={openAdd}
		>
			{#snippet icon()}
				<Plus size={18} />
			{/snippet}
			Add account
		</Button>
	</div>

	{#if error}
		<p class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400">
			{error}
		</p>
	{/if}

	<div class="overflow-x-auto">
		<table class="w-full border-collapse text-sm">
			<thead>
				<tr class="border-b border-gray-200 dark:border-gray-800">
					{#each [["username", "Full Name"], ["email", "Email"], ["role", "Role"], ["status", "Status"]] as [col, label]}
						<th class={th} onclick={() => setSort(col as SortCol)}>
							<span class="inline-flex items-center gap-1">
								{label}
								{#if sortCol === col}
									{#if sortDir === "asc"}
										<CaretUp size={12} weight="bold" />
									{:else}
										<CaretDown size={12} weight="bold" />
									{/if}
								{/if}
							</span>
						</th>
					{/each}
					<th class="py-2.5 text-right text-[11px] font-semibold uppercase tracking-wide text-black dark:text-white">
						Actions
					</th>
				</tr>
			</thead>
			<tbody>
				{#if users.isLoading}
					<tr><td colspan="5" class="py-6 text-center text-gray-500 dark:text-gray-400">Loading</td></tr>
				{:else}
					{#each visible as user (user.id)}
						<tr
							class="border-b border-gray-100 last:border-0 dark:border-gray-800 {user.disabled
								? 'opacity-55'
								: ''}"
						>
							<td class="py-2.5 pr-3">
								<div class="flex items-center gap-2">
									{#if user.role === "admin"}
										<ShieldCheck size={16} class="shrink-0 text-secondary" />
									{/if}
									<span class="font-semibold text-primary dark:text-gray-50">
										{user.username}
									</span>
								</div>
							</td>
							<td class="py-2.5 pr-3 text-gray-500 dark:text-gray-400">
								{user.email ?? "—"}
							</td>
							<td class="py-2.5 pr-3">
								<span class="rounded-lg bg-gray-100 px-2 py-1 text-xs font-semibold text-gray-600 dark:bg-gray-800 dark:text-gray-300">
									{roleLabel(user.role)}
								</span>
							</td>
							<td class="py-2.5 pr-3">
								{#if user.disabled}
									<span class="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400">
										<span class="size-1.5 rounded-full bg-gray-400"></span>
										Disabled
									</span>
								{:else}
									<span class="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
										<span class="size-1.5 rounded-full bg-emerald-500"></span>
										Enabled
									</span>
								{/if}
							</td>
							<td class="py-2.5">
								<div class="flex items-center justify-end gap-1.5">
									{#if user.role !== "admin"}
										<Button
											variant="icon"
											ghost
											type="button"
											onclick={() => toggleDisabled(user)}
											disabled={busyId === user.id}
											title={user.disabled ? "Enable account" : "Disable account"}
											aria-label={user.disabled ? "Enable account" : "Disable account"}
										>
											{#snippet icon()}
												{#if busyId === user.id}
													<CircleNotch size={16} class="animate-spin" />
												{:else if user.disabled}
													<UserIcon size={16} />
												{:else}
													<Prohibit size={16} />
												{/if}
											{/snippet}
										</Button>
									{/if}
									<Button
										variant="icon"
										ghost
										type="button"
										onclick={() => openEdit(user)}
										title="Edit account"
										aria-label="Edit account"
									>
										{#snippet icon()}
											<PencilSimple size={16} />
										{/snippet}
									</Button>
									{#if user.role !== "admin"}
										<Button
											variant="icon"
											ghost
											danger
											type="button"
											onclick={() => removeUser(user)}
											disabled={busyId === user.id}
											title="Delete account"
											aria-label="Delete account"
										>
											{#snippet icon()}
												<Trash size={16} />
											{/snippet}
										</Button>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>
</section>

<Modal bind:open={addOpen} label="Add account">
	<form
		onsubmit={createUser}
		class="grid w-full max-w-md gap-3 rounded-2xl border border-gray-800 bg-gray-900 p-6"
	>
		<h2 class="text-lg font-bold tracking-tight text-gray-50">Add account</h2>
		<Input id="new-username" label="Full Name" bind:value={newUsername} icon={UserIcon} required />
		<Input id="new-email" label="Email" type="email" bind:value={newEmail} required />
		<InputPassword id="new-password" label="Password" bind:value={newPassword} minlength={8} required />
		<label class="grid gap-1.5 text-sm font-semibold text-gray-100">
			<span>Role</span>
			<ComboBox
				bind:value={newRole}
				class={selectClass}
				options={[
					{ value: "prof", label: "Faculty" },
					{ value: "student", label: "Student" },
				]}
			/>
		</label>
		{#if addError}
			<p class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-400">{addError}</p>
		{/if}
		<Button
			variant="icon+text"
			type="submit"
			disabled={creating}
		>
			{#snippet icon()}
				{#if creating}
					<CircleNotch size={18} class="animate-spin" />
				{:else}
					<Plus size={18} />
				{/if}
			{/snippet}
			Create
		</Button>
	</form>
</Modal>

<Modal bind:open={editOpen} label="Edit account">
	{#if editing}
		<form
			onsubmit={saveUser}
			class="grid w-full max-w-md gap-3 rounded-2xl border border-gray-800 bg-gray-900 p-6"
		>
			<h2 class="text-lg font-bold tracking-tight text-gray-50">Edit {editing.username}</h2>
			<Input id="draft-username" label="Full Name" bind:value={draftUsername} />
			<Input id="draft-email" label="Email" type="email" bind:value={draftEmail} />
			<InputPassword id="draft-password" label="New password" bind:value={draftPassword} />
			<label class="grid gap-1.5 text-sm font-semibold text-gray-100">
				<span>Role</span>
				<ComboBox
					bind:value={draftRole}
					disabled={editing.role === "admin"}
					class={selectClass}
					options={
						editing.role === "admin"
							? [{ value: "prof", label: "Superadmin" }]
							: [
									{ value: "prof", label: "Faculty" },
									{ value: "student", label: "Student" },
							  ]
					}
				/>
			</label>
			{#if editError}
				<p class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-400">{editError}</p>
			{/if}
			<Button
				variant="icon+text"
				type="submit"
				disabled={saving}
				class="mt-1"
			>
				{#snippet icon()}
					{#if saving}
						<CircleNotch size={18} class="animate-spin" />
					{:else}
						<FloppyDisk size={18} />
					{/if}
				{/snippet}
				Save
			</Button>
		</form>
	{/if}
</Modal>
