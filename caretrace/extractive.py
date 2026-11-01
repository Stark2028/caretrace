"""Conservative, source-preserving extraction for a lightweight review demo.

This engine returns literal source spans. It can still miss or misclassify intent.
"""

from __future__ import annotations

import re

from .contracts import Turn, validate_orders


class ExtractiveEngine:
    name = "source-v1"
    ACTION = re.compile(r"\b(order|arrange|schedule|book|prescribe|start|continue|refill|increase|decrease|stop|discontinue)\s+(?:you\s+on\s+|with\s+|the\s+|an?\s+)?", re.I)
    IMAGING = re.compile(r"\b(?:x[- ]?ray|mri|ct\s+scan|ultrasound|mammogram|echocardiogram|echo)\b", re.I)
    LAB = re.compile(r"\b(?:blood\s*(?:test|work|count)|bloodwork|lab(?:s|oratory)?|cbc|bmp|cmp|urinalysis|culture|thyroid\s+(?:panel|test)|lipid\s+panel|autoimmune\s+panel|hemoglobin\s+a1c|hba1c|kidney\s+function|liver\s+function|creatinine|cholesterol\s+test)\b", re.I)
    FOLLOW = re.compile(r"\b(?:follow[- ]?up|appointment|review|physical\s+therapy|referral)\b", re.I)
    MEDICATION = re.compile(r"\b(?:mg|milligrams?|tablets?|capsules?|inhalers?|medication|antibiotic|insulin|aspirin|metformin|tramadol|ultram|amoxicillin|ibuprofen|albuterol|lasix|lisinopril|synthroid|levothyroxine|norvasc|hydrochlorothiazide|naprosyn|flexeril)\b", re.I)
    EXCLUDE = re.compile(r"\b(?:don't|do\s+not|won't|will\s+not|not\s+going\s+to|no\s+need\s+to|avoid|cancel|might|consider|if)\b", re.I)
    HISTORY = re.compile(r"\b(?:previously|last\s+(?:visit|time|year|month|week)|was\s+(?:told\s+to|going\s+to)|used\s+to)\b", re.I)
    END = re.compile(r"\.(?!\d)|[!?;]|,\s*(?:okay|all\s+right)|\b(?:because|and\s+then|hey\s*,?\s*dragon)\b", re.I)
    FOLLOW_ACTION = re.compile(r"\b(?:follow[- ]?up\s+(?:in|after|next|with)|see\s+(?:you|her|him)\s+(?:back|again)|come\s+back|return\s+in)\b[^.!?;]*", re.I)

    def extract(self, turns: list[Turn]) -> list[dict]:
        candidates = []
        for turn in turns:
            if turn.speaker != "doctor":
                continue
            actions = list(self.ACTION.finditer(turn.text))
            for index, action in enumerate(actions):
                # Negation is checked within the current clause rather than across a whole visit.
                clause_start = max(turn.text.rfind(mark, 0, action.start()) for mark in ".;?!") + 1
                prefix = turn.text[clause_start:action.start()]
                if self.EXCLUDE.search(prefix) or self.HISTORY.search(prefix):
                    continue
                end = actions[index + 1].start() if index + 1 < len(actions) else len(turn.text)
                ending = self.END.search(turn.text, action.end(), end)
                if ending:
                    end = ending.start()
                start = action.end()
                fragment = turn.text[start:end].strip(" ,:")
                if not fragment or len(fragment) > 500:
                    continue
                if self.IMAGING.search(fragment):
                    kind = "imaging"
                elif self.LAB.search(fragment):
                    kind = "lab"
                elif self.FOLLOW.search(fragment):
                    kind = "followup"
                elif action.group(1).lower() in {"prescribe", "refill"} or self.MEDICATION.search(fragment):
                    kind = "medication"
                else:
                    continue
                # Retain stop/change verbs because they alter the meaning of medication orders.
                if action.group(1).lower() in {"stop", "discontinue", "increase", "decrease"}:
                    start = action.start()
                    fragment = turn.text[start:end].strip(" ,:")
                actual_start = turn.text.find(fragment, start, end)
                candidates.append((turn, kind, fragment, actual_start, actual_start + len(fragment)))
            if not actions:
                for match in self.FOLLOW_ACTION.finditer(turn.text):
                    prefix = turn.text[max(0, match.start() - 45):match.start()]
                    if not self.EXCLUDE.search(prefix) and not self.HISTORY.search(prefix):
                        candidates.append((turn, "followup", match.group(0).strip(), match.start(), match.end()))
        result, seen = [], set()
        for turn, kind, fragment, start, end in candidates:
            key = (kind, fragment.lower())
            if key in seen:
                continue
            seen.add(key)
            item = validate_orders({"orders": [{"order_type": kind, "description": fragment,
                                    "reason": None, "provenance": [turn.id]}]}, turns)[0]
            item["source_span"] = {"turn_id": turn.id, "start": start, "end": end}
            item["origin"] = "verbatim_source"
            result.append(item)
        return result[:30]
