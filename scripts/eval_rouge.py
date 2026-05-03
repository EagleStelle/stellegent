"""ROUGE scoring for summaries. Usage: eval_rouge.py <pred.txt> <ref.txt>"""
from __future__ import annotations
import sys
from pathlib import Path
from rouge_score import rouge_scorer  # type: ignore


def main(argv):
    if len(argv) != 3:
        print("usage: eval_rouge.py <pred.txt> <ref.txt>")
        return 2
    pred = Path(argv[1]).read_text(encoding="utf-8")
    ref = Path(argv[2]).read_text(encoding="utf-8")
    sc = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    s = sc.score(ref, pred)
    for k, v in s.items():
        print(f"{k}: P={v.precision:.3f} R={v.recall:.3f} F={v.fmeasure:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
