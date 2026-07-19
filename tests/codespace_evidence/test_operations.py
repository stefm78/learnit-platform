"""Independent contradictory QA for operation allowlisting and GitHub pagination."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest import mock
import unittest

from tools.codespace_evidence import OPERATIONS
from tools.codespace_evidence.github import GhClient, GitHubError, _flatten_slurped_pages
from tools.codespace_evidence.operations import HANDLERS, PROFILES, _checks, _reviews
from tools.codespace_evidence.run import main


SHA = "f" * 40
REPOSITORY = "stefm78/learnit-platform"


class FakeRunner:
    def __init__(self) -> None:
        self.counter = 0

    def run(self, argv: list[str], **_: object) -> SimpleNamespace:
        self.counter += 1
        text = f"log page for {' '.join(argv)}"
        encoded = text.encode("utf-8")
        return SimpleNamespace(
            id=f"cmd-{self.counter:03d}",
            return_code=0,
            timed_out=False,
            stdout=text,
            stderr="",
            stdout_bytes=len(encoded),
            stdout_sha256=hashlib.sha256(encoded).hexdigest(),
        )


class PaginatedClient(GhClient):
    def __init__(self, *, with_runs: bool = True) -> None:
        super().__init__(FakeRunner(), Path("."))
        self.with_runs = with_runs
        self.calls: list[tuple[str, bool]] = []

    def api_json(self, endpoint: str, *, paginate: bool = False, timeout: int = 300) -> object:
        del timeout
        self.calls.append((endpoint, paginate))
        if endpoint == f"repos/{REPOSITORY}/pulls/7":
            return {
                "state": "open",
                "draft": True,
                "merged": False,
                "mergeable": True,
                "mergeable_state": "clean",
                "title": "QA target",
                "html_url": "https://example.invalid/pr/7",
                "base": {"ref": "main", "sha": "a" * 40},
                "head": {"ref": "topic", "sha": SHA},
            }
        if "/pulls/7/files?" in endpoint:
            return [
                [{"filename": "a.txt", "status": "added", "additions": 1, "deletions": 0, "changes": 1}],
                [{"filename": "b.txt", "status": "modified", "additions": 1, "deletions": 1, "changes": 2}],
            ]
        if "/pulls/7/reviews?" in endpoint:
            return [
                [{"id": 1, "state": "APPROVED", "commit_id": SHA, "user": {"login": "one"}}],
                [{"id": 2, "state": "CHANGES_REQUESTED", "commit_id": "e" * 40, "user": {"login": "two"}}],
            ]
        if f"/commits/{SHA}/status?" in endpoint:
            return [
                {"state": "success", "statuses": [{"context": "context-one", "state": "success", "sha": SHA}]},
                {"state": "success", "statuses": [{"context": "context-two", "state": "pending", "sha": SHA}]},
            ]
        if f"/commits/{SHA}/check-runs?" in endpoint:
            return [
                {"check_runs": [{"name": "check-one", "status": "completed", "conclusion": "success", "head_sha": SHA}]},
                {"check_runs": [{"name": "check-two", "status": "completed", "conclusion": "failure", "head_sha": SHA}]},
            ]
        if "/actions/runs?" in endpoint:
            if not self.with_runs:
                return [{"workflow_runs": []}]
            return [
                {"workflow_runs": [{"id": 11, "name": "workflow-one"}]},
                {"workflow_runs": [{"id": 22, "name": "workflow-two"}]},
            ]
        if "/actions/runs/11/jobs?" in endpoint:
            return [{"jobs": [{"id": 111, "name": "job-one", "steps": [{"name": "step-one"}]}]}]
        if "/actions/runs/22/jobs?" in endpoint:
            return [{"jobs": [{"id": 222, "name": "job-two", "steps": [{"name": "step-two"}]}]}]
        if "/actions/runs/11/artifacts?" in endpoint:
            return [{"artifacts": [{"id": 1111, "name": "artifact-one"}]}]
        if "/actions/runs/22/artifacts?" in endpoint:
            return [{"artifacts": [{"id": 2222, "name": "artifact-two"}]}]
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    def api_text(self, endpoint: str, *, accept: str | None = None, timeout: int = 300) -> str:
        del accept, timeout
        self.calls.append((endpoint, False))
        return (
            "diff --git a/a.txt b/a.txt\nnew file mode 100644\n"
            "diff --git a/b.txt b/b.txt\nindex 1..2 100644\n"
        )


def runtime_request() -> SimpleNamespace:
    return SimpleNamespace(
        job_id="CEB-QA-ENV-1",
        digest_sha256="9" * 64,
        operation="pr-snapshot",
        repository=REPOSITORY,
        origin=SimpleNamespace(type="issue", number=102, request_comment_id=123),
        target_type="pull_request",
        target_number=103,
        target_sha=SHA,
        allow_new_attempt=False,
    )


class OperationTests(unittest.TestCase):
    def test_exact_four_operation_allowlist_is_preserved(self) -> None:
        expected = {
            "pr-snapshot",
            "pr-governor-evidence",
            "run-repository-validation",
            "run-test-profile",
        }
        self.assertEqual(set(OPERATIONS), expected)
        self.assertEqual(set(HANDLERS), expected)

    def test_test_profiles_are_fixed_and_request_independent(self) -> None:
        self.assertEqual(set(PROFILES), {"repository", "learnit-next-strict", "player-fast", "player-full"})
        for argv in PROFILES.values():
            self.assertIsInstance(argv, list)
            self.assertNotIn("shell", " ".join(argv).lower())

    def test_page_flattening_is_exhaustive(self) -> None:
        self.assertEqual(_flatten_slurped_pages([[1, 2], [3], [4, 5]]), [1, 2, 3, 4, 5])
        self.assertEqual(
            _flatten_slurped_pages([{"items": [1]}, {"items": [2, 3]}], list_key="items"),
            [1, 2, 3],
        )

    def test_reviews_are_bound_to_each_reviewed_sha(self) -> None:
        reviews = _reviews(
            [
                {"id": 1, "state": "APPROVED", "commit_id": SHA, "user": {"login": "qa"}},
                {"id": 2, "state": "APPROVED", "commit_id": "e" * 40, "user": {"login": "old"}},
            ],
            SHA,
        )
        self.assertTrue(reviews[0]["matches_target_sha"])
        self.assertFalse(reviews[1]["matches_target_sha"])
        self.assertEqual(reviews[1]["reviewed_sha"], "e" * 40)

    def test_status_contexts_and_check_runs_are_both_collected(self) -> None:
        inventory = _checks(
            {
                "checks": {
                    "status_contexts": [{"context": "legacy", "state": "success", "sha": SHA}],
                    "check_runs": [{"name": "modern", "status": "completed", "conclusion": "success", "head_sha": SHA}],
                }
            }
        )
        self.assertEqual(inventory["legacy"]["source"], "status")
        self.assertEqual(inventory["modern"]["source"], "check_run")

    def test_changed_files_reviews_runs_jobs_steps_logs_and_artifacts_span_pages(self) -> None:
        client = PaginatedClient()
        snapshot, artifacts, missing = client.collect_pr_snapshot(
            repository=REPOSITORY,
            pr_number=7,
            target_sha=SHA,
            include_logs=True,
            include_artifacts=True,
        )
        self.assertEqual([item["filename"] for item in snapshot["changed_files"]], ["a.txt", "b.txt"])
        self.assertEqual(len(snapshot["reviews"]), 2)
        checks = snapshot["checks"]
        self.assertEqual(len(checks["status_contexts"]), 2)
        self.assertEqual(len(checks["check_runs"]), 2)
        self.assertEqual(len(checks["workflow_runs"]), 2)
        self.assertEqual(len(checks["workflow_jobs"]), 2)
        self.assertEqual([job["steps"][0]["name"] for job in checks["workflow_jobs"]], ["step-one", "step-two"])
        self.assertEqual(len(checks["workflow_artifacts"]), 2)
        self.assertEqual(len(checks["log_summaries"]), 2)
        self.assertIn("diff --git a/a.txt b/a.txt", artifacts["diff.patch"])
        self.assertIn("diff --git a/b.txt b/b.txt", artifacts["diff.patch"])
        self.assertIn("ARTIFACT_CONTENT_NOT_DOWNLOADED_SECURITY_BOUNDARY", missing)
        paginated_calls = [endpoint for endpoint, paginated in client.calls if paginated]
        self.assertTrue(any("/files?" in endpoint for endpoint in paginated_calls))
        self.assertTrue(any("/reviews?" in endpoint for endpoint in paginated_calls))
        self.assertTrue(any("/jobs?" in endpoint for endpoint in paginated_calls))
        self.assertTrue(any("/artifacts?" in endpoint for endpoint in paginated_calls))

    def test_unavailable_runs_are_explicit_missing_proof(self) -> None:
        client = PaginatedClient(with_runs=False)
        snapshot, _, missing = client.collect_pr_snapshot(
            repository=REPOSITORY,
            pr_number=7,
            target_sha=SHA,
            include_logs=True,
            include_artifacts=True,
        )
        self.assertEqual(snapshot["checks"]["workflow_runs"], [])
        self.assertIn("NO_WORKFLOW_RUNS_FOR_LOG_COLLECTION", missing)
        self.assertIn("NO_WORKFLOW_RUNS_FOR_ARTIFACT_COLLECTION", missing)

    def _assert_preflight_failure_is_durably_classified(self, reason: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            descriptor = root / "request.json"
            descriptor.write_text("{}", encoding="utf-8")
            output = root / "out"
            client = mock.MagicMock()
            client.preflight.side_effect = GitHubError(reason)
            stderr = io.StringIO()
            with (
                mock.patch("tools.codespace_evidence.run.discover_repository_root", return_value=root),
                mock.patch(
                    "tools.codespace_evidence.run.load_and_verify_request",
                    return_value=(SimpleNamespace(), runtime_request(), {}),
                ),
                mock.patch("tools.codespace_evidence.run.GhClient", return_value=client),
                contextlib.redirect_stderr(stderr),
            ):
                result = main(["--request", str(descriptor), "--output-root", str(output)])
            self.assertNotEqual(result, 0)
            failure = output / "CEB-QA-ENV-1" / "attempt-001" / "publication" / "failure.json"
            self.assertTrue(
                failure.is_file(),
                "environment failures must allocate an immutable attempt and leave durable classified evidence",
            )
            payload = json.loads(failure.read_text(encoding="utf-8"))
            self.assertEqual(payload["classification"], "FAIL_ENVIRONMENT")

    def test_private_repository_inaccessible_is_durably_classified(self) -> None:
        self._assert_preflight_failure_is_durably_classified("private repository inaccessible")

    def test_gh_absent_is_durably_classified(self) -> None:
        self._assert_preflight_failure_is_durably_classified("gh executable absent")

    def test_expired_or_invalid_token_is_durably_classified(self) -> None:
        self._assert_preflight_failure_is_durably_classified("gh authentication is unavailable or expired")

    def test_network_interruption_is_durably_classified(self) -> None:
        self._assert_preflight_failure_is_durably_classified("network interrupted")


if __name__ == "__main__":
    unittest.main()
