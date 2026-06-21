<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiDelete, apiGet } from "$lib/api/client";
	import type { LectureDetail, User } from "$lib/types";
	import {
		Trash,
		PencilSimple,
		CalendarBlank,
		UserCircle,
		GlobeHemisphereWest,
		LockSimple,
		FilePdf,
		FileDoc,
		FileTxt,
		BookOpen,
	} from "phosphor-svelte";
	import Card from "$lib/components/ui/Card.svelte";
	import ImageModal from "$lib/components/modal/Image.svelte";
	import TextModal from "$lib/components/modal/Text.svelte";
	import Button from "$lib/components/ui/Button.svelte";

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
	const downloads = [
		{ type: "pdf", label: "PDF", Icon: FilePdf },
		{ type: "docx", label: "DOCX", Icon: FileDoc },
		{ type: "txt", label: "TXT", Icon: FileTxt },
	];

	const fileUrl = (type: string) =>
		`/api/v1/lectures/${id}/file?type=${type}`;

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
		await apiDelete(`/api/v1/lectures/${id}`);
		await qc.invalidateQueries({ queryKey: ["lectures"] });
		goto("/lectures");
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
	<Card>
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
			class="flex shrink-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"
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
								? lec.owner_username
								: "Unknown"}</span
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
						secondary
						onclick={() => downloadFile(d.type)}
						title={`Download ${d.label}`}
					>
						{#snippet icon()}
							<d.Icon size={16} />
						{/snippet}
						{d.label}
					</Button>
				{/each}
				{#if canManage}
					<div
						class="mx-1 h-6 w-px rounded-full bg-gray-200 dark:bg-gray-800"
					></div>
					<Button
						variant="icon+text"
						onclick={() => goto(`/lectures/${id}/edit`)}
						title="Edit lecture"
					>
						{#snippet icon()}
							<PencilSimple size={16} />
						{/snippet}
						Edit
					</Button>
					<Button
						variant="icon+text"
						danger
						onclick={remove}
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



		<div class="flex min-h-0 flex-1 flex-col overflow-hidden">
			<ImageModal
				src={fileUrl("image")}
				alt={`Board capture — ${lec.course_name ?? "lecture"}`}
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
