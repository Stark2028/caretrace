"""Shared validation and prompting for order extraction."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

ORDER_TYPES = frozenset({"medication", "lab", "imaging", "followup"})
MAX_TURNS = 300
MAX_TEXT_CHARS = 40_000


@dataclass(frozen=True)
class Turn:
    id: int
    speaker: str
    text: str


def parse_turns(text: str) -> list[Turn]:
    """Parse one speaker-labelled turn per line; optional source IDs must be unique."""
    if not text.strip() or len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"Enter 1–{MAX_TEXT_CHARS:,} characters of simulated dialogue.")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > MAX_TURNS:
        raise ValueError(f"Use at most {MAX_TURNS} turns.")
    turns = []
    pattern = re.compile(r"^(?:(\d+)\s+)?(?:\[\s*(doctor|clinician|patient|patient_guest|guest|unknown)\s*\]|(doctor|clinician|patient|guest|unknown)\s*:)\s*(.+)$", re.I)
    for position, line in enumerate(lines, 1):
        match = pattern.match(line)
        if not match:
            raise ValueError(f"Line {position}: start with 'Doctor:' or 'Patient:'.")
        number, bracketed, named, content = match.groups()
        speaker = (bracketed or named).lower()
        speaker = {"clinician": "doctor", "patient_guest": "guest"}.get(speaker, speaker)
        turns.append(Turn(int(number or position), speaker, content.strip()))
    ids = [turn.id for turn in turns]
    if any(identifier < 1 for identifier in ids) or len(ids) != len(set(ids)):
        raise ValueError("Turn numbers must be positive and unique.")
    return turns


def format_turns(turns: list[Turn]) -> str:
    return "\n".join(f"{turn.id} [{turn.speaker}] {turn.text}" for turn in turns)


def parse_enumerated(text: str) -> list[Turn]:
    """Read SIMORD turns, including empty turns and multiline source utterances."""
    pattern = re.compile(r"^\s*(\d+)\s+\[\s*([^]]+)\s*\]\s*(.*)$", re.I)
    turns: list[Turn] = []
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            number, speaker, content = match.groups()
            role = speaker.strip().lower()
            role = {"patient_guest": "guest", "clinician": "doctor"}.get(role, role)
            if role not in {"doctor", "patient", "guest", "unknown"}:
                content = f"[{speaker.strip()}] {content}".strip()
                role = "unknown"
            turns.append(Turn(int(number), role, content.strip()))
        elif not turns and re.match(r"^\s*\d+\s+\S", line):
            number, content = line.strip().split(maxsplit=1)
            turns.append(Turn(int(number), "unknown", content))
        elif line.strip() and turns:
            previous = turns[-1]
            turns[-1] = Turn(previous.id, previous.speaker, (previous.text + " " + line.strip()).strip())
        elif line.strip():
            raise ValueError("Dataset transcript starts without a numbered speaker turn")
    ids = [turn.id for turn in turns]
    if not turns or len(ids) != len(set(ids)) or any(number < 1 for number in ids):
        raise ValueError("Dataset has missing, repeated, or invalid turn IDs")
    return turns


SYSTEM = (
    "You extract explicitly planned clinician orders from simulated consultation transcripts. "
    "Return a JSON object with an orders array. Each order has order_type (medication, lab, "
    "imaging, or followup), description, reason (string or null), and provenance (list of "
    "integer turn numbers). Include supporting turns. Do not invent details or include "
    "historical, rejected, or merely hypothetical orders. Include medications only when "
    "explicitly started, renewed, changed, or stopped by the clinician; a patient's report "
    "of a prior medication is not itself an order. Do not infer a dose, timing, or clinical reason; "
    "set reason to null unless explicitly stated. Cite turns supporting the action. "
    "If none, return {\"orders\":[]}."
)


def prompt_messages(turns: list[Turn]) -> list[dict[str, str]]:
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": format_turns(turns)}]


def validate_orders(raw: object, turns: list[Turn]) -> list[dict]:
    """Reject malformed model responses and retain explicit evidence problems for review."""
    if not isinstance(raw, dict) or not isinstance(raw.get("orders"), list):
        raise ValueError("Model response must contain an orders list.")
    if len(raw["orders"]) > 30:
        raise ValueError("Model produced too many orders.")
    known = {turn.id for turn in turns}
    result = []
    for item in raw["orders"]:
        if not isinstance(item, dict):
            raise ValueError("Each order must be an object.")
        kind = str(item.get("order_type", "")).strip().lower().replace("-", "")
        description = item.get("description")
        provenance = item.get("provenance", [])
        reason = item.get("reason")
        if kind not in ORDER_TYPES or not isinstance(description, str) or not description.strip() or len(description) > 500:
            raise ValueError("An order has an invalid type or description.")
        if reason is not None and (not isinstance(reason, str) or len(reason) > 500):
            raise ValueError("An order has an invalid reason.")
        if not isinstance(provenance, list) or len(provenance) > 64 or any(type(x) is not int or x < 1 for x in provenance):
            raise ValueError("Evidence must be a list of positive turn IDs.")
        evidence = list(dict.fromkeys(provenance))
        missing = [x for x in evidence if x not in known]
        result.append({"order_type": kind, "description": description.strip(),
                       "reason": reason.strip() if reason else None,
                       "provenance": evidence,
                       "evidence_status": "missing" if not evidence else ("invalid_turn" if missing else "linked")})
    return result


def decode_json(text: str) -> object:
    """Parse one JSON object; allow a markdown fence but no extra prose."""
    content = text.strip()
    if content.startswith("```") and content.endswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.I)
        content = re.sub(r"\s*```$", "", content)
    return json.loads(content)
