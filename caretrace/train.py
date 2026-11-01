"""Fine-tune the final Transformer block on the training partition only.

This is partial fine-tuning, not LoRA. Validation/test examples are never read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import time
from pathlib import Path

from .contracts import parse_enumerated, prompt_messages
from .data import get_dataset, rows_for
from .engine import MODEL_ID, MODEL_REVISION


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--gradient-accumulation", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, help="Training smoke check; never a benchmark")
    args = parser.parse_args()
    if args.out.exists() or args.epochs < 1 or args.gradient_accumulation < 1 or args.learning_rate <= 0:
        parser.error("Use a new output path and positive training settings")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise RuntimeError("Training requires a CUDA-enabled PyTorch installation")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    manifest_bytes = args.manifest.read_bytes()
    rows = rows_for(get_dataset(), json.loads(manifest_bytes), "train")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, revision=MODEL_REVISION,
                                                torch_dtype=torch.float16).cuda()
    for parameter in model.parameters():
        parameter.requires_grad = False
    for parameter in model.model.layers[-1].parameters():
        parameter.requires_grad = True
    for parameter in model.model.norm.parameters():
        parameter.requires_grad = True
    # Keep trainable weights in FP32 for stable gradients with AMP.
    for parameter in model.parameters():
        if parameter.requires_grad:
            parameter.data = parameter.data.float()
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    examples, skipped, invalid_evidence = [], [], []
    for row in rows:
        turns = parse_enumerated(row["enumerated_transcript"])
        ids = {turn.id for turn in turns}
        if any(not order.get("provenance") or not set(order["provenance"]) <= ids
               for order in row["orders"]):
            invalid_evidence.append(row["id"])
            continue
        prompt = tokenizer.apply_chat_template(prompt_messages(turns), tokenize=False, add_generation_prompt=True)
        prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        orders = [{"order_type": order["order_type"].lower().replace("-", ""),
                   "description": order["description"], "reason": order.get("reason"),
                   "provenance": order.get("provenance") or []} for order in row["orders"]]
        answer = json.dumps({"orders": orders}, ensure_ascii=False) + tokenizer.eos_token
        target_ids = tokenizer(answer, add_special_tokens=False)["input_ids"]
        if len(prompt_ids) + len(target_ids) > args.max_tokens:
            skipped.append(row["id"])
            continue
        examples.append((row["id"], prompt_ids, target_ids))
    if args.limit:
        examples = examples[:args.limit]
    if not examples:
        raise ValueError("No training examples fit the requested context length")
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.learning_rate)
    scaler = torch.amp.GradScaler("cuda")
    started = time.perf_counter()
    model.train()
    optimizer.zero_grad(set_to_none=True)
    steps = 0
    for epoch in range(args.epochs):
        random.shuffle(examples)
        for index, (_, prompt_ids, target_ids) in enumerate(examples):
            ids = torch.tensor([prompt_ids + target_ids], dtype=torch.long, device="cuda")
            target = torch.tensor(target_ids, dtype=torch.long, device="cuda")
            with torch.autocast("cuda", dtype=torch.float16):
                hidden = model.model(input_ids=ids, use_cache=False).last_hidden_state
                logits = model.lm_head(hidden[:, len(prompt_ids) - 1:-1, :])
                loss = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.shape[-1]).float(), target)
            # A final partial accumulation window must average its actual examples.
            window_start = (index // args.gradient_accumulation) * args.gradient_accumulation
            window_size = min(args.gradient_accumulation, len(examples) - window_start)
            scaler.scale(loss / window_size).backward()
            if (index + 1) % args.gradient_accumulation == 0 or index + 1 == len(examples):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                steps += 1
            if (index + 1) % 10 == 0 or index + 1 == len(examples):
                print(f"epoch={epoch + 1} example={index + 1}/{len(examples)} loss={loss.item():.4f}", flush=True)
    args.out.mkdir(parents=True)
    model.save_pretrained(args.out / "model", safe_serialization=True)
    tokenizer.save_pretrained(args.out / "model")
    repo = Path(__file__).resolve().parents[1]
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo, capture_output=True, text=True)
    report = {"base_model": MODEL_ID, "base_revision": MODEL_REVISION,
              "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "train_examples_used": len(examples), "train_examples_skipped_context_limit": skipped,
              "train_examples_skipped_invalid_evidence": invalid_evidence,
              "smoke_run": args.limit is not None, "epochs": args.epochs,
              "learning_rate": args.learning_rate, "gradient_accumulation": args.gradient_accumulation,
              "max_tokens": args.max_tokens, "seed": args.seed, "trainable_parameters": trainable,
              "optimization_steps": steps, "device": torch.cuda.get_device_name(0),
              "torch": torch.__version__, "peak_gpu_bytes": torch.cuda.max_memory_allocated(),
              "seconds": round(time.perf_counter() - started, 2),
              "code_commit": commit.stdout.strip() if commit.returncode == 0 else None,
              "code_dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None}
    (args.out / "train_config.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
