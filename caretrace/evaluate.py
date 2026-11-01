"""Evaluate on a frozen split; never ignore malformed or missing predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from importlib.metadata import version
from pathlib import Path

from .contracts import SYSTEM, parse_enumerated
from .data import get_dataset, rows_for
from .engine import MODEL_ID, MODEL_REVISION, create_engine
from .metrics import aggregate, score_encounter


def artifact_hash(path: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(file for file in path.rglob("*") if file.is_file())
    if not files:
        raise ValueError("Model artifact contains no files")
    for file in files:
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        with file.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split", choices=("validation", "test1", "test2"), required=True)
    parser.add_argument("--final-test", action="store_true")
    parser.add_argument("--engine", default="rules")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.split.startswith("test") and (not args.final_test or args.limit is not None):
        parser.error("Test scoring requires --final-test and prohibits --limit")
    if args.final_test and args.split == "validation":
        parser.error("--final-test requires a test split")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.out.exists():
        parser.error("Output path exists")
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    rows = rows_for(get_dataset(), manifest, args.split)
    if args.limit:
        rows = rows[:args.limit]
    engine = create_engine(args.engine)
    args.out.mkdir(parents=True)
    records, failed, started = [], 0, time.perf_counter()
    spans_checked, spans_exact = 0, 0
    with (args.out / "predictions.jsonl").open("w", encoding="utf-8") as output:
        for index, row in enumerate(rows, 1):
            valid_turns = set()
            try:
                turns = parse_enumerated(row["enumerated_transcript"])
                valid_turns = {turn.id for turn in turns}
                predicted = engine.extract(turns)
                error = None
            except (ValueError, json.JSONDecodeError) as exc:
                predicted, error = [], str(exc)
                failed += 1
            metrics = score_encounter(row["orders"], predicted, valid_turns=valid_turns)
            source_text = {turn.id: turn.text for turn in turns} if valid_turns else {}
            for item in predicted:
                if item.get("origin") == "verbatim_source":
                    spans_checked += 1
                    span = item["source_span"]
                    spans_exact += source_text.get(span["turn_id"], "")[span["start"]:span["end"]] == item["description"]
            records.append(metrics)
            output.write(json.dumps({"id": row["id"], "prediction": predicted, "error": error,
                                     "counts": metrics}, ensure_ascii=False) + "\n")
            output.flush()
            if index % 5 == 0 or index == len(rows):
                print(f"Processed {index}/{len(rows)} encounters; failures={failed}", flush=True)
    metrics = aggregate(records)
    repo = Path(__file__).resolve().parents[1]
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo, capture_output=True, text=True)
    metrics.update({"split": args.split, "limited": args.limit is not None,
                    "source_spans_checked": spans_checked, "source_spans_exact": spans_exact,
                    "engine": engine.name, "parse_or_input_failures": failed,
                    "ollama_model_digest": getattr(engine, "digest", None),
                    "model_revision": MODEL_REVISION if args.engine == MODEL_ID else None,
                    "model_artifact_sha256": artifact_hash(Path(args.engine)) if Path(args.engine).is_dir() else None,
                    "system_prompt_sha256": hashlib.sha256(SYSTEM.encode()).hexdigest(),
                    "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                    "elapsed_seconds": round(time.perf_counter() - started, 2),
                    "versions": {name: version(name) for name in ("datasets", "transformers", "torch")},
                    "code_commit": commit.stdout.strip() if commit.returncode == 0 else None,
                    "code_dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
                    "metric_note": "Type plus token-F1 >= 0.67 and matching digit strings; greedy one-to-one matching. Evidence ID overlap is unvalidated, not clinical accuracy."})
    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
