"""Transparent lexical proxy for one-to-one order matching.

This is not the official MEDIQA-OE evaluator or a clinical accuracy metric.
"""

from __future__ import annotations

import re
from collections import Counter


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def token_f1(a: str, b: str) -> float:
    left, right = tokens(a), tokens(b)
    if not left or not right:
        return 0.0
    overlap = sum((Counter(left) & Counter(right)).values())
    return 2 * overlap / (len(left) + len(right))


def score_encounter(gold: list[dict], predicted: list[dict], threshold: float = 0.5,
                    valid_turns: set[int] | None = None) -> dict:
    def reference_valid(item):
        ids = set(item.get("provenance") or [])
        return bool(ids) and all(type(x) is int and x > 0 for x in ids) and (valid_turns is None or ids <= valid_turns)

    candidates = []
    for i, expected in enumerate(gold):
        for j, actual in enumerate(predicted):
            if expected["order_type"].replace("-", "") == actual["order_type"].replace("-", ""):
                similarity = token_f1(expected["description"], actual["description"])
                if similarity >= threshold:
                    candidates.append((similarity, i, j))
    used_g, used_p, evidence_hit, evidence_total, evidence_pred = set(), set(), 0, 0, 0
    # Fixed greedy matching by highest lexical overlap; transparent but not semantic adjudication.
    for _, i, j in sorted(candidates, reverse=True):
        if i in used_g or j in used_p:
            continue
        used_g.add(i)
        used_p.add(j)
        if not reference_valid(gold[i]):
            continue
        ref = set(gold[i].get("provenance") or [])
        out = set(predicted[j].get("provenance") or [])
        evidence_hit += len(ref & out)
        evidence_total += len(ref)
        evidence_pred += len(out)
    return {"gold": len(gold), "predicted": len(predicted), "matched": len(used_g),
            "evidence_hit": evidence_hit, "evidence_gold": evidence_total,
            "evidence_predicted": evidence_pred,
            "invalid_reference_evidence": sum(not reference_valid(item) for item in gold),
            "unlinked": sum(item.get("evidence_status") != "linked" for item in predicted)}


def aggregate(rows: list[dict]) -> dict:
    keys = ("gold", "predicted", "matched", "evidence_hit", "evidence_gold", "evidence_predicted", "invalid_reference_evidence", "unlinked")
    sums = {key: sum(row[key] for row in rows) for key in keys}
    p = sums["matched"] / sums["predicted"] if sums["predicted"] else 0.0
    r = sums["matched"] / sums["gold"] if sums["gold"] else 0.0
    sums.update({"encounters": len(rows), "precision_proxy": p, "recall_proxy": r,
                 "f1_proxy": 2 * p * r / (p + r) if p + r else 0.0,
                 "evidence_precision_on_matched": sums["evidence_hit"] / sums["evidence_predicted"] if sums["evidence_predicted"] else None,
                 "evidence_recall_on_matched": sums["evidence_hit"] / sums["evidence_gold"] if sums["evidence_gold"] else None})
    return sums
