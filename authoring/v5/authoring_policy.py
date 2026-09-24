#!/usr/bin/env python3
"""V5 authoring-time policy checks that complement the frozen V5 validator.

The frozen contract remains structural. This module adds fail-closed authoring
policy for obvious answer leakage. It intentionally does not pretend that
string matching can prove semantic safety: a V5 Factory PASS also requires an
independent reviewer to explicitly pass hint progression and answer-leak checks.
"""
from __future__ import annotations

import re
from typing import Any

PASS = "PASS_V5_AUTHORING_POLICY_R1"
HOLD = "HOLD_V5_AUTHORING_POLICY_R1"


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def reference_urls(package: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for course in package.get("courses", []):
        if not isinstance(course, dict):
            continue
        for activity in course.get("activities", []):
            if not isinstance(activity, dict):
                continue
            for ref in activity.get("references", []) or []:
                if isinstance(ref, dict) and isinstance(ref.get("url"), str):
                    urls.append(ref["url"])
    return urls


def _answer_labels(activity: dict[str, Any]) -> list[str]:
    kind = activity.get("type")
    labels: list[str] = []
    if kind == "qcm":
        correct = activity.get("correctChoiceId")
        for choice in activity.get("choices", []):
            if isinstance(choice, dict) and choice.get("choiceId") == correct:
                labels.append(str(choice.get("label", "")))
    elif kind == "constructed":
        labels += [str(x) for x in activity.get("acceptedResponses", []) if isinstance(x, str)]
    elif kind == "fill":
        token_labels = {
            item.get("tokenId"): str(item.get("label", ""))
            for item in activity.get("tokens", []) if isinstance(item, dict)
        }
        for answer in activity.get("answers", []):
            if isinstance(answer, dict) and answer.get("tokenId") in token_labels:
                labels.append(token_labels[answer["tokenId"]])
    elif kind == "order":
        item_labels = {
            item.get("itemId"): str(item.get("label", ""))
            for item in activity.get("items", []) if isinstance(item, dict)
        }
        ordered = [item_labels.get(item_id, "") for item_id in activity.get("correctOrder", [])]
        if ordered and all(ordered):
            labels.append(" -> ".join(ordered))
            labels.append("; ".join(ordered))
    return [x for x in labels if _norm(x)]


def obvious_hint_leaks(package: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for ci, course in enumerate(package.get("courses", [])):
        if not isinstance(course, dict):
            continue
        for ai, activity in enumerate(course.get("activities", [])):
            if not isinstance(activity, dict):
                continue
            answers = [_norm(x) for x in _answer_labels(activity)]
            for hi, hint in enumerate(activity.get("hints", []) or []):
                h = _norm(hint)
                if not h:
                    continue
                for answer in answers:
                    if answer and (answer == h or (len(answer) >= 3 and answer in h)):
                        reasons.append(
                            f"HINT_REVEALS_CANONICAL_ANSWER:$.courses[{ci}].activities[{ai}].hints[{hi}]"
                        )
                        break
    return sorted(set(reasons))


def analyze(package: dict[str, Any]) -> dict[str, Any]:
    reasons = obvious_hint_leaks(package)
    hint_count = sum(
        len(activity.get("hints", []) or [])
        for course in package.get("courses", []) if isinstance(course, dict)
        for activity in course.get("activities", []) if isinstance(activity, dict)
    )
    return {
        "schema": "learnit.atlas.v5.authoring_policy_report.v1",
        "profile": "atlas.v5.authoring-policy.r1",
        "hintCount": hint_count,
        "semanticReviewRequiredForHintSafety": hint_count > 0,
        "verdict": PASS if not reasons else HOLD,
        "reasons": reasons,
    }
