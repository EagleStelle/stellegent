<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiPatch, apiGet } from "$lib/api/client";
	import type { ManagedUser, User } from "$lib/types";
	import Input from "$lib/components/ui/Input.svelte";
	import ComboBox from "$lib/components/ui/ComboBox.svelte";
	import Button from "$lib/components/ui/Button.svelte";
	import { ArrowLeft } from "phosphor-svelte";

	const qc = useQueryClient();
	const id = $derived(page.params.id);

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

	const editing = $derived((users.data ?? []).find((u) => String(u.id) === id));

	let draftUsername = $state("");
	let draftEmail = $state("");
	let draftRole = $state<"prof" | "student">("prof");
	let draftStatus = $state<"enabled" | "disabled">("enabled");
	let saving = $state(false);
	let editError = $state("");

	// Seed the drafts once per user
	let seededUserId = "";
	$effect(() => {
		if (!editing) return;
		if (String(editing.id) !== id || seededUserId === id) return;
		seededUserId = id;
		draftUsername = editing.username;
		draftEmail = editing.email ?? "";
		draftRole = editing.role === "student" ? "student" : "prof";
		draftStatus = editing.disabled ? "disabled" : "enabled";
	});

	async function saveUser(e?: SubmitEvent) {
		if (e) e.preventDefault();
		if (!editing) return;
		saving = true;
		editError = "";
		const body: Record<string, unknown> = { username: draftUsername.trim() };
		if (draftEmail.trim()) body.email = draftEmail.trim();
		if (editing.role !== "admin") {
			body.role = draftRole;
			body.disabled = draftStatus === "disabled";
		}
		try {
			await apiPatch<ManagedUser>(`/api/v1/admin/users/${editing.id}`, body);
			await qc.invalidateQueries({ queryKey: ["admin-users"] });
			await qc.invalidateQueries({ queryKey: ["course-options"] });
			goto("/admin");
		} catch (err) {
			editError = err instanceof Error ? err.message : "Save failed";
		} finally {
			saving = false;
		}
	}
</script>

{#if users.isLoading}
	<div
		class="h-[calc(100dvh-2rem)] w-full animate-pulse rounded-2xl bg-gray-200 dark:bg-gray-800"
	></div>
{:else if editing}
	<form
		onsubmit={saveUser}
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
					Edit Account
				</h1>
			</div>
		</header>

		<!-- Scrollable Middle -->
		<div class="flex flex-col flex-1 gap-6 py-4">
			<div class="grid gap-6 md:grid-cols-2">
				<Input
					id="draft-username"
					label="Full Name"
					bind:value={draftUsername}
				/>
				<Input
					id="draft-email"
					label="Email"
					type="email"
					bind:value={draftEmail}
				/>
				<label class="grid gap-1.5">
					<span class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">Role</span>
					<ComboBox
						bind:value={draftRole}
						disabled={editing.role === "admin"}
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
				<label class="grid gap-1.5">
					<span class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">Status</span>
					<ComboBox
						bind:value={draftStatus}
						disabled={editing.role === "admin"}
						options={[
							{ value: "enabled", label: "Enabled" },
							{ value: "disabled", label: "Disabled" },
						]}
					/>
				</label>
			</div>

			{#if editError}
				<p
					class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400"
				>
					{editError}
				</p>
			{/if}
		</div>

		<!-- Sticky Footer -->
		<footer
			class="sticky bottom-20 z-10 flex items-center justify-between gap-4 border-t border-gray-200 bg-gray-50 pt-2 dark:border-gray-800 dark:bg-gray-950 md:bottom-0"
		>
			<div class="min-w-0 flex-1 pl-2">
				<span class="block truncate text-sm font-medium text-gray-500 dark:text-gray-400">
					{draftUsername}
				</span>
			</div>
			<div class="flex shrink-0 items-center gap-3">
				<Button secondary type="button" onclick={() => goto("/admin")}
					>Cancel</Button
				>
				<Button type="submit" disabled={saving}>
					Save Account
				</Button>
			</div>
		</footer>
	</form>
{:else}
	<div class="flex flex-col items-center justify-center py-12 text-center">
		<h2 class="text-lg font-bold text-gray-900 dark:text-gray-50">User not found</h2>
		<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">The user you are looking for does not exist or has been deleted.</p>
		<Button class="mt-4" onclick={() => goto("/admin")}>Back to admin</Button>
	</div>
{/if}
