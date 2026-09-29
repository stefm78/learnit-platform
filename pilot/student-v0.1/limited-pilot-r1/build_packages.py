#!/usr/bin/env python3
"""Deterministic V5-aware packaging for Student V0.1 limited pilot R1."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V5_VALIDATOR = ROOT / "authoring" / "v5" / "validate_kit.py"
JOB = "JOB_31_LIMITED_PILOT_5_6_STUDENTS_EXECUTION_R1"
WORK_PACKAGE = "ATLAS-WP-073"
CANDIDATE_SHA = "e04cf62963faae83e073cde9cffd9d33ae42dc9c"
APP_SHA256 = "7ee493b8855e4cda7703deccbf5c813391afaa5a9674d6760b75a277e0267553"
APP_BYTES = 583764
KIT_CONTRACT = "learnit.kit.v5"
KIT_SHA256 = "aeac0925e686d6055405382142ad14831c27f73992401a1748ec76b85665c62b"
JOB30_EVIDENCE_HEAD = "af14bc0a9b1988b5d42b158ae4a6b3afa544221f"
MAX_SESSIONS = 6
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
FILE_MODE = 0o100644

START_HERE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Learn-it — démarrer le cours</title>
<style>
body{font-family:system-ui,sans-serif;max-width:48rem;margin:2rem auto;padding:0 1rem;line-height:1.5}
a{display:inline-block;padding:.75rem 1rem;border:2px solid currentColor;border-radius:.5rem;font-weight:700}
code{overflow-wrap:anywhere}.note{padding:.75rem;border-left:4px solid currentColor}
</style>
</head>
<body>
<h1>Démarrer le cours</h1>
<p class="note">Ce dossier fonctionne localement et hors ligne. Gardez les quatre fichiers ensemble.</p>
<ol>
<li>Cliquez sur <a id="open-learnit" href="learnit-next.html">Ouvrir Learn-it</a>.</li>
<li>Dans Learn-it, choisissez « Importer un cours ».</li>
<li>Sélectionnez <code>course.learnit.json</code>, puis confirmez l’import.</li>
<li>Ouvrez le cours et choisissez « Commencer ».</li>
</ol>
<h2>Si quelque chose est interrompu</h2>
<ul>
<li>Si le choix du fichier est annulé, relancez simplement « Importer un cours » et choisissez <code>course.learnit.json</code>.</li>
<li>Si vous voulez repartir de zéro, utilisez « Réinitialiser les données locales », confirmez, puis réimportez <code>course.learnit.json</code>.</li>
<li>Si vous revenez à la bibliothèque, utilisez « Reprendre » pour continuer le cours.</li>
</ul>
<p>Aucune connexion Internet ni aucun compte n’est nécessaire.</p>
</body>
</html>
""".encode("utf-8")

FACILITATOR_RUNBOOK = """# Limited pilot R1 — facilitator runbook

Use only the exact learner package identified by `CHECKSUMS.json`.

Before a session:
1. Accept only `PERMISSION_STATUS: CONFIRMED` or `PERMISSION_STATUS: NOT_REQUIRED`.
2. Verify the learner-package SHA-256.
3. Confirm the frozen candidate identity is unchanged.
4. Start from clean learner state or explicitly reset local data.
5. Allocate the next unused pseudonymous ID from LP01..LP06.
6. Keep this facilitator package out of learner view.

During a session, intervene minimally. Record necessary assistance; do not teach around a defect and do not modify the candidate between students.

After a session, record only the bounded fields in `SESSION_RECORD_TEMPLATE.json`. Remove identifying details from free text before persistence.

A BLOCKER requires immediate HOLD. A MAJOR requires HOLD_PENDING_HUMAN and no next student until an explicit human decision. MINOR and NOTE may be recorded without automatic hold.

After five countable real sessions, stop for `COHORT_SIZE_DECISION: CLOSE_AT_5 | RUN_AUTHORIZED_SESSION_6`. Never admit a seventh session.
"""

SEVERITY_RUBRIC = """# Severity rubric

- **BLOCKER** — prevents safe/meaningful continuation of the pilot or invalidates the frozen candidate/package for subsequent sessions. Set `HOLD`.
- **MAJOR** — materially degrades the intended learner journey and requires an explicit human continuation decision before another student. Set `HOLD_PENDING_HUMAN`.
- **MINOR** — bounded defect or friction that does not by itself stop the cohort.
- **NOTE** — observation without a defect claim.

`HR24_003` is an already accepted known pilot limitation. Its expected behavior is not a new BLOCKER/MAJOR. Record only a materially different or worse observed delta as a new finding.
"""

PRIVACY_RULES = """# Privacy and data minimization

Repository evidence uses only pseudonymous session IDs LP01..LP06.

Do not record names, email addresses, school/class identifiers, dates of birth, precise addresses or locations, IP addresses, account identifiers or credentials, raw browser profiles, screen recordings, audio/video, participant photographs, or verbatim notes containing identifying details.

Consent/guardian/organization documents stay outside Git. Git may record only:
`PERMISSION_STATUS: CONFIRMED | NOT_REQUIRED | NOT_CONFIRMED`.

A session may run only with `CONFIRMED` or `NOT_REQUIRED`.
"""

KNOWN_LIMITATION = """# Known limitation — HR24-003

Status: `CONFIRMED_SEPARATE_ENGINE_JOB_REQUIRED`

Pilot acceptance: `ACCEPT`

This is an accepted known limitation for the first bounded cohort only. It is not repaired, resolved, implemented, or removed by JOB31.
"""

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")

