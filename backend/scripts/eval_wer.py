"""WER/CER scoring. Usage: python scripts/eval_wer.py <pred.txt> <ref.txt>"""
from __future__ import annotations
import sys
from pathlib import Path

import jiwer  # type: ignore


def main(argv):
    if len(argv) != 3:
        print("usage: eval_wer.py <pred.txt> <ref.txt>")
        return 2
    pred = Path(argv[1]).read_text(encoding="utf-8").strip()
    ref = Path(argv[2]).read_text(encoding="utf-8").strip()
    transform = jiwer.Compose([
        jiwer.ToLowerCase(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.Strip(),
    ])
    wer = jiwer.wer(ref, pred, truth_transform=transform, hypothesis_transform=transform)
    cer = jiwer.cer(ref, pred, truth_transform=transform, hypothesis_transform=transform)
    print(f"WER: {wer:.4f}  ({(1-wer)*100:.2f}% WRR)")
    print(f"CER: {cer:.4f}  ({(1-cer)*100:.2f}% CRR)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
