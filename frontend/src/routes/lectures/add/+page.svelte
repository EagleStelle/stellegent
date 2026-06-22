<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiGet } from "$lib/api/client";
	import type { Course, User, Visibility } from "$lib/types";
	import { ArrowLeft, ImageSquare, CircleNotch } from "phosphor-svelte";
	import Button from "$lib/components/ui/Button.svelte";
	import ComboBox from "$lib/components/ui/ComboBox.svelte";
	import { pendingUpload } from "$lib/upload.svelte";

	const qc = useQueryClient();

	const me = createQuery(() => ({
		queryKey: ["me"],
		queryFn: () => apiGet<User>("/api/v1/me"),
	}));
	const canTeach = $derived(
		me.data?.role === "prof" || me.data?.role === "admin",
	);
	const courses = createQuery(() => ({
		queryKey: ["courses"],
		queryFn: () => apiGet<Course[]>("/api/v1/courses"),
		enabled: canTeach,
	}));

	let fileInput: HTMLInputElement | null = $state(null);
	let saving = $state(false);
	let addError = $state("");
	let draftVisibility = $state<Visibility>("public");
	let draftCourseId = $state(page.url.searchParams.get("courseId") ?? "");

	const file = $derived(pendingUpload.file);

	// Live object URL for the chosen image; revoked whenever the file changes or
	// the page unmounts so we don't leak blob URLs.
	let previewUrl = $state("");
	$effect(() => {
		const f = pendingUpload.file;
		if (!f) {
			previewUrl = "";
			return;
		}
		const url = URL.createObjectURL(f);
		previewUrl = url;
		return () => URL.revokeObjectURL(url);
	});

	// A lecture under a course always inherits the course's visibility; lock the
	// visibility picker while a course is selected. Mirrors /live.
	const selectedCourse = $derived(
		(courses.data ?? []).find((c) => String(c.id) === draftCourseId) ?? null,
	);
	$effect(() => {
		if (selectedCourse) draftVisibility = selectedCourse.visibility;
	});

	function pickImage() {
		fileInput?.click();
	}

	function onFile(e: Event) {
		const input = e.target as HTMLInputElement;
		const selected = input.files?.[0];
		input.value = "";
		if (selected) pendingUpload.set(selected);
	}

	async function submit(e?: SubmitEvent) {
		if (e) e.preventDefault();
		if (!file) {
			addError = "Select an image first";
			return;
		}
		saving = true;
		addError = "";
		const fd = new FormData();
		fd.append("image", file);
		fd.append("visibility", draftVisibility);
		if (draftCourseId) fd.append("course_id", draftCourseId);
		try {
			const res = await fetch("/api/v1/upload", {
				method: "POST",
				credentials: "include",
				body: fd,
			});
			if (!res.ok) {
				const body = (await res.json().catch(() => null)) as { detail?: string } | null;
				throw new Error(body?.detail ?? res.statusText);
			}
			await res.json();
			pendingUpload.clear();
			await qc.invalidateQueries({ queryKey: ["processing-tasks"] });
			goto("/lectures");
		} catch (err) {
			addError = err instanceof Error ? err.message : "Upload failed";
		} finally {
			saving = false;
		}
	}

	function cancel() {
		pendingUpload.clear();
		goto("/lectures");
	}
</script>

<form onsubmit={submit} class="relative flex min-h-[calc(100dvh-2rem)] flex-col">
	<!-- Sticky Header -->
	<header
		class="sticky top-0 z-10 flex items-center gap-4 bg-gray-50 pb-2 dark:bg-gray-950 shadow-sm border-b border-gray-200 dark:border-gray-800"
	>
		<Button
			variant="icon"
			ghost
			type="button"
			onclick={cancel}
			title="Back to lectures"
		>
			{#snippet icon()}
				<ArrowLeft size={20} />
			{/snippet}
		</Button>
		<div>
			<h1 class="text-2xl font-bold tracking-tight text-primary dark:text-gray-50">
				Add Lecture
			</h1>
		</div>
	</header>

	<!-- Scrollable Middle -->
	<div class="flex flex-col flex-1 gap-6 py-4">
		<div class="grid gap-6 md:grid-cols-2">
			<label class="grid gap-1.5">
				<span class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">Course</span>
				<ComboBox
					bind:value={draftCourseId}
					placeholder="No course"
					options={(courses.data ?? []).map((c) => ({
						value: String(c.id),
						label: c.name,
					}))}
				/>
			</label>
			<label class="grid gap-1.5">
				<span class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">Visibility</span>
				<ComboBox
					bind:value={draftVisibility}
					disabled={selectedCourse !== null}
					options={[
						{ value: "public", label: "Public" },
						{ value: "private", label: "Private" },
					]}
				/>
			</label>
		</div>

		<!-- Image preview. Click to choose / replace the image. -->
		<section class="grid content-start gap-3">
			<h2 class="text-[11px] font-semibold uppercase tracking-wide text-primary/60 md:text-xs dark:text-gray-400">
				Image
			</h2>
			<input
				bind:this={fileInput}
				type="file"
				accept=".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
				onchange={onFile}
				class="sr-only"
			/>
			<button
				type="button"
				onclick={pickImage}
				title={file ? "Click to choose a different image" : "Click to select an image"}
				class="group flex min-h-48 w-full items-center justify-center overflow-hidden rounded-lg border border-dashed border-gray-300 bg-white transition-colors hover:border-secondary/60 dark:border-gray-700 dark:bg-gray-950"
			>
				{#if previewUrl}
					<img src={previewUrl} alt="Selected lecture" class="max-h-128 w-full object-contain" />
				{:else}
					<span class="flex flex-col items-center gap-2 px-4 py-12 text-gray-500 dark:text-gray-400">
						<ImageSquare size={32} />
						<span class="text-sm font-medium">Click to select an image</span>
					</span>
				{/if}
			</button>
			{#if file}
				<p class="truncate text-xs text-gray-500 dark:text-gray-400">{file.name}</p>
			{/if}
		</section>

		{#if addError}
			<p class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400">
				{addError}
			</p>
		{/if}
	</div>

	<!-- Sticky Footer -->
	<footer
		class="sticky bottom-20 z-10 flex items-center justify-end gap-3 border-t border-gray-200 bg-gray-50 pt-2 dark:border-gray-800 dark:bg-gray-950 md:bottom-0"
	>
		<Button secondary type="button" onclick={cancel}>Cancel</Button>
		<Button type="submit" disabled={saving || !file}>
			{#if saving}
				<CircleNotch size={18} class="animate-spin" />
				Queuing
			{:else}
				Add
			{/if}
		</Button>
	</footer>
</form>
