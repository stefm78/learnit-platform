"""GitHub evidence collection and same-origin comment publication via ``gh``."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable

from . import OUTCOME_MARKER, STATEMENT
from .execute import CommandRunner, ExecutionError, redact_value

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HEADER_RE = re.compile(r"(?m)^([a-z_]+): ([^\n]+)$")


class GitHubError(RuntimeError):
    """Raised when GitHub evidence or publication cannot be completed safely."""


def _parse_json(text: str, label: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GitHubError(f"{label} did not return valid JSON: {exc}") from exc


def _flatten_slurped_pages(value: Any, *, list_key: str | None = None) -> list[Any]:
    """Flatten ``gh api --paginate --slurp`` output without hiding page shape."""

    pages = value if isinstance(value, list) else [value]
    result: list[Any] = []
    for page in pages:
        if list_key is None:
            if not isinstance(page, list):
                raise GitHubError("paginated endpoint returned a non-list page")
            result.extend(page)
        else:
            if not isinstance(page, dict) or not isinstance(page.get(list_key), list):
                raise GitHubError(f"paginated endpoint omitted list key: {list_key}")
            result.extend(page[list_key])
    return result


def _publication_headers(body: str) -> dict[str, str] | None:
    if body.count(OUTCOME_MARKER) != 1 or not body.startswith(OUTCOME_MARKER + "\n"):
        return None
    pairs = HEADER_RE.findall(body)
    headers: dict[str, str] = {}
    for key, value in pairs:
        if key in headers:
            return None
        headers[key] = value
    return headers


def _publication_payload(body: str) -> dict[str, Any] | None:
    blocks = re.findall(r"```json\n(.*?)\n```", body, flags=re.DOTALL)
    if len(blocks) != 1:
        return None
    try:
        payload = json.loads(blocks[0])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _matches_identity(
    body: str,
    *,
    repository: str,
    origin_type: str,
    origin_number: int,
    job_id: str,
    request_digest: str,
    target_sha: str,
) -> bool:
    return (
        body.startswith(OUTCOME_MARKER + "\n")
        and f"job_id: {job_id}\n" in body
        and f"request_sha256: {request_digest}\n" in body
        and f"repository: {repository}\n" in body
        and f"origin: {origin_type}#{origin_number}\n" in body
        and f"target_sha: {target_sha}\n" in body
        and (
            "completion_state: FINAL_SEALED\n" in body
            or "completion_state: FINAL_DIAGNOSTIC_ONLY\n" in body
        )
    )


def _cryptographically_complete_publication(
    body: str,
    *,
    repository: str,
    origin_type: str,
    origin_number: int,
    job_id: str,
    request_digest: str,
    target_sha: str,
) -> bool:
    """Validate the durable capsule before a restart may trust it.

    Marker fragments are only candidates. The exact header, fenced JSON payload,
    origin identity and both bundle digests must agree. The caller subsequently
    re-reads the exact comment ID and requires byte-for-byte equality.
    """

    headers = _publication_headers(body)
    payload = _publication_payload(body)
    if headers is None or payload is None or STATEMENT not in body:
        return False
    expected_headers = {
        "job_id": job_id,
        "request_sha256": request_digest,
        "repository": repository,
        "origin": f"{origin_type}#{origin_number}",
        "target_sha": target_sha,
    }
    if any(headers.get(key) != value for key, value in expected_headers.items()):
        return False
    manifest = headers.get("manifest_sha256", "")
    bundle = headers.get("bundle_sha256", "")
    if not SHA256_RE.fullmatch(manifest) or not SHA256_RE.fullmatch(bundle):
        return False
    completion = headers.get("completion_state")
    if completion == "FINAL_SEALED":
        facts = payload.get("facts")
        sealed = payload.get("sealed_bundle")
        if not isinstance(facts, dict) or not isinstance(sealed, dict):
            return False
        origin = facts.get("origin")
        target = facts.get("target")
        if not isinstance(origin, dict) or not isinstance(target, dict):
            return False
        if (
            facts.get("job_id") != job_id
            or facts.get("request_sha256") != request_digest
            or facts.get("repository") != repository
            or origin.get("type") != origin_type
            or origin.get("number") != origin_number
            or target.get("requested_sha") != target_sha
            or sealed.get("manifest_sha256") != manifest
            or sealed.get("bundle_sha256") != bundle
        ):
            return False
        artifact_digests = sealed.get("artifact_sha256")
        if not isinstance(artifact_digests, dict):
            return False
        if any(not isinstance(value, str) or not SHA256_RE.fullmatch(value) for value in artifact_digests.values()):
            return False
        return True
    if completion == "FINAL_DIAGNOSTIC_ONLY":
        origin = payload.get("origin")
        if origin is not None and (
            not isinstance(origin, dict)
            or origin.get("type") != origin_type
            or origin.get("number") != origin_number
        ):
            return False
        return (
            payload.get("job_id") == job_id
            and payload.get("request_sha256") == request_digest
            and payload.get("target_sha") == target_sha
            and payload.get("manifest_sha256") == manifest
            and payload.get("bundle_sha256") == bundle
            and payload.get("classification") == "INCONCLUSIVE"
        )
    return False


@dataclass(frozen=True)
class PublicationResult:
    comment_id: int
    html_url: str
    body: str
    created_at: str | None


class GhClient:
    def __init__(self, runner: CommandRunner, repository_root: Path) -> None:
        self.runner = runner
        self.repository_root = repository_root

    def _run(self, argv: list[str], *, timeout: int = 300) -> str:
        try:
            record = self.runner.run(argv, cwd=self.repository_root, timeout_seconds=timeout)
        except FileNotFoundError as exc:
            raise GitHubError("gh executable absent") from exc
        except ExecutionError as exc:
            raise GitHubError(str(exc)) from exc
        if record.return_code != 0 or record.timed_out:
            raise GitHubError(f"GitHub command failed: {' '.join(record.argv)}")
        return record.stdout

    def api_json(self, endpoint: str, *, paginate: bool = False, timeout: int = 300) -> Any:
        argv = ["gh", "api", "-H", "X-GitHub-Api-Version: 2022-11-28"]
        if paginate:
            argv.extend(["--paginate", "--slurp"])
        argv.append(endpoint)
        return redact_value(_parse_json(self._run(argv, timeout=timeout), endpoint))

    def api_text(self, endpoint: str, *, accept: str | None = None, timeout: int = 300) -> str:
        argv = ["gh", "api", "-H", "X-GitHub-Api-Version: 2022-11-28"]
        if accept:
            argv.extend(["-H", f"Accept: {accept}"])
        argv.append(endpoint)
        return self._run(argv, timeout=timeout)

    def preflight(self, repository: str) -> dict[str, Any]:
        version = self._run(["gh", "--version"], timeout=30).strip().splitlines()
        auth_record = self.runner.run(
            ["gh", "auth", "status", "--active"],
            cwd=self.repository_root,
            timeout_seconds=30,
        )
        if auth_record.return_code != 0:
            raise GitHubError("gh authentication is unavailable or expired")
        user = self.api_json("user", timeout=30)
        repo_text = self._run(
            ["gh", "repo", "view", repository, "--json", "nameWithOwner,isPrivate,url,defaultBranchRef"],
            timeout=60,
        )
        repo = redact_value(_parse_json(repo_text, "gh repo view"))
        if repo.get("nameWithOwner") != repository:
            raise GitHubError("authenticated GitHub context resolved a different repository")
        return {
            "gh_version": version[0] if version else "",
            "authenticated_host": "github.com",
            "authenticated_login": user.get("login") if isinstance(user, dict) else None,
            "repository": repo,
            "credential_capabilities": "not inferred from token scope",
            "bridge_exposed_mutations": ["same-origin issue conversation comment creation"],
        }

    def fetch_request_comment(self, repository: str, comment_id: int) -> dict[str, Any]:
        value = self.api_json(f"repos/{repository}/issues/comments/{comment_id}", timeout=60)
        if not isinstance(value, dict):
            raise GitHubError("request comment endpoint returned an invalid object")
        return value

    def resolve_target(
        self,
        *,
        repository: str,
        target_type: str,
        target_number: int | None,
        target_sha: str,
    ) -> dict[str, Any]:
        if target_type == "pull_request":
            if target_number is None:
                raise GitHubError("pull request target requires target_number")
            pr = self.api_json(f"repos/{repository}/pulls/{target_number}", timeout=60)
            if not isinstance(pr, dict) or not isinstance(pr.get("head"), dict):
                raise GitHubError("pull request target could not be resolved")
            return {
                "type": "pull_request",
                "number": target_number,
                "sha": pr["head"].get("sha"),
                "state": pr.get("state"),
                "draft": pr.get("draft"),
                "merged": pr.get("merged"),
                "base_sha": pr.get("base", {}).get("sha") if isinstance(pr.get("base"), dict) else None,
                "head_ref": pr.get("head", {}).get("ref") if isinstance(pr.get("head"), dict) else None,
            }
        commit = self.api_json(f"repos/{repository}/commits/{target_sha}", timeout=60)
        if not isinstance(commit, dict) or not isinstance(commit.get("sha"), str):
            raise GitHubError("commit target could not be resolved")
        return {"type": "commit", "number": None, "sha": commit["sha"]}

    def collect_pr_snapshot(
        self,
        *,
        repository: str,
        pr_number: int,
        target_sha: str,
        include_logs: bool,
        include_artifacts: bool,
    ) -> tuple[dict[str, Any], dict[str, str], list[str]]:
        missing_proof: list[str] = []
        artifacts: dict[str, str] = {}
        pr = self.api_json(f"repos/{repository}/pulls/{pr_number}", timeout=60)
        if not isinstance(pr, dict):
            raise GitHubError("pull request metadata is invalid")
        changed_files = _flatten_slurped_pages(
            self.api_json(
                f"repos/{repository}/pulls/{pr_number}/files?per_page=100",
                paginate=True,
                timeout=300,
            )
        )
        diff = self.api_text(
            f"repos/{repository}/pulls/{pr_number}",
            accept="application/vnd.github.v3.diff",
            timeout=300,
        )
        artifacts["diff.patch"] = diff
        reviews = _flatten_slurped_pages(
            self.api_json(
                f"repos/{repository}/pulls/{pr_number}/reviews?per_page=100",
                paginate=True,
                timeout=300,
            )
        )
        artifacts["reviews.json"] = json.dumps(reviews, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        status_pages = self.api_json(
            f"repos/{repository}/commits/{target_sha}/status?per_page=100",
            paginate=True,
            timeout=300,
        )
        status_contexts: list[Any] = []
        combined_state: str | None = None
        for page in status_pages if isinstance(status_pages, list) else [status_pages]:
            if not isinstance(page, dict) or not isinstance(page.get("statuses"), list):
                raise GitHubError("combined status pagination returned an invalid page")
            combined_state = combined_state or page.get("state")
            status_contexts.extend(page["statuses"])
        check_runs = _flatten_slurped_pages(
            self.api_json(
                f"repos/{repository}/commits/{target_sha}/check-runs?per_page=100",
                paginate=True,
                timeout=300,
            ),
            list_key="check_runs",
        )
        workflow_runs = _flatten_slurped_pages(
            self.api_json(
                f"repos/{repository}/actions/runs?head_sha={target_sha}&per_page=100",
                paginate=True,
                timeout=300,
            ),
            list_key="workflow_runs",
        )
        workflow_jobs: list[dict[str, Any]] = []
        workflow_artifacts: list[dict[str, Any]] = []
        log_summaries: list[dict[str, Any]] = []
        for run in workflow_runs:
            if not isinstance(run, dict) or not isinstance(run.get("id"), int):
                missing_proof.append("WORKFLOW_RUN_WITHOUT_ID")
                continue
            run_id = run["id"]
            jobs = _flatten_slurped_pages(
                self.api_json(
                    f"repos/{repository}/actions/runs/{run_id}/jobs?per_page=100",
                    paginate=True,
                    timeout=300,
                ),
                list_key="jobs",
            )
            workflow_jobs.extend(jobs)
            if include_logs:
                log_record = self.runner.run(
                    ["gh", "run", "view", str(run_id), "--repo", repository, "--log"],
                    cwd=self.repository_root,
                    timeout_seconds=600,
                )
                if log_record.return_code == 0 and not log_record.timed_out:
                    artifacts[f"workflow-run-{run_id}.log"] = log_record.stdout
                    log_summaries.append(
                        {
                            "run_id": run_id,
                            "bytes": log_record.stdout_bytes,
                            "sha256": log_record.stdout_sha256,
                            "command_id": log_record.id,
                        }
                    )
                else:
                    missing_proof.append(f"WORKFLOW_LOG_UNAVAILABLE:{run_id}")
            if include_artifacts:
                workflow_artifacts.extend(
                    _flatten_slurped_pages(
                        self.api_json(
                            f"repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100",
                            paginate=True,
                            timeout=300,
                        ),
                        list_key="artifacts",
                    )
                )
        if include_logs and not workflow_runs:
            missing_proof.append("NO_WORKFLOW_RUNS_FOR_LOG_COLLECTION")
        if include_artifacts and not workflow_runs:
            missing_proof.append("NO_WORKFLOW_RUNS_FOR_ARTIFACT_COLLECTION")
        if include_artifacts:
            missing_proof.append("ARTIFACT_CONTENT_NOT_DOWNLOADED_SECURITY_BOUNDARY")
        checks = {
            "combined_state": combined_state,
            "status_contexts": status_contexts,
            "check_runs": check_runs,
            "workflow_runs": workflow_runs,
            "workflow_jobs": workflow_jobs,
            "workflow_artifacts": workflow_artifacts,
            "log_summaries": log_summaries,
        }
        artifacts["checks.json"] = json.dumps(checks, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        file_inventory = [
            {
                "filename": item.get("filename"),
                "status": item.get("status"),
                "additions": item.get("additions"),
                "deletions": item.get("deletions"),
                "changes": item.get("changes"),
                "blob_url": item.get("blob_url"),
                "raw_url": item.get("raw_url"),
            }
            for item in changed_files
            if isinstance(item, dict)
        ]
        metadata = {
            "number": pr_number,
            "state": pr.get("state"),
            "draft": pr.get("draft"),
            "merged": pr.get("merged"),
            "mergeable": pr.get("mergeable"),
            "mergeable_state": pr.get("mergeable_state"),
            "title": pr.get("title"),
            "html_url": pr.get("html_url"),
            "base": {
                "ref": pr.get("base", {}).get("ref") if isinstance(pr.get("base"), dict) else None,
                "sha": pr.get("base", {}).get("sha") if isinstance(pr.get("base"), dict) else None,
            },
            "head": {
                "ref": pr.get("head", {}).get("ref") if isinstance(pr.get("head"), dict) else None,
                "sha": pr.get("head", {}).get("sha") if isinstance(pr.get("head"), dict) else None,
            },
            "changed_files_count": len(file_inventory),
            "changed_files": file_inventory,
            "diff": {
                "bytes": len(diff.encode("utf-8")),
                "sha256": __import__("hashlib").sha256(diff.encode("utf-8")).hexdigest(),
                "artifact": "diff.patch",
            },
            "reviews": reviews,
            "checks": checks,
        }
        return metadata, artifacts, sorted(set(missing_proof))

    def list_origin_comments(self, repository: str, origin_number: int) -> list[dict[str, Any]]:
        pages = self.api_json(
            f"repos/{repository}/issues/{origin_number}/comments?per_page=100",
            paginate=True,
            timeout=300,
        )
        return [item for item in _flatten_slurped_pages(pages) if isinstance(item, dict)]

    def find_existing_final_publication(
        self,
        *,
        repository: str,
        origin_type: str,
        origin_number: int,
        job_id: str,
        request_digest: str,
        target_sha: str,
    ) -> dict[str, Any] | None:
        candidates: list[dict[str, Any]] = []
        for comment in self.list_origin_comments(repository, origin_number):
            body = comment.get("body")
            if isinstance(body, str) and _matches_identity(
                body,
                repository=repository,
                origin_type=origin_type,
                origin_number=origin_number,
                job_id=job_id,
                request_digest=request_digest,
                target_sha=target_sha,
            ):
                candidates.append(comment)
        if len(candidates) > 1:
            raise GitHubError("multiple verified final publications exist for the same job and request digest")
        if not candidates:
            return None
        candidate = candidates[0]
        body = candidate.get("body")
        comment_id = candidate.get("id")
        if not isinstance(body, str) or not isinstance(comment_id, int):
            return None
        if not _cryptographically_complete_publication(
            body,
            repository=repository,
            origin_type=origin_type,
            origin_number=origin_number,
            job_id=job_id,
            request_digest=request_digest,
            target_sha=target_sha,
        ):
            return None
        reread = self.read_comment(repository=repository, comment_id=comment_id)
        expected_issue_url = f"https://api.github.com/repos/{repository}/issues/{origin_number}"
        if reread.get("id") != comment_id or reread.get("issue_url") != expected_issue_url:
            raise GitHubError("existing publication is not attached to the exact verified origin")
        if reread.get("body") != body:
            raise GitHubError("existing publication changed during exact read-back")
        if not _cryptographically_complete_publication(
            body,
            repository=repository,
            origin_type=origin_type,
            origin_number=origin_number,
            job_id=job_id,
            request_digest=request_digest,
            target_sha=target_sha,
        ):
            raise GitHubError("existing publication failed digest and payload verification")
        return reread

    def publish_comment(self, *, repository: str, origin_number: int, body: str) -> PublicationResult:
        payload = {"body": body}
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            payload_path = Path(handle.name)
        try:
            output = self._run(
                [
                    "gh",
                    "api",
                    "-H",
                    "X-GitHub-Api-Version: 2022-11-28",
                    "--method",
                    "POST",
                    f"repos/{repository}/issues/{origin_number}/comments",
                    "--input",
                    str(payload_path),
                ],
                timeout=300,
            )
        finally:
            payload_path.unlink(missing_ok=True)
        value = redact_value(_parse_json(output, "comment publication"))
        if not isinstance(value, dict) or not isinstance(value.get("id"), int):
            raise GitHubError("comment publication did not return an exact comment identity")
        return PublicationResult(
            comment_id=value["id"],
            html_url=str(value.get("html_url", "")),
            body=str(value.get("body", "")),
            created_at=value.get("created_at") if isinstance(value.get("created_at"), str) else None,
        )

    def read_comment(self, *, repository: str, comment_id: int) -> dict[str, Any]:
        value = self.api_json(f"repos/{repository}/issues/comments/{comment_id}", timeout=60)
        if not isinstance(value, dict):
            raise GitHubError("published comment read-back returned an invalid object")
        return value

    def verify_publication(
        self,
        *,
        repository: str,
        origin_number: int,
        result: PublicationResult,
        expected_body: str,
        required_fragments: Iterable[str],
    ) -> dict[str, Any]:
        reread = self.read_comment(repository=repository, comment_id=result.comment_id)
        expected_issue_url = f"https://api.github.com/repos/{repository}/issues/{origin_number}"
        if reread.get("id") != result.comment_id:
            raise GitHubError("published comment identity changed during read-back")
        if reread.get("issue_url") != expected_issue_url:
            raise GitHubError("published comment is not attached to the verified origin")
        if reread.get("body") != expected_body:
            raise GitHubError("published comment body differs from the exact rendered body")
        for fragment in required_fragments:
            if fragment not in expected_body:
                raise GitHubError(f"published comment omitted required fragment: {fragment}")
        return {
            "state": "VERIFIED",
            "comment_id": result.comment_id,
            "html_url": reread.get("html_url"),
            "created_at": reread.get("created_at"),
            "updated_at": reread.get("updated_at"),
            "body_bytes": len(expected_body.encode("utf-8")),
        }
