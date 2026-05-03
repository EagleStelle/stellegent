"""End-to-end latency benchmark. Usage: bench_latency.py <image.jpg> [N]"""
from __future__ import annotations
import sys
import time
import statistics

import cv2
from stellegent.pipeline import process_image


def main(argv):
    if len(argv) < 2:
        print("usage: bench_latency.py <image.jpg> [N]")
        return 2
    n = int(argv[2]) if len(argv) > 2 else 3
    img = cv2.imread(argv[1])
    times = []
    for i in range(n):
        t = time.perf_counter()
        process_image(img)
        dt = time.perf_counter() - t
        times.append(dt)
        print(f"run {i+1}: {dt:.2f}s")
    print(f"mean={statistics.mean(times):.2f}s  median={statistics.median(times):.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
