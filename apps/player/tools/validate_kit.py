#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
import json
import re
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contract" / "learnit-import.schema.json"
CAPABILITIES_PATH = ROOT / "contract" / "learnit-capabilities.json"
TAXONOMY_PATH = ROOT / "contract" / "pedagogical-taxonomy.json"
FORBIDDEN_TEXT = re.compile(r"\b(?:TODO|DEBUG|undefined|NaN)\b|\[BLANK", re.IGNORECASE)
SAFE_MEDIA_FORMATS = {"svg", "png", "jpeg", "jpg", "webp", "gif"}
SAFE_MEDIA_ROLES = {"concept_visual", "question_stimulus", "worked_example", "misconception_fix", "diagram_to_interpret", "memory_anchor"}
UNSAFE_SVG = re.compile(r"<script|on[a-z]+\s*=|javascript:|vbscript:|foreignObject|<iframe|<image|<use|\sstyle\s*=|(?:href|xlink:href)\s*=|url\(\s*(?!#)", re.IGNORECASE)
SAFE_RASTER_DATA = re.compile(r"^data:image/(?:png|jpe?g|webp|gif);base64,[A-Za-z0-9+/=\s]+$", re.IGNORECASE)

def media_security_error(asset: dict) -> str | None:
    data = str(asset.get('data') or asset.get('src') or asset.get('url') or asset.get('source_url') or '').strip()
    fmt = str(asset.get('format', '')).lower()
    if fmt == 'svg' or data.lower().startswith('<svg'):
        return 'unsafe-svg-content' if UNSAFE_SVG.search(data) else None
    if data.lower().startswith('data:'):
        return None if len(data) <= 5_000_000 and SAFE_RASTER_DATA.fullmatch(data) else 'unsafe-data-image'
    if data:
        return None if data.lower().startswith('https://') and len(data) <= 4096 and '@' not in data.split('://', 1)[-1].split('/', 1)[0] else 'unsafe-remote-image'
    return 'missing-media-source'


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def path_string(parts) -> str:
    return "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts)


def iter_courses(payload: dict):
    if payload.get("kind") == "learnit-course-package":
        return payload.get("courses", []), payload.get("assets", [])
    return [payload], payload.get("assets", [])


