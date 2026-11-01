"""Interchangeable rule baseline and local Transformers inference."""

from __future__ import annotations

import os
import json
import re
import threading
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener

from .contracts import Turn, decode_json, prompt_messages, validate_orders

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
ORDER_SCHEMA = {"type": "object", "properties": {"orders": {"type": "array", "maxItems": 30,
    "items": {"type": "object", "properties": {
        "order_type": {"type": "string", "enum": ["medication", "lab", "imaging", "followup"]},
        "description": {"type": "string"}, "reason": {"type": ["string", "null"]},
        "provenance": {"type": "array", "items": {"type": "integer"}}},
        "required": ["order_type", "description", "reason", "provenance"]}}}, "required": ["orders"]}


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
        self.model = AutoModelForCausalLM.from_pretrained(model, torch_dtype=dtype, **kwargs).to(device=self.device, dtype=dtype).eval()
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


class OllamaEngine:
    """Loopback-only local Qwen inference with schema-constrained decoding."""

    def __init__(self, model: str):
        if model not in {"qwen2.5:3b", "qwen2.5:7b"}:
            raise ValueError("The Ollama adapter supports qwen2.5:3b or qwen2.5:7b.")
        self.url = os.getenv("CARETRACE_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
        parsed = urlsplit(self.url)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("Ollama must use a local loopback HTTP URL.")
        from transformers import AutoTokenizer
        self.model = model
        self.name = f"ollama:{model}"
        self.opener = build_opener(ProxyHandler({}))
        tokenizer_path = os.getenv("CARETRACE_TOKENIZER_PATH")
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path or MODEL_ID,
                                                      **({} if tokenizer_path else {"revision": MODEL_REVISION}))
        with self.opener.open(self.url + "/api/tags", timeout=10) as response:
            tags = json.load(response).get("models", [])
        found = next((item for item in tags if item.get("name") == model), None)
        if found is None:
            raise ValueError(f"Local Ollama model {model} is unavailable.")
        self.digest = found.get("digest")
        if not self.digest:
            raise ValueError("Local Ollama model did not provide an artifact digest.")
        self.lock = threading.Lock()

    def extract(self, turns: list[Turn]) -> list[dict]:
        messages = prompt_messages(turns)
        count = len(self.tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True))
        # Reserve output and template overhead so the server never silently trims history.
        if count + 1024 > 8192:
            raise ValueError("Transcript exceeds the model context limit; shorten it before retrying.")
        payload = {"model": self.model, "messages": messages, "stream": False, "format": ORDER_SCHEMA,
                   "options": {"temperature": 0, "seed": 42, "num_ctx": 8192, "num_predict": 768}}
        request = Request(self.url + "/api/chat", data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        with self.lock, self.opener.open(request, timeout=240) as response:
            data = json.load(response)
        if data.get("done_reason") == "length":
            raise ValueError("Model output reached its limit; shorten the transcript and retry.")
        return validate_orders(decode_json(data["message"]["content"]), turns)


def create_engine(selection: str):
    if selection == "rules":
        return RuleEngine()
    if selection.startswith("ollama:"):
        return OllamaEngine(selection.removeprefix("ollama:"))
    return TransformerEngine(selection)
