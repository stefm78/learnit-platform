#!/usr/bin/env python3
"""Build a deterministic local/offline Student V0.1 pilot package."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "authoring" / "v4" / "validate_kit.py"
PREFIX = "student-v01-pilot/"
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
FILE_MODE = 0o100644
BUILDER_VERSION = "1.0"

START_HERE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Student V0.1 — démarrer</title>
<style>
body{font-family:system-ui,sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem;line-height:1.5}
a{display:inline-block;padding:.75rem 1rem;border:2px solid currentColor;border-radius:.5rem;font-weight:700}
code{overflow-wrap:anywhere}.note{padding:.75rem;border-left:4px solid currentColor}
</style>
</head>
<body>
<h1>Student V0.1 — démarrer</h1>
<p class="note">Ce paquet fonctionne localement et hors ligne. Gardez tous les fichiers dans le même dossier.</p>
<h2>Learner</h2>
<ol>
<li>Ouvrez ce fichier <code>START_HERE.html</code>.</li>
<li>Cliquez sur <a id="open-learnit" href="learnit-next.html">Ouvrir Learn-it</a>.</li>
<li>Dans Learn-it, activez « Importer un cours » pour ouvrir le sélecteur de fichier.</li>
<li>Sélectionnez <code>course.learnit.json</code>.</li>
<li>Cliquez sur « Importer ».</li>
<li>Cliquez sur « Commencer ».</li>
</ol>
<p><strong>Actions obligatoires jusqu’au démarrage du cours : 6.</strong></p>
<h2>Facilitator/setup</h2>
<ul>
<li>Extrayez complètement l’archive avant de la remettre à l’apprenant.</li>
<li>Ne renommez pas et ne séparez pas les quatre fichiers.</li>
<li>Aucune connexion Internet, compte ou service distant n’est requis.</li>
</ul>
<h2>Recovery</h2>
<ul>
<li>JSON erroné/non-V4 : revenez à la bibliothèque et choisissez <code>course.learnit.json</code>.</li>
<li>Sélecteur annulé : réactivez « Importer un cours » et sélectionnez le fichier.</li>
<li>Retour bibliothèque : utilisez « ← Bibliothèque », puis « Reprendre ».</li>
<li>Réinitialisation locale : utilisez « Réinitialiser les données locales », confirmez, puis réimportez le cours.</li>
</ul>
<p>Ce paquet ne fournit ni synchronisation cloud, ni reprise inter-appareils, ni récupération de compte.</p>
</body>
</html>
""".encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def validate_kit(path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, "-B", str(VALIDATOR), str(path), "--format=json"],
        cwd=ROOT, text=True, capture_output=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    report = json.loads(result.stdout)
    if not report.get("ok"):
        raise SystemExit("canonical V4 validation did not return ok=true")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("contract") != "learnit.kit.v4":
        raise SystemExit("pilot package requires canonical learnit.kit.v4 input")
    return payload


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(PREFIX + name, ZIP_TIME)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = FILE_MODE << 16
    info.extra = b""
    info.comment = b""
    return info


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not args.app.is_file() or not args.kit.is_file():
        raise SystemExit("explicit app and kit inputs must be existing files")
    payload = validate_kit(args.kit)
    app = args.app.read_bytes()
    kit = args.kit.read_bytes()

    manifest = {
        "schema": "student.v0.1.pilot-package.v1",
        "app": {"filename": "learnit-next.html", "bytes": len(app), "sha256": sha256(app)},
        "kit": {
            "filename": "course.learnit.json",
            "bytes": len(kit),
            "sha256": sha256(kit),
            "contract": payload["contract"],
        },
        "start": {"filename": "START_HERE.html", "mode": "DIRECT_FILE"},
        "builder": {"version": BUILDER_VERSION},
        "localOffline": True,
    }
    entries = {
        "START_HERE.html": START_HERE,
        "course.learnit.json": kit,
        "learnit-next.html": app,
        "pilot_manifest.json": canonical_json(manifest),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        archive.comment = b""
        for name in sorted(entries):
            archive.writestr(zip_info(name), entries[name])

    raw = args.output.read_bytes()
    print(f"PILOT_PACKAGE_BYTES={len(raw)}")
    print(f"PILOT_PACKAGE_SHA256={sha256(raw)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
