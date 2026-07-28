#!/usr/bin/env python3
"""Deterministic, fail-closed Learn-it Next single-file build."""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps/learnit-next"
MANIFEST_PATH = APP / "source_manifest.json"
DEFAULT_OUTPUT = APP / "dist/learnit-next.html"
ARTIFACT_REL = "apps/learnit-next/dist/learnit-next.html"
SELF_PATH = "apps/learnit-next/source_manifest.json"
SELF_KIND = "canonical-self-sha256"
BLOB_KIND = "git-blob-sha1"
IMPORT_RE = re.compile(
    r"""(?P<prefix>\b(?:import|export)\s+(?:(?:[^'";]*?)\s+from\s+)?)(?P<quote>['"])(?P<spec>[^'"]+)(?P=quote)""",
    re.MULTILINE,
)


class BuildError(RuntimeError):
    """A deterministic build contract was violated."""


def duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BuildError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=duplicate_rejecting_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot read JSON {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise BuildError(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def manifest_self_digest(manifest: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(manifest, ensure_ascii=False))
    hits = [
        item for item in clone.get("workingFiles", [])
        if item.get("path") == SELF_PATH
    ]
    if len(hits) != 1:
        raise BuildError("manifest must contain its own path exactly once")
    hits[0]["fingerprint"]["value"] = None
    return sha256(canonical_bytes(clone))


def git_blob_bytes(blob_sha: str) -> bytes:
    if not (ROOT / ".git").exists():
        raise BuildError(
            f"declared file is absent and Git object access is unavailable: {blob_sha}"
        )
    process = subprocess.run(
        ["git", "cat-file", "blob", blob_sha],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode:
        detail = process.stderr.decode("utf-8", "replace").strip()
        raise BuildError(f"cannot read declared Git blob {blob_sha}: {detail}")
    return process.stdout


def item_bytes(item: dict[str, Any]) -> bytes:
    path = str(item["path"])
    target = ROOT / path
    if target.is_file():
        return target.read_bytes()
    fingerprint = item.get("fingerprint", {})
    if fingerprint.get("kind") != BLOB_KIND:
        raise BuildError(f"missing non-blob manifest file: {path}")
    return git_blob_bytes(str(fingerprint.get("value", "")))


def validate_manifest() -> tuple[dict[str, Any], list[str], dict[str, bytes]]:
    manifest = load_json(MANIFEST_PATH)
    if manifest.get("schema") != "learnit.next.source-manifest.v2":
        raise BuildError("unsupported source manifest schema")
    if manifest.get("workPackage") != "PROG-WP-001":
        raise BuildError("source manifest work package differs")

    items = manifest.get("workingFiles")
    if not isinstance(items, list) or not items:
        raise BuildError("workingFiles must be a non-empty list")
    paths = [item.get("path") for item in items if isinstance(item, dict)]
    if len(paths) != len(items) or len(set(paths)) != len(paths):
        raise BuildError("workingFiles paths must be unique strings")
    if manifest.get("fileBudget") != len(items):
        raise BuildError("manifest fileBudget differs from workingFiles count")

    ordered = manifest.get("build", {}).get("orderedSources")
    if not isinstance(ordered, list) or not ordered or len(set(ordered)) != len(ordered):
        raise BuildError("build.orderedSources must be a unique non-empty list")
    required = {
        "apps/learnit-next/index.template.html",
        "apps/learnit-next/src/styles.css",
        "apps/learnit-next/src/main.js",
    }
    if not required.issubset(set(ordered)):
        raise BuildError("canonical template, stylesheet or main module is absent")
    if not set(ordered).issubset(set(paths)):
        raise BuildError("ordered build source is absent from workingFiles")
    if manifest.get("artifact", {}).get("path") != ARTIFACT_REL:
        raise BuildError("manifest artifact path is not canonical")

    data_by_path: dict[str, bytes] = {}
    for item in items:
        path = str(item["path"])
        fingerprint = item.get("fingerprint", {})
        kind = fingerprint.get("kind")
        declared = fingerprint.get("value")
        if path == SELF_PATH:
            actual = manifest_self_digest(manifest)
            if kind != SELF_KIND or declared != actual:
                raise BuildError(
                    f"source manifest self fingerprint is stale: expected={declared} actual={actual}"
                )
            data_by_path[path] = MANIFEST_PATH.read_bytes()
            continue
        data = item_bytes(item)
        actual = git_blob_sha1(data)
        if kind != BLOB_KIND or declared != actual:
            raise BuildError(
                f"stale Git blob fingerprint: {path}: expected={declared} actual={actual}"
            )
        data_by_path[path] = data

    actual_source_files: set[str] = set()
    template = APP / "index.template.html"
    if template.is_file():
        actual_source_files.add(template.relative_to(ROOT).as_posix())
    source_root = APP / "src"
    if source_root.exists():
        actual_source_files.update(
            path.relative_to(ROOT).as_posix()
            for path in source_root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    extras = actual_source_files - set(ordered)
    missing = set(ordered) - set(data_by_path)
    if extras or missing:
        raise BuildError(f"source tree drift: extra={sorted(extras)}, missing={sorted(missing)}")

    return manifest, ordered, data_by_path


def resolve_import(current: str, specifier: str, known: set[str]) -> str:
    if not specifier.startswith("."):
        raise BuildError(f"external module import is forbidden: {current} -> {specifier}")
    target = posixpath.normpath(posixpath.join(posixpath.dirname(current), specifier))
    if target not in known:
        raise BuildError(f"undeclared module import: {current} -> {target}")
    return target


def prepare_modules(
    ordered: list[str], data_by_path: dict[str, bytes]
) -> tuple[dict[str, str], dict[str, list[tuple[str, str]]], list[str]]:
    module_paths = [path for path in ordered if path.endswith(".js")]
    known = set(module_paths)
    sources: dict[str, str] = {}
    dependencies: dict[str, list[tuple[str, str]]] = {}
    token_counter = 0

    for path in module_paths:
        try:
            source = data_by_path[path].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BuildError(f"JavaScript source is not UTF-8: {path}") from exc
        deps: list[tuple[str, str]] = []

        def replace(match: re.Match[str]) -> str:
            nonlocal token_counter
            target = resolve_import(path, match.group("spec"), known)
            token = f"__LEARNIT_MODULE_URL_{token_counter:04d}__"
            token_counter += 1
            deps.append((token, target))
            return f"{match.group('prefix')}{match.group('quote')}{token}{match.group('quote')}"

        sources[path] = IMPORT_RE.sub(replace, source)
        dependencies[path] = deps

    order: list[str] = []
    state: dict[str, int] = {}

    def visit(path: str) -> None:
        status = state.get(path, 0)
        if status == 1:
            raise BuildError(f"cyclic ES module graph is unsupported: {path}")
        if status == 2:
            return
        state[path] = 1
        for _, target in dependencies[path]:
            visit(target)
        state[path] = 2
        order.append(path)

    for path in module_paths:
        visit(path)
    return sources, dependencies, order


def safe_json(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_artifact(ordered: list[str], data_by_path: dict[str, bytes]) -> bytes:
    template_path = "apps/learnit-next/index.template.html"
    css_path = "apps/learnit-next/src/styles.css"
    main_path = "apps/learnit-next/src/main.js"
    try:
        template = data_by_path[template_path].decode("utf-8")
        css = data_by_path[css_path].decode("utf-8").rstrip()
    except UnicodeDecodeError as exc:
        raise BuildError("template or stylesheet is not UTF-8") from exc

    sources, dependencies, module_order = prepare_modules(ordered, data_by_path)
    if main_path not in sources:
        raise BuildError("main.js is absent from the module graph")

    bootstrap = (
        "const __sources=Object.freeze(" + safe_json(sources) + ");\n"
        "const __dependencies=Object.freeze(" + safe_json(dependencies) + ");\n"
        "const __order=Object.freeze(" + safe_json(module_order) + ");\n"
        "const __urls=Object.create(null);\n"
        "for(const __id of __order){\n"
        "  let __source=__sources[__id];\n"
        "  for(const [__token,__target] of __dependencies[__id]){\n"
        "    const __url=__urls[__target];\n"
        "    if(!__url)throw new Error(`Unresolved bundled module: ${__id} -> ${__target}`);\n"
        "    __source=__source.split(__token).join(__url);\n"
        "  }\n"
        "  __urls[__id]=URL.createObjectURL(new Blob([__source],{type:'text/javascript'}));\n"
        "}\n"
        "await import(__urls[" + json.dumps(main_path) + "]);\n"
    )

    link = '<link rel="stylesheet" href="./src/styles.css">'
    module = '<script type="module" src="./src/main.js"></script>'
    if template.count(link) != 1 or template.count(module) != 1:
        raise BuildError("template entry points are not the frozen expected form")
    artifact = template.replace(link, f"<style>\n{css}\n</style>").replace(
        module, f'<script type="module">\n{bootstrap}</script>'
    )
    return (artifact.rstrip() + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        _, ordered, data_by_path = validate_manifest()
        artifact = render_artifact(ordered, data_by_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(artifact)
        print(
            json.dumps(
                {
                    "artifact": output.relative_to(ROOT).as_posix(),
                    "bytes": len(artifact),
                    "sha256": sha256(artifact),
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:
        print(f"LEARNIT_NEXT_BUILD_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
