"""ROUGE scoring for summaries. Usage: eval_rouge.py <pred.txt> <ref.txt>"""
from __future__ import annotations
import sys
from pathlib import Path

from stellegent.evaluation import score_summary


def main(argv):
    if len(argv) != 3:
        print("usage: eval_rouge.py <pred.txt> <ref.txt>")
        return 2
    pred = Path(argv[1]).read_text(encoding="utf-8")
    ref = Path(argv[2]).read_text(encoding="utf-8")
    scores = score_summary(hypothesis=pred, reference=ref)
    if scores is None:
        print("reference needed")
        return 1
    for key in ("rouge1", "rouge2", "rougeL"):
        value = scores[key]
        print(
            f"{key}: P={value['precision']:.3f} "
            f"R={value['recall']:.3f} F={value['fmeasure']:.3f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
