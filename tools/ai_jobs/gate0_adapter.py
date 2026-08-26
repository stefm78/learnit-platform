"""Single-invocation adapter to the already accepted Gate 0 runner."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
import tempfile

from tools.codespace_evidence.execute import CommandRunner

from .contracts import ContractError, QueueJob, validate_gate0_operation


@dataclass(frozen=True)
class Gate0Invocation:
    return_code: int
    timed_out: bool
    output_root: str


def invoke_once(
    *,
    runner: CommandRunner,
    repository_root: Path,
    job: QueueJob,
    timeout_seconds: int = 3600,
) -> Gate0Invocation:
    validate_gate0_operation(job.operation)
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
        raise ContractError("timeout_seconds must be an exact integer")
    if not 30 <= timeout_seconds <= 3600:
        raise ContractError("timeout_seconds outside fixed Gate 0 range")

    with tempfile.TemporaryDirectory(prefix="learnit-gate1-") as tmp:
        root = Path(tmp)
        descriptor = root / "launch.json"
        output = root / "gate0-output"
        descriptor.write_text(
            json.dumps(
                {
                    "repository": job.repository,
                    "origin_type": job.origin_type,
                    "origin_number": job.origin_number,
                    "request_comment_id": job.request_comment_id,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
        record = runner.run(
            [
                sys.executable,
                str(repository_root / "tools/codespace_evidence/run.py"),
                "--request", str(descriptor),
                "--output-root", str(output),
            ],
            cwd=repository_root,
            timeout_seconds=timeout_seconds,
        )
        return Gate0Invocation(
            return_code=record.return_code,
            timed_out=record.timed_out,
            output_root=str(output),
        )
