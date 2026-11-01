"""Pin and audit simulated encounter partitions before experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DATASET = "mkieffer/SIMORD"
REVISION = "a5e570d7512cd36e64b6e4b03d2800ee6fcec86b"


def get_dataset():
    from datasets import load_dataset
    return load_dataset(DATASET, revision=REVISION)


def partition(identifier: str) -> str:
    return "validation" if int(hashlib.sha256(identifier.encode()).hexdigest()[:8], 16) % 5 == 0 else "train"


def build_manifest(dataset) -> dict:
    ids = {name: [row["id"] for row in split] for name, split in dataset.items()}
    names = list(ids)
    for name in names:
        if len(ids[name]) != len(set(ids[name])):
            raise ValueError(f"Duplicate encounter ID in {name}")
    for i, name in enumerate(names):
        for other in names[i + 1:]:
            if set(ids[name]) & set(ids[other]):
                raise ValueError(f"Encounter IDs overlap: {name} and {other}")
    result = {"dataset": DATASET, "revision": REVISION,
              "split_method": "sha256(id) first 8 hex digits modulo 5; zero is validation",
              "source_fingerprints": {name: split._fingerprint for name, split in dataset.items()},
              "partitions": {"train": [x for x in ids["train"] if partition(x) == "train"],
                             "validation": [x for x in ids["train"] if partition(x) == "validation"],
                             "test1": ids["test1"], "test2": ids["test2"]}}
    if any(not values for values in result["partitions"].values()):
        raise ValueError("Empty partition")
    return result


def rows_for(dataset, manifest: dict, part: str) -> list[dict]:
    actual = {name: split._fingerprint for name, split in dataset.items()}
    if actual != manifest["source_fingerprints"]:
        raise ValueError("Dataset fingerprints differ from the manifest.")
    source = "train" if part in {"train", "validation"} else part
    wanted = set(manifest["partitions"][part])
    rows = [row for row in dataset[source] if row["id"] in wanted]
    if len(rows) != len(wanted):
        raise ValueError("Manifest does not match source rows")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Manifest already exists; use a new path")
    manifest = build_manifest(get_dataset())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({name: len(ids) for name, ids in manifest["partitions"].items()}))


if __name__ == "__main__":
    main()
