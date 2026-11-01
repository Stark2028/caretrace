"""Paired encounter bootstrap for the transparent order-matching proxy."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from .metrics import aggregate


def compare(baseline: list[dict], candidate: list[dict], samples: int = 1000, seed: int = 42) -> dict:
    if samples < 1 or not baseline or len(baseline) != len(candidate):
        raise ValueError("Use the same nonempty encounters and a positive sample count.")
    if [r["id"] for r in baseline] != [r["id"] for r in candidate]:
        raise ValueError("Encounter IDs and order must match.")
    if any(a["counts"]["gold"] != b["counts"]["gold"] for a, b in zip(baseline, candidate)):
        raise ValueError("Reference order counts differ.")
    base_counts = [r["counts"] for r in baseline]
    candidate_counts = [r["counts"] for r in candidate]
    base = aggregate(base_counts)
    other = aggregate(candidate_counts)
    rng = random.Random(seed)
    differences = []
    for _ in range(samples):
        chosen = [rng.randrange(len(baseline)) for _ in baseline]
        left = aggregate([base_counts[i] for i in chosen])["f1_proxy"]
        right = aggregate([candidate_counts[i] for i in chosen])["f1_proxy"]
        differences.append(right - left)
    differences.sort()
    def percentile(fraction):
        position = (len(differences) - 1) * fraction
        lower = int(position)
        upper = min(lower + 1, len(differences) - 1)
        return differences[lower] + (differences[upper] - differences[lower]) * (position - lower)
    return {"encounters": len(baseline), "baseline": base, "candidate": other,
            "candidate_minus_baseline_f1_proxy": other["f1_proxy"] - base["f1_proxy"],
            "bootstrap_95pct_interval": [percentile(.025), percentile(.975)],
            "bootstrap_samples": samples, "seed": seed,
            "interpretation": "Encounter bootstrap of lexical proxy, not clinical accuracy; related encounters may not be independent."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Output already exists")
    def read(path):
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = compare(read(args.baseline), read(args.candidate), args.samples, args.seed)
    result["baseline_sha256"] = hashlib.sha256(args.baseline.read_bytes()).hexdigest()
    result["candidate_sha256"] = hashlib.sha256(args.candidate.read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
