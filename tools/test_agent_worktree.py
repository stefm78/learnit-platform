#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

MODULE_PATH = Path(__file__).with_name("agent_worktree.py")
spec = importlib.util.spec_from_file_location("agent_worktree", MODULE_PATH)
assert spec and spec.loader
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)

BASE = "a" * 40
HEAD = "b" * 40
BRANCH = "agent/PROG-WP-001-smoke"


class AgentWorktreeValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.job_dir = self.root / ".agent-jobs" / "LLV2-TEST-001"
        self.job_dir.mkdir(parents=True)
        (self.job_dir / "READY").write_text("", encoding="utf-8")
        self.old_root = agent.ROOT
        self.old_runtime = agent.RUNTIME_DIR
        self.old_jobs = agent.JOB_ROOT
        agent.ROOT = self.root
        agent.RUNTIME_DIR = self.root / ".agent-runtime"
        agent.JOB_ROOT = self.root / ".agent-jobs"
        self.env = mock.patch.dict(os.environ, {"AGENT_BRANCH": BRANCH}, clear=False)
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        agent.ROOT = self.old_root
        agent.RUNTIME_DIR = self.old_runtime
        agent.JOB_ROOT = self.old_jobs
        self.temp.cleanup()

    def common(self, mode: str) -> dict:
        return {
            "schemaVersion": 1,
            "id": "LLV2-TEST-001",
            "baseCommit": BASE,
            "branch": BRANCH,
            "mode": mode,
        }

    def git_ok(self, *args: str, **_: object) -> str:
        if args[:2] == ("merge-base", BASE):
            return BASE
        if args[:2] == ("diff", "--name-only"):
            return ".agent-jobs/LLV2-TEST-001/job.json\n.agent-jobs/LLV2-TEST-001/READY"
        if args[:2] == ("rev-parse", "HEAD"):
            return HEAD
        return ""

    def test_analyze_accepts_fixed_profile_without_patch(self) -> None:
        job = self.common("analyze") | {"analysisProfile": "learnit-next-snapshot"}
        with mock.patch.object(agent, "git", side_effect=self.git_ok):
            plan = agent.validate_job(self.job_dir, job)
        self.assertEqual(plan["mode"], "analyze")
        self.assertEqual(plan["profile"], "learnit-next-snapshot")
        self.assertNotIn("patchFile", plan)

    def test_analyze_rejects_unknown_profile(self) -> None:
        job = self.common("analyze") | {"analysisProfile": "shell-anything"}
        with mock.patch.object(agent, "git", side_effect=self.git_ok):
            with self.assertRaisesRegex(agent.AgentError, "unsupported analysisProfile"):
                agent.validate_job(self.job_dir, job)

    def test_analyze_rejects_arbitrary_command_field(self) -> None:
        job = self.common("analyze") | {
            "analysisProfile": "learnit-next-snapshot",
            "command": "rm -rf /",
        }
        with mock.patch.object(agent, "git", side_effect=self.git_ok):
            with self.assertRaisesRegex(agent.AgentError, "unsupported fields: command"):
                agent.validate_job(self.job_dir, job)

    def test_invalid_sha_fails_before_git_execution(self) -> None:
        job = self.common("analyze") | {
            "baseCommit": "main",
            "analysisProfile": "learnit-next-snapshot",
        }
        with mock.patch.object(agent, "git") as git_call:
            with self.assertRaisesRegex(agent.AgentError, "full lowercase SHA"):
                agent.validate_job(self.job_dir, job)
        git_call.assert_not_called()

    def implementation_job(self) -> dict:
        patch = self.job_dir / "change.patch"
        patch.write_text("diff --git a/x b/x\n", encoding="utf-8")
        return self.common("implement") | {
            "patchFile": ".agent-jobs/LLV2-TEST-001/change.patch",
            "allowedPaths": ["apps/learnit-next/src/**"],
            "forbiddenPaths": [],
            "testProfile": "learnit-next-fast",
            "commitMessage": "LLV2: bounded change",
        }

    def apply_run(self, args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        output = ""
        if "--numstat" in args:
            output = "1\t0\tapps/learnit-next/src/core/session.js\n"
        return subprocess.CompletedProcess(args, 0, stdout=output, stderr="")

    def test_implement_accepts_learnit_next_profile(self) -> None:
        job = self.implementation_job()
        with (
            mock.patch.object(agent, "git", side_effect=self.git_ok),
            mock.patch.object(agent, "run", side_effect=self.apply_run),
        ):
            plan = agent.validate_job(self.job_dir, job)
        self.assertEqual(plan["mode"], "implement")
        self.assertEqual(plan["profile"], "learnit-next-fast")
        self.assertEqual(plan["patchPaths"], ["apps/learnit-next/src/core/session.js"])

    def test_implement_rejects_snapshot_profile(self) -> None:
        job = self.implementation_job()
        job["testProfile"] = "learnit-next-snapshot"
        with mock.patch.object(agent, "git", side_effect=self.git_ok):
            with self.assertRaisesRegex(agent.AgentError, "analysis-only"):
                agent.validate_job(self.job_dir, job)

    def test_implement_rejects_forbidden_path(self) -> None:
        job = self.implementation_job()
        job["forbiddenPaths"] = ["apps/learnit-next/src/**"]
        with (
            mock.patch.object(agent, "git", side_effect=self.git_ok),
            mock.patch.object(agent, "run", side_effect=self.apply_run),
        ):
            with self.assertRaisesRegex(agent.AgentError, "forbidden"):
                agent.validate_job(self.job_dir, job)

    def test_analyze_plan_cannot_apply(self) -> None:
        plan = self.root / "plan.json"
        plan.write_text(
            json.dumps(
                {
                    "schemaVersion": 2,
                    "mode": "analyze",
                    "profile": "learnit-next-snapshot",
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(agent.AgentError, "cannot apply"):
            agent.cmd_apply(plan)

    def test_all_required_next_profiles_are_fixed(self) -> None:
        expected = {
            "learnit-next-snapshot",
            "learnit-next-fast",
            "learnit-next-full",
            "learnit-next-browser",
            "learnit-next-authoring",
            "learnit-next-contract",
        }
        self.assertEqual(agent.NEXT_PROFILES, expected)
        self.assertTrue(expected <= set(agent.PROFILE_COMMANDS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