def validate_payload(payload: dict) -> dict:
    schema = load_json(SCHEMA_PATH)
    capabilities = load_json(CAPABILITIES_PATH)
    validator = Draft202012Validator(schema)
    errors: list[dict] = []
    warnings: list[dict] = []

    def add(code: str, message: str, path: str = "$", severity: str = "error"):
        item = {"code": code, "message": message, "path": path, "severity": severity}
        (errors if severity == "error" else warnings).append(item)

    for err in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path)):
        add("schema", err.message, path_string(err.absolute_path))

    if not isinstance(payload, dict):
        add("root-object", "La racine doit être un objet JSON.")
        return {"ok": False, "errors": errors, "warnings": warnings}

    contract_version = payload.get("schema_version") if payload.get("kind") == "learnit-course-package" else "learnit-content-v2"
    expected = capabilities["contract_version"]
    if payload.get("kind") == "learnit-course-package" and contract_version != expected:
        add("contract-version", f"Contrat attendu : {expected}.", "$.schema_version")

    courses, root_assets = iter_courses(payload)
    root_asset_ids = set()
    root_asset_map = {}
    for index, asset in enumerate(root_assets if isinstance(root_assets, list) else []):
        path = f"$.assets[{index}]"
        aid = asset.get("id") if isinstance(asset, dict) else None
        if aid in root_asset_ids:
            add("asset-id-duplicate", f"Asset dupliqué : {aid}", f"{path}.id")
        if aid:
            root_asset_ids.add(aid)
            root_asset_map[aid] = asset
        if isinstance(asset, dict):
            fmt = str(asset.get("format", "")).lower()
            if fmt and fmt not in SAFE_MEDIA_FORMATS:
                add("asset-format-unsupported", f"Format non supporté : {fmt}", f"{path}.format")
            if not str(asset.get("alt", "")).strip():
                add("asset-alt-missing", "Texte alternatif manquant.", f"{path}.alt", "warning")
            if str(asset.get("pedagogical_role", "")) not in SAFE_MEDIA_ROLES:
                add("asset-role-missing", "Rôle pédagogique absent ou inconnu.", f"{path}.pedagogical_role", "warning")
            security_error = media_security_error(asset)
            if security_error:
                add("media-unsafe", f"Média non sûr : {security_error}.", f"{path}.data")

    seen_titles = set()
    for ci, course in enumerate(courses if isinstance(courses, list) else []):
        cpath = f"$.courses[{ci}]" if payload.get("kind") == "learnit-course-package" else "$"
        if not isinstance(course, dict):
            continue
        title = course.get("title")
        if title in seen_titles:
            add("course-title-duplicate", f"Titre de parcours dupliqué : {title}", f"{cpath}.title")
        if title:
            seen_titles.add(title)
        course_asset_ids = set(root_asset_ids)
        course_asset_map = dict(root_asset_map)
        used_asset_ids = set()
        for ai, asset in enumerate(course.get("assets", []) if isinstance(course.get("assets"), list) else []):
            path = f"{cpath}.assets[{ai}]"
            aid = asset.get("id") if isinstance(asset, dict) else None
            if aid in course_asset_ids:
                add("asset-id-duplicate", f"Asset dupliqué : {aid}", f"{path}.id")
            if aid:
                course_asset_ids.add(aid)
                course_asset_map[aid] = asset
            if isinstance(asset, dict):
                fmt = str(asset.get("format", "")).lower()
                if fmt and fmt not in SAFE_MEDIA_FORMATS:
                    add("asset-format-unsupported", f"Format non supporté : {fmt}", f"{path}.format")
                if not str(asset.get("alt", "")).strip():
                    add("asset-alt-missing", "Texte alternatif manquant.", f"{path}.alt", "warning")
                if str(asset.get("pedagogical_role", "")) not in SAFE_MEDIA_ROLES:
                    add("asset-role-missing", "Rôle pédagogique absent ou inconnu.", f"{path}.pedagogical_role", "warning")
                security_error = media_security_error(asset)
                if security_error:
                    add("media-unsafe", f"Média non sûr : {security_error}.", f"{path}.data")
        activity_ids = set()
        objective_rows: dict[str, list[dict]] = {}
        question_seen: dict[str, str] = {}
        type_counts: Counter = Counter()
        activities = course.get("activities", []) if isinstance(course.get("activities"), list) else []
        for ai, activity in enumerate(activities):
            apath = f"{cpath}.activities[{ai}]"
            if not isinstance(activity, dict):
                continue
            aid = activity.get("id")
            if aid in activity_ids:
                add("activity-id-duplicate", f"Identifiant dupliqué : {aid}", f"{apath}.id")
            if aid:
                activity_ids.add(aid)
            kind = activity.get("type")
            type_counts[kind] += 1
            objective = str(activity.get("objective", "")).strip()
            role = str(activity.get("assessment_role", ""))
            phase = str(activity.get("learning_phase", ""))
            objective_rows.setdefault(objective, []).append({"path": apath, "id": str(aid or ''), "role": role, "phase": phase, "type": str(kind or ''), "transfer_probe": activity.get('transfer_probe') is True, "transfer_distance": str(activity.get('transfer_distance', '')), "variant_of": str(activity.get('variant_of', ''))})
            question_key = re.sub(r"\s+", " ", str(activity.get("question", "")).lower()).strip()
            if question_key and question_key in question_seen:
                add("question-exact-duplicate", "Question répétée à l’identique.", f"{apath}.question", "warning")
            elif question_key:
                question_seen[question_key] = apath
            declared = capabilities.get("activity_types", {}).get(kind)
            if declared and declared.get("status") != "stable":
                add("activity-not-stable", f"Le type {kind} n’est pas stable.", f"{apath}.type")
            if kind == "qcm" and isinstance(activity.get("choices"), list) and isinstance(activity.get("answer"), int):
                if activity["answer"] >= len(activity["choices"]):
                    add("qcm-answer-range", "L’index answer dépasse choices[].", f"{apath}.answer")
                if len(set(activity["choices"])) != len(activity["choices"]):
                    add("qcm-choice-duplicate", "Les choix QCM doivent être distincts.", f"{apath}.choices")
            if kind == "fill" and isinstance(activity.get("tokens"), list) and isinstance(activity.get("answer"), list):
                missing = [value for value in activity["answer"] if value not in activity["tokens"]]
                if missing:
                    add("fill-answer-token-missing", f"Réponses absentes des tokens : {missing}", f"{apath}.answer")
                indexes = [part for part in activity.get("parts", []) if isinstance(part, int)]
                if indexes and max(indexes) >= len(activity["answer"]):
                    add("fill-part-index-range", "Un index de parts[] dépasse answer[].", f"{apath}.parts")
            if kind == "order" and isinstance(activity.get("tokens"), list) and isinstance(activity.get("answer"), list):
                if Counter(activity["tokens"]) != Counter(activity["answer"]):
                    add("order-answer-token-mismatch", "tokens[] et answer[] doivent contenir les mêmes éléments.", apath)
            if kind == "matching" and isinstance(activity.get("pairs"), list):
                left = [p[0] for p in activity["pairs"] if isinstance(p, list) and len(p) == 2]
                right = [p[1] for p in activity["pairs"] if isinstance(p, list) and len(p) == 2]
                if len(set(left)) != len(left) or len(set(right)) != len(right):
                    add("matching-pair-duplicate", "Les deux colonnes de matching doivent être injectives.", f"{apath}.pairs")
            if activity.get('transfer_probe') is True:
                if phase != 'transfer':
                    add('transfer-probe-phase', 'Un transfer_probe doit utiliser learning_phase=transfer.', f'{apath}.learning_phase')
                if str(activity.get('transfer_distance', '')) not in {'near', 'far'}:
                    add('transfer-distance-missing', 'Un transfer_probe doit préciser transfer_distance: near ou far.', f'{apath}.transfer_distance')
                if not str(activity.get('variant_of', '')).strip():
                    add('transfer-variant-link-missing', 'Un transfer_probe doit référencer une activité source avec variant_of.', f'{apath}.variant_of')
                elif str(activity.get('variant_of')) == str(aid):
                    add('transfer-variant-self-reference', 'variant_of ne peut pas référencer la même activité.', f'{apath}.variant_of')
            for mi, media in enumerate(activity.get("media", []) if isinstance(activity.get("media"), list) else []):
                ref = media.get("assetId") if isinstance(media, dict) else None
                if ref and ref not in course_asset_ids:
                    add("media-asset-missing", f"Asset introuvable : {ref}", f"{apath}.media[{mi}].assetId")
                elif ref:
                    used_asset_ids.add(ref)
            serialized = json.dumps(activity, ensure_ascii=False)
            if FORBIDDEN_TEXT.search(serialized):
                add("forbidden-visible-marker", "Marqueur technique visible détecté.", apath)

        for objective, rows in objective_rows.items():
            for row in rows:
                if row.get('transfer_probe') and row.get('variant_of') and row.get('variant_of') not in activity_ids:
                    add('transfer-variant-source-missing', f"Activité source introuvable : {row.get('variant_of')}", f"{row.get('path')}.variant_of")
        for asset_id in sorted(course_asset_ids):
            if asset_id not in used_asset_ids:
                add("asset-unused", f"Asset non utilisé : {asset_id}", f"{cpath}.assets", "advice")
        for objective, rows in objective_rows.items():
            if not objective:
                continue
            base = rows[0]["path"]
            if len(rows) < 2:
                add("objective-single-evidence", f"Objectif couvert par une seule activité : {objective}", f"{base}.objective", "advice")
            if not any(row["role"] == "validation" for row in rows):
                add("objective-no-validation", f"Aucune validation pour : {objective}", f"{base}.assessment_role", "warning")
            if not any(row["role"] == "remediation" or row["phase"] == "remediation" for row in rows):
                add("objective-no-remediation", f"Aucune remédiation dédiée pour : {objective}", f"{base}.assessment_role", "warning")
            if len(activities) >= 6 and not any(row["phase"] == "transfer" for row in rows):
                add("objective-no-transfer", f"Aucun transfert explicite pour : {objective}", f"{base}.learning_phase", "advice")
            if len(activities) >= 6 and any(row['phase'] == 'transfer' for row in rows) and not any(row.get('transfer_probe') and row.get('transfer_distance') == 'far' for row in rows):
                add('objective-no-far-transfer-probe', f"Aucun probe de transfert lointain pour : {objective}", f"{base}.transfer_probe", 'advice')
            if len(activities) >= 6 and not any(row['role'] in {'diagnostic','validation'} and row['phase'] in {'application','transfer','validation','diagnostic'} for row in rows):
                add('objective-no-higher-order-assessment', f"Aucune évaluation d’application ou de transfert pour : {objective}", f"{base}.assessment_role", 'warning')
        if len(activities) >= 8 and len([kind for kind, count in type_counts.items() if kind and count]) < 3:
            add("course-format-imbalance", "Moins de trois formats d’activité dans un parcours long.", f"{cpath}.activities", "warning")

    return {
        "schema": "learnit.kit_validation_report.v1",
        "ok": not errors,
        "contract_version": capabilities["contract_version"],
        "errors": errors,
        "warnings": warnings,
        "summary": {"errors": len(errors), "warnings": len(warnings)},
    }


def main() -> int:
    parser = ArgumentParser(description="Valide un kit contre le contrat strict Learn-it publié par l’application.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    reports = []
    for path in args.files:
        try:
            payload = load_json(path)
            report = validate_payload(payload)
        except Exception as exc:
            report = {"schema": "learnit.kit_validation_report.v1", "ok": False, "errors": [{"code": "read", "message": str(exc), "path": "$", "severity": "error"}], "warnings": [], "summary": {"errors": 1, "warnings": 0}}
        reports.append({"file": str(path), **report})
    result = {"ok": all(r["ok"] for r in reports), "reports": reports}
    if args.json_output or len(reports) > 1:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        report = reports[0]
        print(f"{'PASS' if report['ok'] else 'HOLD'} — {report['file']} — {report['summary']['errors']} erreur(s), {report['summary']['warnings']} alerte(s)")
        for item in report["errors"] + report["warnings"]:
            print(f"- {item['severity'].upper()} {item['code']} {item['path']}: {item['message']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
