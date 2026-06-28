<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import {
		createMutation,
		createQuery,
		useQueryClient,
	} from "@tanstack/svelte-query";
	import { apiDelete, apiGet, apiPatch, apiPost } from "$lib/api/client";
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
		ArrowRight,
		ArrowLeft,
		Sparkle,
		CircleNotch,
		CaretDown,
	} from "phosphor-svelte";
	import Card, { cardVariants } from "$lib/components/ui/Card.svelte";
	import ImageModal from "$lib/components/modal/Image.svelte";
	import Button from "$lib/components/ui/Button.svelte";
	import Textarea from "$lib/components/ui/Textarea.svelte";
	import { cn } from "$lib/utils";

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

	const generateSummary = createMutation(() => ({
		mutationFn: () =>
			apiPost<LectureDetail>(`/api/v1/lectures/${id}/summarize`),
		onSuccess: (data) => {
			qc.setQueryData(["lecture", id], data);
		},
	}));

	let evaluationOpen = $state(false);
	let savingEvaluation = $state(false);
	let evaluationError = $state("");
	let evaluationStatus = $state("");
	let evaluationSeedId = $state<string | null>(null);
	let draftReferenceTranscript = $state("");
	let draftReferenceSummary = $state("");

	$effect(() => {
		if (!lecture.data || evaluationSeedId === lecture.data.id) return;
		evaluationSeedId = lecture.data.id;
		draftReferenceTranscript = lecture.data.reference_transcript ?? "";
		draftReferenceSummary = lecture.data.reference_summary ?? "";
		evaluationError = "";
		evaluationStatus = "";
	});

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
		const base = (
			lecture.data?.title ??
			lecture.data?.course_name ??
			"lecture"
		)
			.replace(/[^\w-]+/g, "_")
			.replace(/^_+|_+$/g, "");
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

	function resetEvaluationDrafts() {
		draftReferenceTranscript = lecture.data?.reference_transcript ?? "";
		draftReferenceSummary = lecture.data?.reference_summary ?? "";
		evaluationError = "";
		evaluationStatus = "";
	}

	async function saveEvaluation() {
		savingEvaluation = true;
		evaluationError = "";
		evaluationStatus = "";
		try {
			const data = await apiPatch<LectureDetail>(`/api/v1/lectures/${id}`, {
				reference_transcript: draftReferenceTranscript.trim() || null,
				reference_summary: draftReferenceSummary.trim() || null,
			});
			qc.setQueryData(["lecture", id], data);
			evaluationSeedId = data.id;
			draftReferenceTranscript = data.reference_transcript ?? "";
			draftReferenceSummary = data.reference_summary ?? "";
			evaluationStatus = "Saved";
		} catch (err) {
			evaluationError = err instanceof Error ? err.message : "Save failed";
		} finally {
			savingEvaluation = false;
		}
	}

	async function clearEvaluationReferences() {
		draftReferenceTranscript = "";
		draftReferenceSummary = "";
		await saveEvaluation();
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

	function formatPercent(value: number | null | undefined) {
		if (value === null || value === undefined || Number.isNaN(value)) {
			return "N/A";
		}
		return `${(value * 100).toFixed(1)}%`;
	}

	function formatDuration(value: number | null | undefined) {
		if (value === null || value === undefined || Number.isNaN(value)) {
			return "Not recorded";
		}
		if (value >= 1000) {
			return `${(value / 1000).toFixed(value >= 10000 ? 1 : 2)}s`;
		}
		return `${value.toFixed(0)}ms`;
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
	{@const evaluation = lec.evaluation}
	{@const latency = lec.processing_timing}
	{@const hasEvaluation = Boolean(evaluation.raw_ocr || evaluation.summary)}
	<section
		class="flex flex-col gap-4 lg:h-[calc(100dvh-2rem)] lg:max-h-[calc(100dvh-2rem)] lg:overflow-y-auto lg:pr-1"
	>
		<header
			class="flex shrink-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"
		>
			<div class="flex items-start gap-3 sm:gap-4">
				<Button
					variant="icon"
					ghost
					onclick={() => goto("/lectures")}
					title="Back to lectures"
				>
					{#snippet icon()}
						<ArrowLeft size={20} />
					{/snippet}
				</Button>
				<div class="flex flex-col gap-2">
				<div class="flex items-center gap-3">
					<h1
						class="text-2xl font-bold tracking-tight text-balance text-primary dark:text-gray-50"
					>
						{lec.title ?? lec.course_name ?? "Lecture"}
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
					{#if lec.course_name}
						<div
							class="flex shrink-0 items-center gap-1.5 whitespace-nowrap"
						>
							<BookOpen size={16} />
							{lec.course_name}
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
				rawSrc={fileUrl("image_raw")}
				alt={`Board capture — ${lec.course_name ?? "lecture"}`}
			/>
		</div>

		<div class="grid shrink-0 gap-4 md:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(18rem,0.8fr)]">
			<div
				role="button"
				tabindex="0"
				class={cn(cardVariants({ interactive: true }), "group flex w-full flex-col gap-2 text-left outline-none")}
				onclick={() => goto(`/lectures/${id}/transcript`)}
				onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goto(`/lectures/${id}/transcript`); } }}
			>
				<div class="flex min-h-8 w-full items-center justify-between gap-2">
					<h2 class="text-sm font-semibold text-primary transition-colors group-hover:text-secondary dark:text-gray-50">
						OCR
					</h2>
					<ArrowRight size={16} class="shrink-0 text-gray-400 transition-colors duration-200 group-hover:text-secondary" />
				</div>
				<p class="whitespace-pre-wrap text-sm leading-6 text-gray-600 dark:text-gray-300" style="display:-webkit-box;-webkit-line-clamp:6;-webkit-box-orient:vertical;overflow:hidden;">
					{lec.raw_ocr_text?.trim() ? lec.raw_ocr_text : "No OCR text yet."}
				</p>
			</div>

			<div
				role="button"
				tabindex="0"
				class={cn(cardVariants({ interactive: true }), "group flex w-full flex-col gap-2 text-left outline-none")}
				onclick={() => goto(`/lectures/${id}/summary`)}
				onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goto(`/lectures/${id}/summary`); } }}
			>
				<div class="flex min-h-8 w-full items-center justify-between gap-2">
					<h2 class="text-sm font-semibold text-primary transition-colors group-hover:text-secondary dark:text-gray-50">
						Summary
					</h2>
					<div class="flex items-center gap-1">
						{#if canManage}
							<Button
								variant="icon"
								ghost
								onclick={(e: MouseEvent) => { e.stopPropagation(); generateSummary.mutate(); }}
								onkeydown={(e: KeyboardEvent) => { e.stopPropagation(); }}
								disabled={generateSummary.isPending}
								title="Generate summary"
							>
								{#snippet icon()}
									{#if generateSummary.isPending}
										<CircleNotch size={16} class="animate-spin" />
									{:else}
										<Sparkle size={16} />
									{/if}
								{/snippet}
							</Button>
						{/if}
						<ArrowRight size={16} class="shrink-0 text-gray-400 transition-colors duration-200 group-hover:text-secondary" />
					</div>
				</div>
				<p
					class="whitespace-pre-wrap text-sm leading-6 text-gray-600 dark:text-gray-300"
					style="display:-webkit-box;-webkit-line-clamp:6;-webkit-box-orient:vertical;overflow:hidden;"
				>
					{lec.summary?.trim() ? lec.summary : "No summary yet."}
				</p>
			</div>

			<div
				class={cn(cardVariants(), "flex w-full flex-col gap-3 md:col-span-2 xl:col-span-1")}
			>
				<div class="flex min-h-8 w-full items-center justify-between gap-2">
					<h2 class="text-sm font-semibold text-primary dark:text-gray-50">
						Latency
					</h2>
				</div>

				{#if latency}
					<div class="grid gap-2 text-sm">
						{#each latency.stages as stage (stage.key)}
							<div class="flex items-center justify-between gap-3">
								<span class="min-w-0 truncate text-gray-600 dark:text-gray-300">
									{stage.label}
								</span>
								<span class="shrink-0 font-semibold tabular-nums text-primary dark:text-gray-50">
									{stage.triggered ? formatDuration(stage.duration_ms) : "Skipped"}
								</span>
							</div>
						{/each}
					</div>
					<div class="grid gap-2 border-t border-gray-100 pt-3 text-sm dark:border-gray-800">
						<div class="flex items-center justify-between gap-3">
							<span class="font-medium text-gray-600 dark:text-gray-300">Total</span>
							<span class="font-semibold tabular-nums text-primary dark:text-gray-50">
								{formatDuration(latency.total_ms)}
							</span>
						</div>
						<div class="flex items-center justify-between gap-3">
							<span class="font-medium text-gray-600 dark:text-gray-300">Mean / median</span>
							<span class="font-semibold tabular-nums text-primary dark:text-gray-50">
								{formatDuration(latency.mean_ms)} / {formatDuration(latency.median_ms)}
							</span>
						</div>
					</div>
				{:else}
					<p class="text-sm leading-6 text-gray-600 dark:text-gray-300">
						Latency was not recorded for this lecture.
					</p>
				{/if}
			</div>
		</div>

		<section class={cn(cardVariants(), "grid shrink-0 gap-4")}>
			<div class="flex min-h-8 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
				<div class="flex min-w-0 items-center gap-3">
					<h2 class="text-sm font-semibold text-primary dark:text-gray-50">
						Evaluation
					</h2>
					{#if hasEvaluation}
						<span class="rounded-lg bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
							Scores ready
						</span>
					{:else}
						<span class="rounded-lg bg-amber-500/10 px-2 py-1 text-xs font-semibold text-amber-700 dark:text-amber-300">
							Reference needed
						</span>
					{/if}
				</div>
				<Button
					variant="icon+text"
					secondary
					onclick={() => (evaluationOpen = !evaluationOpen)}
					title={evaluationOpen ? "Collapse evaluation" : "Expand evaluation"}
				>
					{#snippet icon()}
						<CaretDown
							size={16}
							class={cn("transition-transform duration-200", evaluationOpen && "rotate-180")}
						/>
					{/snippet}
					{evaluationOpen ? "Collapse" : "Expand"}
				</Button>
			</div>

			{#if evaluationOpen}
				<div class="grid gap-4 border-t border-gray-100 pt-4 dark:border-gray-800">
					{#if canManage}
						<div class="grid gap-4 md:grid-cols-2">
							<Textarea
								id="evaluation-reference-transcript"
								label="Real transcript"
								bind:value={draftReferenceTranscript}
								rows={8}
								placeholder="Paste the human-verified lecture transcript"
							/>
							<Textarea
								id="evaluation-reference-summary"
								label="Reference summary"
								bind:value={draftReferenceSummary}
								rows={8}
								placeholder="Paste the human/reference summary for ROUGE"
							/>
						</div>
						<div class="flex flex-wrap items-center justify-between gap-3">
							<div class="min-h-5 text-sm font-medium">
								{#if evaluationError}
									<span class="text-red-600 dark:text-red-400">{evaluationError}</span>
								{:else if evaluationStatus}
									<span class="text-emerald-700 dark:text-emerald-300">{evaluationStatus}</span>
								{/if}
							</div>
							<div class="flex flex-wrap items-center gap-2">
								<Button
									ghost
									type="button"
									onclick={resetEvaluationDrafts}
									disabled={savingEvaluation}
								>
									Reset
								</Button>
								<Button
									ghost
									danger
									type="button"
									onclick={clearEvaluationReferences}
									disabled={savingEvaluation}
								>
									Clear
								</Button>
								<Button
									type="button"
									onclick={saveEvaluation}
									disabled={savingEvaluation}
								>
									{savingEvaluation ? "Saving..." : "Save evaluation"}
								</Button>
							</div>
						</div>
					{:else}
						<p class="text-sm leading-6 text-gray-600 dark:text-gray-300">
							Only lecture owners can edit reference text. Scores still show here when references exist.
						</p>
					{/if}

					{#if hasEvaluation}
						<div class="grid gap-4 lg:grid-cols-2">
							{#if evaluation.raw_ocr}
								<div class="grid gap-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-950">
									<p class="text-xs font-semibold uppercase text-primary/60 dark:text-gray-400">
										OCR
									</p>
									<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
										<div>
											<span class="block text-xs text-gray-500 dark:text-gray-400">CER</span>
											<span class="font-semibold tabular-nums text-primary dark:text-gray-50">{formatPercent(evaluation.raw_ocr.cer.error_rate)}</span>
										</div>
										<div>
											<span class="block text-xs text-gray-500 dark:text-gray-400">CRR</span>
											<span class="font-semibold tabular-nums text-primary dark:text-gray-50">{formatPercent(evaluation.raw_ocr.cer.recognition_rate)}</span>
										</div>
										<div>
											<span class="block text-xs text-gray-500 dark:text-gray-400">WER</span>
											<span class="font-semibold tabular-nums text-primary dark:text-gray-50">{formatPercent(evaluation.raw_ocr.wer.error_rate)}</span>
										</div>
										<div>
											<span class="block text-xs text-gray-500 dark:text-gray-400">WRR</span>
											<span class="font-semibold tabular-nums text-primary dark:text-gray-50">{formatPercent(evaluation.raw_ocr.wer.recognition_rate)}</span>
										</div>
									</div>
								</div>
							{/if}

							{#if evaluation.summary}
								<div class="grid gap-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-950">
									<p class="text-xs font-semibold uppercase text-primary/60 dark:text-gray-400">
										Summary
									</p>
									<div class="grid grid-cols-3 gap-3">
										<div>
											<span class="block text-xs text-gray-500 dark:text-gray-400">ROUGE-1</span>
											<span class="font-semibold tabular-nums text-primary dark:text-gray-50">{formatPercent(evaluation.summary.rouge1.fmeasure)}</span>
										</div>
										<div>
											<span class="block text-xs text-gray-500 dark:text-gray-400">ROUGE-2</span>
											<span class="font-semibold tabular-nums text-primary dark:text-gray-50">{formatPercent(evaluation.summary.rouge2.fmeasure)}</span>
										</div>
										<div>
											<span class="block text-xs text-gray-500 dark:text-gray-400">ROUGE-L</span>
											<span class="font-semibold tabular-nums text-primary dark:text-gray-50">{formatPercent(evaluation.summary.rougeL.fmeasure)}</span>
										</div>
									</div>
								</div>
							{/if}
						</div>
					{:else}
						<p class="text-sm leading-6 text-gray-600 dark:text-gray-300">
							Add a real transcript for OCR scores or a reference summary for ROUGE scores.
						</p>
					{/if}
				</div>
			{/if}
		</section>
	</section>
{/if}
