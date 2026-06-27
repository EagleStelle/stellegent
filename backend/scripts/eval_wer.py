"""WER/CER scoring. Usage: python scripts/eval_wer.py <pred.txt> <ref.txt>"""
from __future__ import annotations
import sys
from pathlib import Path

from stellegent.evaluation import score_transcript


def main(argv):
    if len(argv) != 3:
        print("usage: eval_wer.py <pred.txt> <ref.txt>")
        return 2
    pred = Path(argv[1]).read_text(encoding="utf-8").strip()
    ref = Path(argv[2]).read_text(encoding="utf-8").strip()
    scores = score_transcript(hypothesis=pred, reference=ref)
    if scores is None:
        print("reference needed")
        return 1
    wer = scores["wer"]
    cer = scores["cer"]
    print(
        f"WER: {wer['error_rate']:.4f}  "
        f"({wer['recognition_rate'] * 100:.2f}% WRR)"
    )
    print(
        f"CER: {cer['error_rate']:.4f}  "
        f"({cer['recognition_rate'] * 100:.2f}% CRR)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
