<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiGet, apiPatch } from "$lib/api/client";
	import type {
		Course,
		CourseOptions,
		LectureDetail,
		User,
		Visibility,
	} from "$lib/types";
	import {
		Trash,
		PencilSimple,
		FloppyDisk,
		CalendarBlank,
		UserCircle,
		GlobeHemisphereWest,
		LockSimple,
		FilePdf,
		FileDoc,
		FileTxt,
		BookOpen,
		UsersThree,
	} from "phosphor-svelte";
	import Card from "$lib/components/ui/Card.svelte";
	import ImageModal from "$lib/components/modal/Image.svelte";
	import TextModal from "$lib/components/modal/Text.svelte";
	import Modal from "$lib/components/ui/Modal.svelte";
	import Button from "$lib/components/ui/Button.svelte";
	import Select from "$lib/components/ui/Select.svelte";

	const qc = useQueryClient();
	const id = $derived(page.params.id);

	const me = createQuery(() => ({
		queryKey: ["me"],
		queryFn: () => apiGet<User>("/api/v1/me"),
	}));
	const lecture = createQuery(() => ({
		queryKey: ["lecture", id],
		queryFn: () => apiGet<LectureDetail>(`/api/v1/lectures/${id}`),
	}));

	const canManage = $derived(
		me.data?.role === "admin" ||
			(me.data?.role === "prof" &&
				lecture.data?.owner_user_id === me.data.uid),
	);
	const canTeach = $derived(
		me.data?.role === "prof" || me.data?.role === "admin",
	);
	const courses = createQuery(() => ({
		queryKey: ["courses"],
		queryFn: () => apiGet<Course[]>("/api/v1/courses"),
		enabled: canTeach,
	}));
	const options = createQuery(() => ({
		queryKey: ["course-options"],
		queryFn: () => apiGet<CourseOptions>("/api/v1/courses/options"),
		enabled: canTeach,
	}));

	let editOpen = $state(false);
	let saving = $state(false);
	let editError = $state("");
	let draftTitle = $state("");
	let draftSummary = $state("");
	let draftText = $state("");
	let draftVisibility = $state<Visibility>("public");
	let draftCourseId = $state("");
	let draftOwnerId = $state("");
	let draftStudentIds = $state<number[]>([]);

	$effect(() => {
		if (!lecture.data) return;
		draftTitle = lecture.data.course_name ?? "";
		draftSummary = lecture.data.summary ?? "";
		draftText = lecture.data.corrected_text ?? "";
		draftVisibility = lecture.data.visibility;
		draftCourseId = lecture.data.course_id
			? String(lecture.data.course_id)
			: "";
		draftOwnerId = lecture.data.owner_user_id
			? String(lecture.data.owner_user_id)
			: "";
		draftStudentIds = [...lecture.data.student_ids];
	});

	const downloads = [
		{ type: "pdf", label: "PDF", Icon: FilePdf },
		{ type: "docx", label: "DOCX", Icon: FileDoc },
		{ type: "txt", label: "TXT", Icon: FileTxt },
	];

	const fileUrl = (type: string) =>
		`/api/v1/lectures/${id}/file?type=${type}`;

	/**
	 * Fetch the file as a blob and save it. Using a plain <a href> lets the
	 * SvelteKit client router intercept the same-origin link, which breaks the
	 * download (notably for .txt). A blob + credentials avoids that entirely.
	 */
	async function downloadFile(type: string) {
		const res = await fetch(fileUrl(type), { credentials: "include" });
		if (!res.ok) return;
		const blob = await res.blob();
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		const base = (lecture.data?.course_name ?? "lecture").replace(
			/[^\w-]+/g,
			"_",
		);
		a.href = url;
		a.download = `${base}.${type}`;
		document.body.appendChild(a);
		a.click();
		a.remove();
		URL.revokeObjectURL(url);
	}

	async function remove() {
		if (!confirm("Delete this lecture?")) return;
		await fetch(`/api/v1/lectures/${id}`, {
			method: "DELETE",
			credentials: "include",
		});
		qc.invalidateQueries({ queryKey: ["lectures"] });
		goto("/lectures");
	}

	function toggleStudent(studentId: number) {
		draftStudentIds = draftStudentIds.includes(studentId)
			? draftStudentIds.filter((sid) => sid !== studentId)
			: [...draftStudentIds, studentId];
	}

	async function saveLecture() {
		saving = true;
		editError = "";
		const body: Record<string, unknown> = {
			course_name: draftTitle.trim() || null,
			course_id: draftCourseId ? Number(draftCourseId) : null,
			visibility: draftVisibility,
			summary: draftSummary,
			corrected_text: draftText,
			student_ids: draftStudentIds,
		};
		if (me.data?.role === "admin") {
			body.owner_user_id = draftOwnerId ? Number(draftOwnerId) : null;
		}
		try {
			await apiPatch<LectureDetail>(`/api/v1/lectures/${id}`, body);
			await qc.invalidateQueries({ queryKey: ["lecture", id] });
			await qc.invalidateQueries({ queryKey: ["lectures"] });
			editOpen = false;
		} catch (err) {
			editError = err instanceof Error ? err.message : "Save failed";
		} finally {
			saving = false;
		}
	}

	function formatDate(value: string) {
		return new Date(value).toLocaleString(undefined, {
			weekday: "short",
			month: "short",
			day: "numeric",
			hour: "numeric",
			minute: "2-digit",
		});
	}

	const pill =
		"inline-flex h-8 shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg border px-2.5 sm:px-3 text-sm font-medium outline-none transition-all duration-200 active:scale-[0.98] focus-visible:ring-3";
