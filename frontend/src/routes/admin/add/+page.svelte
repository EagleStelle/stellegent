<script lang="ts">
	import { goto } from "$app/navigation";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiPost, apiGet } from "$lib/api/client";
	import type { ManagedUser, User } from "$lib/types";
	import Input from "$lib/components/ui/Input.svelte";
	import InputPassword from "$lib/components/ui/InputPassword.svelte";
	import ComboBox from "$lib/components/ui/ComboBox.svelte";
	import Button from "$lib/components/ui/Button.svelte";
	import { ArrowLeft, Plus, User as UserIcon } from "phosphor-svelte";

	const qc = useQueryClient();

	const me = createQuery(() => ({
		queryKey: ["me"],
		queryFn: () => apiGet<User>("/api/v1/me"),
	}));

	$effect(() => {
		if (me.isError) goto("/");
		if (me.data && me.data.role !== "admin") goto("/lectures");
	});

	let newUsername = $state("");
	let newEmail = $state("");
	let newPassword = $state("");
	let newRole = $state<"prof" | "student">("prof");
	let creating = $state(false);
	let createError = $state("");

	async function createAccount(e: SubmitEvent) {
		e.preventDefault();
		if (!newUsername.trim() || !newEmail.trim() || !newPassword) return;
		creating = true;
		createError = "";
		try {
			await apiPost<ManagedUser>("/api/v1/admin/users", {
				username: newUsername.trim(),
				email: newEmail.trim(),
				password: newPassword,
				role: newRole,
			});
			await qc.invalidateQueries({ queryKey: ["admin-users"] });
			await qc.invalidateQueries({ queryKey: ["course-options"] });
			goto("/admin");
		} catch (err) {
			createError = err instanceof Error ? err.message : "Create failed";
		} finally {
			creating = false;
		}
	}
</script>

<form
	onsubmit={createAccount}
	class="relative flex min-h-[calc(100dvh-2rem)] flex-col"
>
	<!-- Sticky Header -->
	<header
		class="sticky top-0 z-10 flex items-center gap-4 border-b border-gray-200 bg-gray-50 pb-2 dark:border-gray-800 dark:bg-gray-950"
	>
		<Button
			variant="icon"
			ghost
			type="button"
			onclick={() => goto("/admin")}
			title="Back to admin"
		>
			{#snippet icon()}
				<ArrowLeft size={20} />
			{/snippet}
		</Button>
		<div>
			<h1
				class="text-2xl font-bold tracking-tight text-primary dark:text-gray-50"
			>
				Add Account
			</h1>
		</div>
	</header>

	<!-- Scrollable Middle -->
	<div class="flex flex-col flex-1 gap-6 py-4">
		<div class="grid gap-6 md:grid-cols-2">
			<Input
				id="new-username"
				label="Full Name"
				bind:value={newUsername}
				icon={UserIcon}
				required
			/>
			<Input
				id="new-email"
				label="Email"
				type="email"
				bind:value={newEmail}
				required
			/>
			<InputPassword
				id="new-password"
				label="Password"
				bind:value={newPassword}
				minlength={8}
				required
			/>
			<label class="grid gap-1.5">
				<span class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">Role</span>
				<ComboBox
					bind:value={newRole}
					options={[
						{ value: "prof", label: "Faculty" },
						{ value: "student", label: "Student" },
					]}
				/>
			</label>
		</div>

		{#if createError}
			<p
				class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400"
			>
				{createError}
			</p>
		{/if}
	</div>

	<!-- Sticky Footer -->
	<footer
		class="sticky bottom-20 z-10 flex items-center justify-between gap-4 border-t border-gray-200 bg-gray-50 pt-2 dark:border-gray-800 dark:bg-gray-950 md:bottom-0"
	>
		<div class="min-w-0 flex-1 pl-2">
			<span class="block truncate text-sm font-medium text-gray-500 dark:text-gray-400">
				{newUsername}
			</span>
		</div>
		<div class="flex shrink-0 items-center gap-3">
			<Button secondary type="button" onclick={() => goto("/admin")}
				>Cancel</Button
			>
			<Button type="submit" disabled={creating}>
				Create Account
			</Button>
		</div>
	</footer>
</form>
