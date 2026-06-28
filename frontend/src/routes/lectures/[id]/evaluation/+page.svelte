<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import { createQuery, useQueryClient } from "@tanstack/svelte-query";
	import { apiGet, apiPatch } from "$lib/api/client";
	import type { LectureDetail, LectureSummary, User } from "$lib/types";
	import { ArrowLeft } from "phosphor-svelte";
	import Button from "$lib/components/ui/Button.svelte";
	import Textarea from "$lib/components/ui/Textarea.svelte";

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

	let saving = $state(false);
	let error = $state("");
	let exporting = $state(false);
	let exportError = $state("");
	let seededId = $state<string | null>(null);
	let draftReferenceTranscript = $state("");
	let draftReferenceSummary = $state("");

	$effect(() => {
		if (!lecture.data || seededId === lecture.data.id) return;
		seededId = lecture.data.id;
		draftReferenceTranscript = lecture.data.reference_transcript ?? "";
		draftReferenceSummary = lecture.data.reference_summary ?? "";
		error = "";
	});

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

	function resetDrafts() {
		draftReferenceTranscript = lecture.data?.reference_transcript ?? "";
		draftReferenceSummary = lecture.data?.reference_summary ?? "";
		error = "";
	}

	async function saveEvaluation() {
		saving = true;
		error = "";
		try {
			const data = await apiPatch<LectureDetail>(`/api/v1/lectures/${id}`, {
				reference_transcript: draftReferenceTranscript.trim() || null,
				reference_summary: draftReferenceSummary.trim() || null,
			});
			qc.setQueryData(["lecture", id], data);
			seededId = data.id;
			draftReferenceTranscript = data.reference_transcript ?? "";
			draftReferenceSummary = data.reference_summary ?? "";
		} catch (err) {
			error = err instanceof Error ? err.message : "Save failed";
		} finally {
			saving = false;
		}
	}

	async function clearReferences() {
		draftReferenceTranscript = "";
		draftReferenceSummary = "";
		await saveEvaluation();
	}

	type Cell = string | number | null | undefined;

	function csvCell(value: Cell) {
		if (value === null || value === undefined) return "";
		const text = String(value);
		return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
	}

	function toCsv(headers: string[], rows: Cell[][]) {
		return [headers, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n");
	}

	function downloadCsv(name: string, content: string) {
		const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = name;
		document.body.appendChild(a);
		a.click();
		a.remove();
		URL.revokeObjectURL(url);
	}

	const metaHeaders = ["Lecture ID", "Title", "Course", "Date"];
	function metaCells(lec: LectureDetail): Cell[] {
		return [lec.id, lec.title, lec.course_name, lec.date];
	}

	async function exportAll() {
		exporting = true;
		exportError = "";
		try {
			const list = await apiGet<LectureSummary[]>("/api/v1/lectures");
			const details = await Promise.all(
				list.map((l) => apiGet<LectureDetail>(`/api/v1/lectures/${l.id}`)),
			);

			const ocrHeaders = [...metaHeaders, "CER", "CRR", "WER", "WRR"];
			const ocrRows: Cell[][] = details.map((lec) => {
				const o = lec.evaluation?.raw_ocr;
				return [
					...metaCells(lec),
					o?.cer.error_rate, o?.cer.recognition_rate,
					o?.wer.error_rate, o?.wer.recognition_rate,
				];
			});

			const summaryHeaders = [
				...metaHeaders,
				"ROUGE-1 Precision", "ROUGE-1 Recall", "ROUGE-1 F-measure",
				"ROUGE-2 Precision", "ROUGE-2 Recall", "ROUGE-2 F-measure",
				"ROUGE-L Precision", "ROUGE-L Recall", "ROUGE-L F-measure",
			];
			const summaryRows: Cell[][] = details.map((lec) => {
				const s = lec.evaluation?.summary;
				return [
					...metaCells(lec),
					s?.rouge1.precision, s?.rouge1.recall, s?.rouge1.fmeasure,
					s?.rouge2.precision, s?.rouge2.recall, s?.rouge2.fmeasure,
					s?.rougeL.precision, s?.rougeL.recall, s?.rougeL.fmeasure,
				];
			});

			// Fixed pipeline stages (see backend pipeline.py), so every
			// export has the same columns in the same order.
			const STAGES = [
				{ key: "preprocessing", label: "Preprocessing (OpenCV)" },
				{ key: "ocr", label: "OCR (PP-OCRv5)" },
				{ key: "correction", label: "Correction (Phi-3-mini, when triggered)" },
				{ key: "summarization", label: "Summarization (Phi-3-mini)" },
				{ key: "export_db", label: "Export + database write" },
			];
			const latencyHeaders = [
				...metaHeaders,
				...STAGES.map((s) => `${s.label} (ms)`),
				"Total (ms)", "Mean (ms)", "Median (ms)",
			];
			const latencyRows: Cell[][] = details.map((lec) => {
				const t = lec.processing_timing;
				const byKey = new Map(t?.stages.map((s) => [s.key, s]));
				return [
					...metaCells(lec),
					...STAGES.map(({ key }) => {
						const stage = byKey.get(key);
						if (!stage) return "";
						return stage.triggered ? stage.duration_ms : "Skipped";
					}),
					t?.total_ms, t?.mean_ms, t?.median_ms,
				];
			});

			const stamp = new Date().toISOString().slice(0, 10);
			downloadCsv(`evaluation-ocr-${stamp}.csv`, toCsv(ocrHeaders, ocrRows));
			downloadCsv(`evaluation-summary-${stamp}.csv`, toCsv(summaryHeaders, summaryRows));
			downloadCsv(`evaluation-latency-${stamp}.csv`, toCsv(latencyHeaders, latencyRows));
		} catch (err) {
			exportError = err instanceof Error ? err.message : "Export failed";
		} finally {
			exporting = false;
		}
	}
</script>

{#if lecture.data}
	{@const lec = lecture.data}
	{@const evaluation = lec.evaluation}
	{@const latency = lec.processing_timing}
	<div
		class="relative flex h-[calc(100dvh-7rem)] max-h-[calc(100dvh-7rem)] flex-col gap-4 md:h-[calc(100dvh-2rem)] md:max-h-[calc(100dvh-2rem)]"
	>
		<header class="shrink-0">
			<div
				class="flex items-center gap-4 border-b border-gray-200 pb-2 dark:border-gray-800"
			>
				<Button
					variant="icon"
					ghost
					onclick={() => goto(`/lectures/${id}`)}
					title="Back to lecture"
				>
					{#snippet icon()}
						<ArrowLeft size={20} />
					{/snippet}
				</Button>
				<div class="min-w-0 flex-1">
					<h1
						class="text-2xl font-bold tracking-tight text-primary dark:text-gray-50"
					>
						Evaluation
					</h1>
				</div>
				{#if me.data?.role === "admin"}
					<Button
						variant="text"
						type="button"
						onclick={exportAll}
						disabled={exporting}
						title="Export all lecture evaluations as CSV"
					>
						{exporting ? "Exporting…" : "Export"}
					</Button>
				{/if}
			</div>
			{#if exportError}
				<span class="block truncate pt-1 text-xs font-medium text-red-600 dark:text-red-400">
					{exportError}
				</span>
			{/if}
		</header>

		<div class="grid min-h-0 flex-1 gap-8 overflow-y-auto pr-2 lg:grid-cols-2 lg:gap-10">
			<div class="flex flex-col gap-4">
				{#if canManage}
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
				{:else}
					<p class="text-sm leading-6 text-gray-600 dark:text-gray-300">
						Only lecture owners can edit reference text. Scores still show here when references exist.
					</p>
				{/if}
			</div>

			<div class="flex flex-col gap-6">
				<section class="grid gap-3">
					<div class="flex items-center justify-between gap-3 border-b border-gray-200 pb-2 dark:border-gray-800">
						<h2 class="text-sm font-semibold text-primary dark:text-gray-50">
							OCR
						</h2>
						{#if !evaluation.raw_ocr}
							<span class="rounded-lg bg-amber-500/10 px-2 py-1 text-xs font-semibold text-amber-700 dark:text-amber-300">
								Real transcript needed
							</span>
						{/if}
					</div>
					{#if evaluation.raw_ocr}
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
					{:else}
						<p class="text-sm leading-6 text-gray-600 dark:text-gray-300">
							Save a real transcript to calculate CER, CRR, WER, and WRR.
						</p>
					{/if}
				</section>

				<section class="grid gap-3">
					<div class="flex items-center justify-between gap-3 border-b border-gray-200 pb-2 dark:border-gray-800">
						<h2 class="text-sm font-semibold text-primary dark:text-gray-50">
							Summary
						</h2>
						{#if !evaluation.summary}
							<span class="rounded-lg bg-amber-500/10 px-2 py-1 text-xs font-semibold text-amber-700 dark:text-amber-300">
								Reference summary needed
							</span>
						{/if}
					</div>
					{#if evaluation.summary}
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
					{:else}
						<p class="text-sm leading-6 text-gray-600 dark:text-gray-300">
							Save a reference summary to calculate ROUGE-1, ROUGE-2, and ROUGE-L.
						</p>
					{/if}
				</section>

				<section class="grid gap-3">
					<h2 class="border-b border-gray-200 pb-2 text-sm font-semibold text-primary dark:border-gray-800 dark:text-gray-50">
						Latency
					</h2>
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
				</section>
			</div>
		</div>

		<footer class="shrink-0">
			<div
				class="flex items-center justify-between gap-4 border-t border-gray-200 pt-2 dark:border-gray-800"
			>
				<div class="min-w-0 flex-1 pl-2">
					<span class="block truncate text-sm font-medium text-gray-500 dark:text-gray-400">
						{lec.title ?? lec.course_name ?? "Lecture"}
					</span>
					{#if error}
						<span class="block truncate text-xs font-medium text-red-600 dark:text-red-400">
							{error}
						</span>
					{/if}
				</div>
				{#if canManage}
					<div class="flex shrink-0 items-center gap-3">
						<Button ghost type="button" onclick={resetDrafts} disabled={saving}>
							Reset
						</Button>
						<Button ghost danger type="button" onclick={clearReferences} disabled={saving}>
							Clear
						</Button>
						<Button type="button" onclick={saveEvaluation} disabled={saving}>
							{saving ? "Saving..." : "Save"}
						</Button>
					</div>
				{/if}
			</div>
		</footer>
	</div>
{/if}