</script>

{#if lecture.isLoading}
	<section class="flex flex-col gap-4">
		<div class="space-y-2">
			<div
				class="h-4 w-28 animate-pulse rounded-lg bg-gray-200 dark:bg-gray-800"
			></div>
			<div
				class="h-8 w-72 max-w-full animate-pulse rounded-lg bg-gray-200 dark:bg-gray-800"
			></div>
		</div>
		<div class="grid gap-4 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
			<div
				class="aspect-video animate-pulse rounded-2xl bg-gray-200 dark:bg-gray-800"
			></div>
			<div class="flex flex-col gap-4">
				<div
					class="h-32 animate-pulse rounded-xl bg-gray-200 dark:bg-gray-800"
				></div>
				<div
					class="h-32 animate-pulse rounded-xl bg-gray-200 dark:bg-gray-800"
				></div>
			</div>
		</div>
	</section>
{:else if lecture.isError}
	<Card class="mx-auto mt-16 flex max-w-md flex-col items-center gap-4 text-center">
		<h1 class="text-lg font-semibold text-primary dark:text-gray-50">
			Lecture not found
		</h1>
		<p class="text-sm text-gray-500 dark:text-gray-400">
			It may have been removed.
		</p>
		<a
			href="/lectures"
			class="{pill} border-transparent bg-primary text-white hover:bg-primary/90 focus-visible:ring-secondary/30"
		>
			Back to lectures
		</a>
	</Card>
{:else if lecture.data}
	{@const lec = lecture.data}
	<section
		class="flex flex-col gap-4 lg:h-[calc(100dvh-2rem)] lg:max-h-[calc(100dvh-2rem)]"
	>
		<header
			class="flex shrink-0 flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
		>
			<div class="flex flex-col gap-2">
				<div class="flex items-center gap-3">
					<h1
						class="text-2xl font-bold tracking-tight text-balance text-primary dark:text-gray-50"
					>
						{lec.course_title ?? lec.course_name ?? "Lecture"}
					</h1>
					<span
						class="flex shrink-0 items-center gap-1.5 rounded-full bg-secondary/10 px-2.5 py-1 text-xs font-semibold text-secondary"
					>
						{#if lec.visibility === "public"}
							<GlobeHemisphereWest size={14} />
							<span>Public</span>
						{:else}
							<LockSimple size={14} />
							<span>Private</span>
						{/if}
					</span>
				</div>
				<div
					class="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm font-medium text-gray-500 dark:text-gray-400"
				>
					<div
						class="flex shrink-0 items-center gap-1.5 whitespace-nowrap"
					>
						<UserCircle size={16} />
						<span
							>{lec.owner_username
								? `Prof. ${lec.owner_username}`
								: "Prof. Unknown"}</span
						>
					</div>
					<span
						class="hidden text-gray-300 sm:inline dark:text-gray-600"
						>•</span
					>
					{#if lec.course_title}
						<div
							class="flex shrink-0 items-center gap-1.5 whitespace-nowrap"
						>
							<BookOpen size={16} />
							{lec.course_title}
						</div>
						<span
							class="hidden text-gray-300 sm:inline dark:text-gray-600"
							>•</span
						>
					{/if}
					<div
						class="flex shrink-0 items-center gap-1.5 whitespace-nowrap"
					>
						<CalendarBlank size={14} weight="bold" />
						{formatDate(lec.captured_at)}
					</div>
				</div>
			</div>

			<div class="flex flex-wrap items-center gap-2">
				{#each downloads as d (d.type)}
					<Button
						variant="icon+text"
						onclick={() => downloadFile(d.type)}
						class="!bg-white !text-gray-700 hover:!text-secondary border border-gray-200 dark:border-gray-800 dark:!bg-gray-900 dark:!text-gray-200 hover:border-secondary/40"
						title={`Download ${d.label}`}
					>
						{#snippet icon()}
							<d.Icon size={16} />
						{/snippet}
						{d.label}
					</Button>
				{/each}
				{#if canManage}
					<div class="mx-1 h-6 w-px rounded-full bg-gray-200 dark:bg-gray-800"></div>
					<Button
						variant="icon+text"
						onclick={() => (editOpen = !editOpen)}
						class="!bg-white !text-gray-700 hover:!text-secondary border border-gray-200 dark:border-gray-800 dark:!bg-gray-900 dark:!text-gray-200 hover:border-secondary/40"
						title="Edit lecture"
					>
						{#snippet icon()}
							<PencilSimple size={16} />
						{/snippet}
						Edit
					</Button>
					<Button
						variant="icon+text"
						onclick={remove}
						class="!bg-secondary/10 !text-secondary hover:!bg-secondary/20"
						title="Delete lecture"
					>
						{#snippet icon()}
							<Trash size={16} />
						{/snippet}
						Delete
					</Button>
				{/if}
			</div>
		</header>

		{#if canManage}
			<Modal bind:open={editOpen} label="Edit Lecture">
				<Card class="grid w-full max-w-4xl shrink-0 gap-4 overflow-y-auto max-h-[90dvh]">
					<h2 class="text-xl font-bold text-primary dark:text-gray-50">Edit Lecture</h2>
					<div class="grid gap-3 md:grid-cols-3">
					<label
						class="grid gap-1.5 text-sm font-semibold text-primary dark:text-gray-100"
					>
						<span>Title</span>
						<input
							bind:value={draftTitle}
							class="h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm font-medium outline-none focus:border-secondary/60 focus:ring-3 focus:ring-secondary/15 dark:border-gray-800 dark:bg-gray-950"
						/>
					</label>
					<label
						class="grid gap-1.5 text-sm font-semibold text-primary dark:text-gray-100"
					>
						<span>Course</span>
						<Select
							bind:value={draftCourseId}
							placeholder="No course"
							options={(courses.data ?? []).map((c) => ({
								value: String(c.id),
								label: c.name,
							}))}
						/>
					</label>
					<label
						class="grid gap-1.5 text-sm font-semibold text-primary dark:text-gray-100"
					>
						<span>Visibility</span>
						<Select
							bind:value={draftVisibility}
							options={[
								{ value: "public", label: "Public" },
								{ value: "private", label: "Private" },
							]}
						/>
					</label>
					{#if me.data?.role === "admin"}
						<label
							class="grid gap-1.5 text-sm font-semibold text-primary dark:text-gray-100 md:col-span-3"
						>
							<span>Owner</span>
							<Select
								bind:value={draftOwnerId}
								placeholder="Unassigned"
								options={(options.data?.faculty ?? []).map(
									(f) => ({
										value: String(f.id),
										label: f.username,
									}),
								)}
							/>
						</label>
					{/if}
				</div>

				<div class="grid gap-3 md:grid-cols-2">
					<label
						class="grid gap-1.5 text-sm font-semibold text-primary dark:text-gray-100"
					>
						<span>Transcript</span>
						<textarea
							bind:value={draftText}
							rows="7"
							class="min-h-36 rounded-lg border border-gray-200 bg-white p-3 text-sm leading-6 outline-none focus:border-secondary/60 focus:ring-3 focus:ring-secondary/15 dark:border-gray-800 dark:bg-gray-950"
						></textarea>
					</label>
					<label
						class="grid gap-1.5 text-sm font-semibold text-primary dark:text-gray-100"
					>
						<span>Summary</span>
						<textarea
							bind:value={draftSummary}
							rows="7"
							class="min-h-36 rounded-lg border border-gray-200 bg-white p-3 text-sm leading-6 outline-none focus:border-secondary/60 focus:ring-3 focus:ring-secondary/15 dark:border-gray-800 dark:bg-gray-950"
						></textarea>
					</label>
				</div>

				{#if options.data?.students?.length}
					<div class="grid gap-2">
						<div
							class="flex items-center gap-2 text-sm font-semibold text-primary dark:text-gray-100"
						>
							<UsersThree size={16} />
							<span>Direct students</span>
						</div>
						<div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
							{#each options.data.students as student (student.id)}
								<label
									class="flex min-w-0 items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium dark:border-gray-800"
								>
									<input
										type="checkbox"
										checked={draftStudentIds.includes(
											student.id,
										)}
										onchange={() =>
											toggleStudent(student.id)}
										class="size-4 rounded border-gray-300 text-secondary focus:ring-secondary"
									/>
									<span class="truncate"
										>{student.username}</span
									>
								</label>
							{/each}
						</div>
					</div>
				{/if}

				{#if editError}
					<p
						class="rounded-lg bg-red-500/10 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400"
					>
						{editError}
					</p>
				{/if}

				<div class="flex justify-end">
					<Button
						variant="icon+text"
						onclick={saveLecture}
						disabled={saving}
						class="!bg-primary hover:!bg-primary/90"
					>
						{#snippet icon()}
							<FloppyDisk size={16} />
						{/snippet}
						{saving ? "Saving" : "Save"}
					</Button>
				</div>
				</Card>
			</Modal>
		{/if}

		<div class="flex min-h-0 flex-1 flex-col overflow-hidden">
			<ImageModal
				src={fileUrl("image")}
				alt={`Board capture — ${lec.course_name ?? "lecture"}`}
				class="h-full w-full rounded-xl bg-gray-50 object-contain ring-1 ring-gray-900/5 dark:bg-gray-800/50 dark:ring-white/10"
			/>
		</div>

		<div class="grid shrink-0 gap-4 md:grid-cols-2">
			<TextModal
				title="Transcript"
				text={lec.corrected_text}
				fallback="No text yet."
				lines={6}
			/>
			<TextModal
				title="Summary"
				text={lec.summary}
				fallback="No summary yet."
				lines={6}
			/>
		</div>
	</section>
{/if}