def verify_inputs(app_path: Path, kit_path: Path) -> tuple[bytes, bytes, dict]:
    app = app_path.read_bytes()
    kit = kit_path.read_bytes()
    if len(app) != APP_BYTES or sha256(app) != APP_SHA256:
        raise SystemExit("frozen learner app identity mismatch")
    if sha256(kit) != KIT_SHA256:
        raise SystemExit("frozen V5 showcase identity mismatch")
    payload = json.loads(kit.decode("utf-8"))
    if payload.get("contract") != KIT_CONTRACT:
        raise SystemExit("pilot kit is not exact learnit.kit.v5")
    result = subprocess.run(
        [sys.executable, "-B", str(V5_VALIDATOR), str(kit_path), "--format=json"],
        cwd=ROOT, text=True, capture_output=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    report = json.loads(result.stdout)
    if not report.get("ok"):
        raise SystemExit("V5 validator did not return ok=true")
    return app, kit, payload

def pilot_identity() -> dict:
    return {
        "schema": "student.v0.1.limited-pilot-identity.v1",
        "job": JOB,
        "workPackage": WORK_PACKAGE,
        "candidateSha": CANDIDATE_SHA,
        "appSha256": APP_SHA256,
        "appBytes": APP_BYTES,
        "kitContract": KIT_CONTRACT,
        "kitSha256": KIT_SHA256,
        "job30EvidenceHead": JOB30_EVIDENCE_HEAD,
        "g5Pass": "DECLARED",
        "finalDecision": "GO_LIMITED_PILOT",
        "maxAuthorizedStudentSessions": MAX_SESSIONS,
        "hr24_003": "CONFIRMED_SEPARATE_ENGINE_JOB_REQUIRED",
        "hr24_003PilotAcceptance": "ACCEPT",
    }

def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, ZIP_TIME)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = FILE_MODE << 16
    info.extra = b""
    info.comment = b""
    return info

def write_zip(path: Path, entries: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        archive.comment = b""
        for name in sorted(entries):
            archive.writestr(zip_info(name), entries[name])

def session_template() -> dict:
    return {
        "schema": "student.v0.1.limited-pilot-session.v1",
        "sessionId": "LP0N",
        "candidateSha": CANDIDATE_SHA,
        "learnerPackageSha256": "<exact learner package sha256>",
        "permissionStatus": "CONFIRMED",
        "sessionStatus": "COMPLETED",
        "durationMinutes": None,
        "courseCompleted": None,
        "activitiesCompleted": None,
        "facilitatorAssistanceCount": None,
        "recoveryOrResumeObserved": None,
        "technicalIncidents": [],
        "findings": [],
        "postSessionRatings": {
            "startClarity": None,
            "flowClarity": None,
            "feedbackTrust": None,
            "progressClarity": None,
            "overallEase": None,
        },
        "sanitizedFacilitatorSummary": "",
        "evidenceSource": "REAL_HUMAN_FACILITATOR_USER_PROVIDED_EVIDENCE",
        "recordedAt": None,
    }

def ledger_template() -> dict:
    return {
        "schema": "student.v0.1.limited-pilot-ledger.v1",
        "candidateSha": CANDIDATE_SHA,
        "maxAuthorizedStudentSessions": MAX_SESSIONS,
        "slots": [{"sessionId": f"LP0{i}", "status": "NOT_RUN"} for i in range(1, 7)],
    }

def build(app_path: Path, kit_path: Path, learner_out: Path, facilitator_out: Path) -> dict:
    app, kit, _ = verify_inputs(app_path, kit_path)
    identity = pilot_identity()
    learner_entries = {
        "START_HERE.html": START_HERE,
        "course.learnit.json": kit,
        "learnit-next.html": app,
        "pilot_identity.json": canonical_json(identity),
    }
    write_zip(learner_out, learner_entries)
    learner_raw = learner_out.read_bytes()
    learner_sha = sha256(learner_raw)

    checksums = {
        "schema": "student.v0.1.limited-pilot-checksums.v1",
        "candidateSha": CANDIDATE_SHA,
        "app": {"bytes": APP_BYTES, "sha256": APP_SHA256},
        "kit": {"contract": KIT_CONTRACT, "sha256": KIT_SHA256},
        "learnerPackage": {"filename": learner_out.name, "sha256": learner_sha},
        "job30EvidenceHead": JOB30_EVIDENCE_HEAD,
    }
    facilitator_entries = {
        "CHECKSUMS.json": canonical_json(checksums),
        "COHORT_LEDGER_TEMPLATE.json": canonical_json(ledger_template()),
        "FACILITATOR_RUNBOOK.md": FACILITATOR_RUNBOOK.encode("utf-8"),
        "KNOWN_LIMITATION_HR24_003.md": KNOWN_LIMITATION.encode("utf-8"),
        "PRIVACY_DATA_MINIMIZATION.md": PRIVACY_RULES.encode("utf-8"),
        "SESSION_RECORD_TEMPLATE.json": canonical_json(session_template()),
        "SEVERITY_RUBRIC.md": SEVERITY_RUBRIC.encode("utf-8"),
        "pilot_identity.json": canonical_json(identity),
    }
    write_zip(facilitator_out, facilitator_entries)
    facilitator_raw = facilitator_out.read_bytes()
    return {
        "learner": {"bytes": len(learner_raw), "sha256": learner_sha, "path": str(learner_out)},
        "facilitator": {"bytes": len(facilitator_raw), "sha256": sha256(facilitator_raw), "path": str(facilitator_out)},
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--learner-output", type=Path, required=True)
    parser.add_argument("--facilitator-output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.app, args.kit, args.learner_output, args.facilitator_output)
    print(json.dumps(result, sort_keys=True))
    print("MACHINE_SMOKE_ONLY_NOT_A_REAL_STUDENT_SESSION")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
