"""Audit train/validation evidence and cross-partition text overlap without test labels."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from .contracts import parse_enumerated
from .data import get_dataset, rows_for


def normalized_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.lower().split()).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Output already exists")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    dataset = get_dataset()
    stats = {}
    hashes = {}
    for part in ("train", "validation"):
        rows = rows_for(dataset, manifest, part)
        errors, orders, missing_evidence, invalid_evidence, invalid_encounters = 0, 0, 0, 0, 0
        types = Counter()
        hashes[part] = set()
        for row in rows:
            hashes[part].add(normalized_hash(row["enumerated_transcript"]))
            try:
                turns = parse_enumerated(row["enumerated_transcript"])
            except ValueError:
                errors += 1
                continue
            ids = {turn.id for turn in turns}
            encounter_invalid = False
            for order in row["orders"]:
                orders += 1
                types[order["order_type"]] += 1
                evidence = order.get("provenance") or []
                missing_evidence += not evidence
                invalid_evidence += bool(set(evidence) - ids)
                encounter_invalid |= not evidence or bool(set(evidence) - ids)
            invalid_encounters += encounter_invalid
        stats[part] = {"encounters": len(rows), "parse_failures": errors,
                       "orders": orders, "order_types": dict(types),
                       "orders_without_evidence": missing_evidence,
                       "orders_with_unknown_turns": invalid_evidence,
                       "encounters_with_invalid_evidence": invalid_encounters}
    for part in ("test1", "test2"):
        # Input text is hashed solely for overlap checks. Test annotations remain unused.
        hashes[part] = {normalized_hash(text) for text in dataset[part]["enumerated_transcript"]}
    pairs = {}
    parts = list(hashes)
    for i, left in enumerate(parts):
        for right in parts[i + 1:]:
            pairs[f"{left}__{right}"] = len(hashes[left] & hashes[right])
    report = {"train_validation": stats, "exact_normalized_input_hash_overlaps": pairs,
              "test_annotation_access": False}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
