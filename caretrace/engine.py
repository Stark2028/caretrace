"""Interchangeable rule baseline and local Transformers inference."""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path

from .contracts import Turn, decode_json, prompt_messages, validate_orders

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"


class RuleEngine:
    name = "rules-v1"
    PATTERNS = (
        ("lab", re.compile(r"\b(?:order|arrange|schedule|send for|get)\b.{0,70}\b(?:blood test|blood work|bloodwork|lab test|laboratory test)\b", re.I)),
        ("imaging", re.compile(r"\b(?:order|arrange|schedule|send for|get)\b.{0,70}\b(?:x[- ]?ray|mri|ct scan|ultrasound)\b", re.I)),
        ("followup", re.compile(r"\b(?:schedule|arrange|book)\b.{0,70}\b(?:follow[- ]?up|review|appointment)\b", re.I)),
    )
    NEGATED = re.compile(r"\b(?:not|don't|do not|won't|will not|cancel|cancelled|canceled|stop|stopped|previously)\b", re.I)

    def extract(self, turns: list[Turn]) -> list[dict]:
        orders = []
        for turn in turns:
            if turn.speaker != "doctor" or self.NEGATED.search(turn.text):
                continue
            for kind, pattern in self.PATTERNS:
                match = pattern.search(turn.text)
                if match:
                    orders.append({"order_type": kind, "description": match.group(0),
                                   "reason": None, "provenance": [turn.id]})
                    break
        return validate_orders({"orders": orders}, turns)


class TransformerEngine:
    """Load once on demand; supports the pinned base or a saved local checkpoint."""

    def __init__(self, model: str = MODEL_ID):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.name = f"transformers:{model}"
        local = Path(model).is_dir()
        if not local and model != MODEL_ID:
            raise ValueError("Use the pinned base model or a local checkpoint directory.")
        kwargs = {} if local else {"revision": MODEL_REVISION}
        self.tokenizer = AutoTokenizer.from_pretrained(model, **kwargs)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(model, torch_dtype=dtype, **kwargs).to(self.device).eval()
        self.lock = threading.Lock()

    def extract(self, turns: list[Turn]) -> list[dict]:
        import torch

        prompt = self.tokenizer.apply_chat_template(prompt_messages(turns), tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt")
        if inputs.input_ids.shape[1] > int(os.getenv("CARETRACE_MAX_TOKENS", "4096")):
            raise ValueError("Transcript exceeds the model context limit; shorten it before retrying.")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with self.lock, torch.inference_mode():
            result = self.model.generate(**inputs, max_new_tokens=384, do_sample=False,
                                         pad_token_id=self.tokenizer.eos_token_id)
        answer = self.tokenizer.decode(result[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return validate_orders(decode_json(answer), turns)
