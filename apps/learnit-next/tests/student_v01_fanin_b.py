#!/usr/bin/env python3
"""Student V0.1 JOB08 Fan-in B exact integration oracle."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import threading
import zipfile
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BASE = "d5050bace4c7dcbb63dcfe44a64ef344434e9bc2"
MANIFEST_PATH = Path("qualification/STUDENT_V01_G3_R1_FANIN_B_INPUT_MANIFEST.json")
MANIFEST_BLOB = "d76d624b6e76655b60b1a43b1dafbce22d3eb087"
KIT_PATH = Path("showcase/student-v0.1/nombres-complexes/nombres_complexes_student_v01_v4.json")
CONTEXT_PATH = Path("showcase/student-v0.1/nombres-complexes/FACTORY_CONTEXT.json")
SOURCE_PATH = Path("authoring/v2/atlas/nombres_complexes_atlas.json")
SEMANTIC_REVIEW_PATH = Path("qualification/STUDENT_V01_G3_R1_JOB06_SEMANTIC_REVIEW.json")
APP_PATH = Path("apps/learnit-next/dist/learnit-next.html")
EXPECTED_APP_BYTES = 478657
EXPECTED_APP_SHA256 = "85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e"
EXPECTED_KIT_SHA256 = "da2beb6df6f490c6637d5de22ce1c8fc99fafe89a2ba4b0e6c698b0544c193ff"
EXPECTED_PACKAGE_BYTES = 496658
EXPECTED_PACKAGE_SHA256 = "a3d3db4c63fae89b47e1d7a1341ebb522f31df69e1b107ada2ecbb9a11c4ac10"
EXPECTED_CONTEXT = {
    "kitSha256": "sha256:da2beb6df6f490c6637d5de22ce1c8fc99fafe89a2ba4b0e6c698b0544c193ff",
    "briefSha256": "sha256:fe440c7499de6d9bc0ddd40bbd165a92bacf4e81719dcf3da9f9805e1f90639a",
    "contextDigest": "sha256:eab953d540af138f1da0b030d9cee97fdeab4060b76bfc832ab018f7abd89123",
    "sourceSetDigest": "sha256:ab3feaf05bff1240ad795f9afadf954c61311aa4b748f34a108ec19e76da0b83",
}
SOURCE_BLOB = "7f83784e8719917496a694b2ad170d724190fd04"
SEMANTIC_REVIEW_BLOB = "e9b0aa9d9b521a11cf83f9dfd741a5617124a267"
FROZEN_PREFIXES = (
    "qa/student-v0.1/",
    "showcase/student-v0.1/nombres-complexes/",
    "pilot/student-v0.1/",
)
PRODUCT_PATHS = (
    "apps/learnit-next/src",
    "apps/learnit-next/build.py",
    "apps/learnit-next/index.template.html",
    "apps/learnit-next/source_manifest.json",
    "contracts",
    "authoring",
)
FORBIDDEN = {"correctChoiceId", "answers", "acceptedResponses", "matches", "correctOrder", "assignments"}


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=True, text=True, capture_output=True)


def git(*args: str) -> str:
    return run("git", *args).stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def verify_identity() -> dict[str, Any]:
    manifest_blob = git("rev-parse", f"HEAD:{MANIFEST_PATH.as_posix()}")
    assert manifest_blob == MANIFEST_BLOB, (manifest_blob, MANIFEST_BLOB)
    manifest = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    assert manifest["schema"] == "learnit.student-v0.1.g3-r1-fanin-b-inputs.v1"
    assert manifest["g3R1Base"] == "7c13d67a76705b4452304c0f6a882504bc7701a7"
    assert manifest["repairedProduct"]["resultSha"] == "bdb66bffefd6738e3cb4004d304159e9d3d048ce"
    assert manifest["job05R1"]["resultSha"] == "1c92cad7ea576a613b6f198768bbebd114a06082"
    assert manifest["job06R1"]["resultSha"] == "80ec72fef535e78013a9f0fb10bedb57f05bc761"
    assert manifest["job07R2"]["resultSha"] == "5e492fddc4d5cf00c71bdb770eb1aeac11a63803"

    expected: dict[str, str] = {}
    for role in ("job05R1", "job06R1", "job07R2"):
        assert manifest[role]["accepted"] is True
        for entry in manifest[role]["payload"]:
            expected[entry["path"]] = entry["gitBlobSha1"]

    actual_files: set[str] = set()
    for prefix in FROZEN_PREFIXES:
        actual_files.update(line for line in git("ls-files", prefix).splitlines() if line)
    assert actual_files == set(expected), {
        "missing": sorted(set(expected) - actual_files),
        "unexpected": sorted(actual_files - set(expected)),
    }
    for path, blob in sorted(expected.items()):
        assert git("rev-parse", f"HEAD:{path}") == blob, path
        assert git("hash-object", path) == blob, path

    assert sha256(KIT_PATH) == EXPECTED_KIT_SHA256
    assert git("rev-parse", f"HEAD:{SOURCE_PATH.as_posix()}") == SOURCE_BLOB
    assert git("rev-parse", f"HEAD:{SEMANTIC_REVIEW_PATH.as_posix()}") == SEMANTIC_REVIEW_BLOB
    context = json.loads((ROOT / CONTEXT_PATH).read_text(encoding="utf-8"))
    for key, value in EXPECTED_CONTEXT.items():
        assert context[key] == value, (key, context[key], value)

    diff = subprocess.run(
        ["git", "diff", "--quiet", BASE, "HEAD", "--", *PRODUCT_PATHS],
        cwd=ROOT,
        check=False,
    )
    assert diff.returncode == 0, "product/build/contract/authoring inputs drifted from JOB08_BASE"

    result = {
        "schema": "learnit.student-v0.1.job08-fanin-b-oracle.v1",
        "manifestBlob": manifest_blob,
        "payloadFiles": len(expected),
        "kitSha256": sha256(KIT_PATH),
        "productImmutable": True,
        "verdict": "PASS",
    }
    print(json.dumps(result, sort_keys=True))
    print("STUDENT_V01_JOB08_FANIN_MANIFEST_IDENTITY=PASS")
    print("STUDENT_V01_JOB08_ROLE_PAYLOAD_IDENTITY=PASS")
    print("STUDENT_V01_JOB08_PRODUCT_IMMUTABILITY=PASS")
    print("STUDENT_V01_JOB08_FANIN_B_ORACLE=PASS")
    return result


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:
        return


@contextmanager
def artifact_server(directory: Path, filename: str):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(directory)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/{filename}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def assert_safe(page, family: str) -> None:
    snapshot = page.evaluate("""async forbidden => {
      const session = await window.__LEARNIT_NEXT_TEST__.getSession();
      const activity = session?.currentActivity;
      const hits = [];
      const walk = value => {
        if (!value || typeof value !== 'object') return;
        for (const [key, child] of Object.entries(value)) {
          if (forbidden.includes(key)) hits.push(key);
          walk(child);
        }
      };
      walk(activity);
      return {
        keys: activity ? Object.keys(activity).sort() : [],
        type: activity?.presentation?.type ?? null,
        hits,
      };
    }""", sorted(FORBIDDEN))
    assert snapshot["keys"] == ["activityRevisionId", "presentation"], snapshot
    assert snapshot["type"] == family, snapshot
    assert snapshot["hits"] == [], snapshot
    html = page.locator(f'[data-activity-presentation="{family}"]').evaluate("(el) => el.outerHTML")
    for key in FORBIDDEN:
        assert key not in html, (key, family)


def submit(page, scored: bool) -> None:
    page.locator('[data-served-activity-submit="true"]').click()
    feedback = page.locator("[data-served-feedback]")
    feedback.wait_for()
    assert feedback.get_attribute("data-served-feedback") == ("scored" if scored else "non-scored")
    text = feedback.inner_text()
    if scored:
        assert "Réponse correcte" in text, text
    else:
        assert "Activité terminée" in text, text
        assert "Réponse correcte" not in text and "Pas tout à fait" not in text, text


def answer(page, activity: dict[str, Any]) -> None:
    family = activity["type"]
    if family == "lesson":
        page.locator('[data-activity-continue="lesson"]').click()
        submit(page, False)
    elif family == "flashcard":
        page.locator('[data-flashcard-reveal="true"]').click()
        page.locator('[data-activity-continue="flashcard"]').click()
        submit(page, False)
    elif family == "matching":
        for pair in activity["matches"]:
            page.locator(f'[data-matching-left="{pair["leftItemId"]}"]').click()
            page.locator(f'[data-matching-right="{pair["rightItemId"]}"]').click()
        submit(page, True)
    elif family == "order":
        desired = activity["correctOrder"]
        rows = page.locator("[data-order-item]")
        for target_index, item_id in enumerate(desired):
            for _ in range(len(desired) + 1):
                current = [rows.nth(i).get_attribute("data-order-item") for i in range(rows.count())]
                index = current.index(item_id)
                if index == target_index:
                    break
                assert index > target_index, (desired, current)
                page.locator(f'[data-order-item="{item_id}"] [data-order-move="up"]').click()
            else:
                raise AssertionError("could not establish correct order")
        submit(page, True)
    elif family == "qcm":
        page.locator(f'[data-activity-choice="true"][value="{activity["correctChoiceId"]}"]').check()
        submit(page, True)
    elif family == "fill":
        for item in activity["answers"]:
            page.locator(f'[data-activity-slot="{item["slotId"]}"]').select_option(item["tokenId"])
        submit(page, True)
    elif family == "constructed":
        page.locator("[data-constructed-response]").fill(activity["acceptedResponses"][0])
        submit(page, True)
    elif family == "classify":
        for item in activity["assignments"]:
            page.locator(f'[data-classify-select="{item["itemId"]}"]').select_option(item["bucketId"])
        submit(page, True)
    else:
        raise AssertionError(f"unsupported family {family}")


def choose_file(page, path: Path) -> None:
    with page.expect_file_chooser() as chooser_info:
        page.locator("#kit-file").click()
    chooser_info.value.set_files(str(path.resolve()))


def run_journey(browser, entry: str, kit_path: Path, *, viewport: dict[str, int], touch: bool, local_origin: str | None) -> dict[str, Any]:
    kit = json.loads(kit_path.read_text(encoding="utf-8"))
    activities = kit["courses"][0]["activities"]
    assert len(activities) == 11, len(activities)
    context = browser.new_context(viewport=viewport, has_touch=touch)
    page = context.new_page()
    external: list[str] = []
    errors: list[str] = []

    def request_seen(request):
        url = request.url
        if not url.startswith(("http://", "https://")):
            return
        if local_origin is not None and url.startswith(local_origin):
            return
        external.append(url)

    page.on("request", request_seen)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(entry)
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
    choose_file(page, kit_path)
    page.locator("form.import-panel button[type='submit']").click()
    page.get_by_text(kit["courses"][0]["title"], exact=True).wait_for()
    page.get_by_role("button", name="Commencer").click()

    for index, activity in enumerate(activities):
        family = activity["type"]
        page.locator(f'[data-activity-presentation="{family}"]').wait_for()
        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
        assert_safe(page, family)
        answer(page, activity)

        if index in (0, 3):
            page.reload()
            page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
            if index < len(activities) - 1:
                next_family = activities[index + 1]["type"]
                page.locator(f'[data-activity-presentation="{next_family}"]').wait_for()
                assert_safe(page, next_family)
            continue
        if index < len(activities) - 1:
            page.locator('[data-served-next-action="true"]').click()

    page.locator('[data-served-next-action="true"]').click()
    page.get_by_text("Cours terminé", exact=True).wait_for()
    page.reload()
    page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
    page.get_by_text("Cours terminé", exact=True).wait_for()
    progress = page.evaluate("async () => (await window.__LEARNIT_NEXT_TEST__.listCourses())[0]?.progress")
    assert progress["isComplete"] is True, progress
    assert progress["completed"] == len(activities), progress
    assert external == [], external
    assert errors == [], errors
    context.close()
    return {"activities": len(activities), "external": len(external), "errors": len(errors)}


def browser_showcase() -> None:
    verify_identity()
    app = ROOT / APP_PATH
    kit = ROOT / KIT_PATH
    assert app.is_file()
    raw = app.read_bytes()
    assert len(raw) == EXPECTED_APP_BYTES and hashlib.sha256(raw).hexdigest() == EXPECTED_APP_SHA256
    from playwright.sync_api import sync_playwright
    with artifact_server(app.parent, app.name) as url, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        origin = url.rsplit("/", 1)[0]
        desktop = run_journey(browser, url, kit, viewport={"width":1365,"height":768}, touch=False, local_origin=origin)
        mobile = run_journey(browser, url, kit, viewport={"width":390,"height":844}, touch=True, local_origin=origin)
        browser.close()
    print(json.dumps({"desktop":desktop,"mobile":mobile}, sort_keys=True))
    print("STUDENT_V01_JOB08_SHOWCASE_REAL_JOURNEY=PASS")
    print("STUDENT_V01_JOB08_DESKTOP_MOBILE=PASS")
    print("STUDENT_V01_JOB08_RELOAD_RESUME_COMPLETION=PASS")
    print("STUDENT_V01_JOB08_SECRET_BOUNDARY=PASS")
    print("STUDENT_V01_JOB08_OFFLINE_NO_REMOTE=PASS")


def package_browser(package: Path) -> None:
    verify_identity()
    raw = package.read_bytes()
    assert len(raw) == EXPECTED_PACKAGE_BYTES
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_PACKAGE_SHA256
    with tempfile.TemporaryDirectory(prefix="job08-package-") as td:
        root = Path(td)
        with zipfile.ZipFile(package) as archive:
            for info in archive.infolist():
                p = Path(info.filename)
                assert not p.is_absolute() and ".." not in p.parts
                assert info.filename.startswith("student-v01-pilot/")
            archive.extractall(root)
        extracted = root / "student-v01-pilot"
        app = extracted / "learnit-next.html"
        kit = extracted / "course.learnit.json"
        start = extracted / "START_HERE.html"
        assert app.read_bytes() == (ROOT / APP_PATH).read_bytes()
        assert kit.read_bytes() == (ROOT / KIT_PATH).read_bytes()

        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
            context = browser.new_context(viewport={"width":1365,"height":768})
            page = context.new_page()
            external: list[str] = []
            page.on("request", lambda request: external.append(request.url)
                    if request.url.startswith(("http://","https://")) else None)
            page.goto(start.as_uri())
            page.get_by_text("Student V0.1 — démarrer", exact=True).wait_for()
            assert page.locator("#open-learnit").get_attribute("href") == "learnit-next.html"
            page.locator("#open-learnit").click()
            page.wait_for_function("() => Boolean(window.__LEARNIT_NEXT_TEST__)")
            assert external == [], external
            context.close()

            direct = run_journey(
                browser, app.as_uri(), kit,
                viewport={"width":1365,"height":768}, touch=False, local_origin=None,
            )
            browser.close()
    print(json.dumps({"directFile":direct}, sort_keys=True))
    print("START_MODE=DIRECT_FILE")
    print("STUDENT_V01_JOB08_PACKAGE_BROWSER_SMOKE=PASS")
    print("STUDENT_V01_JOB08_PACKAGE_OFFLINE_NO_REMOTE=PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("identity","showcase-browser","package-browser"), default="identity")
    parser.add_argument("--package", type=Path)
    args = parser.parse_args()
    if args.mode == "identity":
        verify_identity()
    elif args.mode == "showcase-browser":
        browser_showcase()
    else:
        if args.package is None:
            raise SystemExit("--package is required for package-browser")
        package_browser(args.package)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
