"""Independent pre-candidate oracle for QA-WP-013 Gate 2 fan-in design review.

This file intentionally does not import a Gate 2 implementation or parent-design examples.
It owns a pure, QA-authored safety oracle. No final design PASS is permitted until this
corpus is rebound to one frozen exact parent-design HEAD.
"""
from __future__ import annotations

import ast
import itertools
import json
from pathlib import Path
import subprocess
import unittest
from typing import Any

BASELINE = "33d4ffc5f8aa5289008a72de301f937137f119e7"
BOUND_DESIGN_HEAD = "5a8c542c675d72f11a7f250ab58c5a2c3cbbf4f3"
BOUND_DESIGN_DOCUMENT_SHA256 = "7e8ea3b8abf2b44883cee786635cdf33e277c7197f155f2262a8d2cdc5ecb783"
BOUND_DESIGN_WORK_PACKAGE_SHA256 = "1ab0af3b3f59e4581e6e68f7fdf3be12d128185a2edf11c27415d5a581f80215"
BOUND_HOLD = "HOLD_GATE2_QA_PRE_EFFECT_DEPENDENCY_REVALIDATION_UNSPECIFIED"
EXPECTED_REPOSITORY = "stefm78/learnit-platform"
EXPECTED_GATE0_OPERATIONS = {
    "pr-snapshot", "pr-governor-evidence",
    "run-repository-validation", "run-test-profile",
}
FIXTURE_SCHEMA = "learnit.gate2.qa-oracle.v1"
ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
WORK_PACKAGE = ROOT / "work-packages" / "QA-WP-013.json"
IDENTITY_FIELDS = {
    "repository", "issue", "session_id", "generation",
    "job_id", "request_digest", "request_comment_id",
}
REQUIRED_ATTACK_IDS = {
    "cycle_self_A_to_A", "cycle_A_B_A", "cycle_long_A_B_C_A",
    "missing_predecessor", "duplicate_dependency",
    "same_job_id_wrong_digest", "same_digest_incompatible_identity",
    "predecessor_failed", "predecessor_stale", "predecessor_ambiguous",
    "outcome_deleted", "outcome_edited_same_comment_id",
    "outcome_body_digest_mismatch", "partial_fan_in", "complete_fan_in",
    "comment_reorder_is_semantically_stable", "pagination_instability",
    "cross_issue", "cross_session", "cross_generation", "wrong_repository",
    "descendant_runnable_too_early", "blocked_queue_not_empty",
    "premature_closure", "crash_before_durable_dependency_observation",
    "crash_after_job_started", "automatic_replay_after_job_started",
    "duplicate_terminal", "recovery_ambiguity", "bounds_at_declared_limit",
    "max_fan_in_exceeded", "max_depth_exceeded", "max_nodes_exceeded",
    "deterministic_election_multiple_runnable",
    "complete_fan_in_eight_predecessors",
    "max_edges_exceeded", "max_fan_out_exceeded", "max_payload_bytes_exceeded",
    "dependency_invalidated_after_election_before_effect",
    "dependency_invalidated_after_job_started_before_effect",
}

def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain one object")
    return value

def cases() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name in ("gate2_fanin_valid.json", "gate2_fanin_invalid.json"):
        out.extend(load_json(FIXTURES / name)["scenarios"])
    return out

def result(state: str, reason: str, *, runnable=(), selected=None,
           closable=False, recovery=False) -> dict[str, Any]:
    return {
        "queue_state": state, "runnable": list(runnable), "selected": selected,
        "closable": closable, "requires_recovery": recovery, "reason": reason,
    }

def cycle(nodes: dict[str, dict[str, Any]]) -> bool:
    color: dict[str, int] = {}
    def visit(n: str) -> bool:
        if color.get(n) == 1: return True
        if color.get(n) == 2: return False
        color[n] = 1
        for d in nodes[n].get("dependencies", []):
            target = d.get("node")
            if target in nodes and visit(target): return True
        color[n] = 2
        return False
    return any(visit(n) for n in nodes if color.get(n, 0) == 0)

def identity_reason(expected: dict[str, Any], observed: dict[str, Any]) -> str | None:
    if set(observed) != IDENTITY_FIELDS: return "DEPENDENCY_IDENTITY_SHAPE_INVALID"
    for field, reason in (
        ("repository", "CROSS_REPOSITORY_DEPENDENCY"),
        ("issue", "CROSS_ISSUE_DEPENDENCY"),
        ("session_id", "CROSS_SESSION_DEPENDENCY"),
        ("generation", "CROSS_GENERATION_DEPENDENCY"),
    ):
        if observed[field] != expected[field]: return reason
    if (observed["job_id"], observed["request_digest"]) != (
        expected["job_id"], expected["request_digest"]
    ): return "PREDECESSOR_IDENTITY_MISMATCH"
    if observed["request_comment_id"] != expected["request_comment_id"]:
        return "PREDECESSOR_REQUEST_COMMENT_MISMATCH"
    return None

def dependency_state(child: dict[str, Any], d: dict[str, Any],
                     nodes: dict[str, dict[str, Any]]) -> tuple[str, str]:
    p = nodes.get(d.get("node"))
    if p is None: return "INVALID", "MISSING_PREDECESSOR"
    expected, observed = p.get("identity"), d.get("identity")
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        return "INVALID", "DEPENDENCY_IDENTITY_SHAPE_INVALID"
    mismatch = identity_reason(expected, observed)
    if mismatch: return "INVALID", mismatch
    for field, reason in (
        ("repository", "CROSS_REPOSITORY_DEPENDENCY"),
        ("issue", "CROSS_ISSUE_DEPENDENCY"),
        ("session_id", "CROSS_SESSION_DEPENDENCY"),
        ("generation", "CROSS_GENERATION_DEPENDENCY"),
    ):
        if observed[field] != child["identity"][field]: return "INVALID", reason

    outcomes = p.get("outcomes", [])
    if len(outcomes) > 1: return "RECOVERY", "DUPLICATE_TERMINAL"
    if p.get("state") != "TERMINAL" or not outcomes:
        return "BLOCKED", "PREDECESSOR_NOT_TERMINAL"
    o = outcomes[0]
    binding = d.get("outcome_binding")
    if not isinstance(binding, dict): return "INVALID", "OUTCOME_BINDING_MISSING"
    if o.get("deleted"): return "BLOCKED", "OUTCOME_DELETED"
    if o.get("created_at") != o.get("updated_at"): return "BLOCKED", "OUTCOME_EDITED"
    if o.get("ambiguous"): return "BLOCKED", "PREDECESSOR_AMBIGUOUS"
    if o.get("stale"): return "BLOCKED", "PREDECESSOR_STALE"
    if o.get("comment_id") != binding.get("comment_id"):
        return "BLOCKED", "OUTCOME_COMMENT_ID_MISMATCH"
    if o.get("body_sha256") != binding.get("body_sha256"):
        return "BLOCKED", "OUTCOME_BINDING_DIGEST_MISMATCH"
    if o.get("observed_body_sha256") != binding.get("body_sha256"):
        return "BLOCKED", "OUTCOME_BODY_DIGEST_MISMATCH"
    if o.get("result") != "COMPLETED": return "BLOCKED", "PREDECESSOR_FAILED"
    return "SATISFIED", "SATISFIED"

def graph_oracle(case: dict[str, Any]) -> dict[str, Any]:
    items = case.get("nodes")
    if not isinstance(items, list): return result("INVALID", "GRAPH_SHAPE_INVALID")
    ids = [n.get("id") for n in items if isinstance(n, dict)]
    if len(ids) != len(items) or len(ids) != len(set(ids)):
        return result("INVALID", "DUPLICATE_NODE_ID")
    nodes = {n["id"]: n for n in items}

    jobs: dict[str, set[str]] = {}
    digests: dict[str, set[str]] = {}
    for n in items:
        i = n.get("identity")
        if not isinstance(i, dict) or set(i) != IDENTITY_FIELDS:
            return result("INVALID", "NODE_IDENTITY_SHAPE_INVALID")
        jobs.setdefault(i["job_id"], set()).add(i["request_digest"])
        digests.setdefault(i["request_digest"], set()).add(i["job_id"])
    if any(len(v) > 1 for v in jobs.values()):
        return result("INVALID", "JOB_ID_DIGEST_CONFLICT")
    if any(len(v) > 1 for v in digests.values()):
        return result("INVALID", "DIGEST_IDENTITY_CONFLICT")

    for n in items:
        seen: set[tuple[Any, ...]] = set()
        for d in n.get("dependencies", []):
            if d.get("node") not in nodes: return result("INVALID", "MISSING_PREDECESSOR")
            i = d.get("identity")
            if not isinstance(i, dict): return result("INVALID", "DEPENDENCY_IDENTITY_SHAPE_INVALID")
            key = (d.get("node"), i.get("job_id"), i.get("request_digest"))
            if key in seen: return result("INVALID", "DUPLICATE_DEPENDENCY")
            seen.add(key)
    if cycle(nodes): return result("INVALID", "CYCLE_DETECTED")

    lim = case.get("limits", {})
    if isinstance(lim, dict):
        if len(items) > lim.get("max_nodes", len(items)):
            return result("INVALID", "MAX_NODES_EXCEEDED")
        if any(len(n.get("dependencies", [])) > lim.get("max_fan_in", 10**9) for n in items):
            return result("INVALID", "MAX_FAN_IN_EXCEEDED")

    runnable: list[dict[str, Any]] = []
    blocked: list[str] = []
    per_node: dict[str, str] = {}
    for n in items:
        if n.get("state") == "TERMINAL": continue
        deps = n.get("dependencies", [])
        if not deps:
            runnable.append(n); continue
        states = [dependency_state(n, d, nodes) for d in deps]
        for kind, why in states:
            if kind == "INVALID": return result("INVALID", why)
            if kind == "RECOVERY":
                return result("RECOVERY_REQUIRED", why, recovery=True)
        if all(kind == "SATISFIED" for kind, _ in states):
            runnable.append(n)
        else:
            reasons = [why for kind, why in states if kind == "BLOCKED"]
            reason = "PARTIAL_FAN_IN" if any(k == "SATISFIED" for k, _ in states) else reasons[0]
            blocked.append(reason); per_node[n["id"]] = reason

    runnable.sort(key=lambda n: (
        n["identity"]["request_comment_id"], n["identity"]["job_id"], n["identity"]["request_digest"]
    ))
    runnable_ids = [n["id"] for n in runnable]
    if runnable:
        why = "DETERMINISTIC_SINGLE_ELECTION" if len(runnable) > 1 else "ALL_DEPENDENCIES_SATISFIED"
        # Preserve the stronger descendant-blocking reason when a root remains runnable.
        if blocked and any(r == "PARTIAL_FAN_IN" for r in blocked): why = "PARTIAL_FAN_IN"
        elif blocked and any(r == "PREDECESSOR_NOT_TERMINAL" for r in blocked): why = "PREDECESSOR_NOT_TERMINAL"
        return result("RUNNABLE", why, runnable=runnable_ids, selected=runnable_ids[0])
    if blocked:
        return result("BLOCKED", blocked[0])
    return result("EMPTY", "NO_PENDING_OR_BLOCKED_NODES", closable=True)

def snapshot_oracle(case: dict[str, Any]) -> dict[str, Any]:
    def normalize(scan: Any) -> list[tuple[Any, ...]]:
        if not isinstance(scan, list): raise AssertionError("scan must be a list")
        return sorted(
            (c.get("id"), c.get("body_sha256"), c.get("created_at"), c.get("updated_at"))
            for c in scan
        )
    a, b = normalize(case.get("scan_a")), normalize(case.get("scan_b"))
    if a != b:
        return result("RECOVERY_REQUIRED", "SNAPSHOT_UNSTABLE", recovery=True)
    return {
        "queue_state":"SNAPSHOT_STABLE","closable":False,
        "requires_recovery":False,"reason":"ORDER_NORMALIZED_BY_IMMUTABLE_COMMENT_ID"
    }

def bounds_oracle(case: dict[str, Any]) -> dict[str, Any]:
    lim, obs = case["limits"], case["observed"]
    for key, reason in (
        ("fan_in","MAX_FAN_IN_EXCEEDED"),
        ("depth","MAX_DEPTH_EXCEEDED"),
        ("nodes","MAX_NODES_EXCEEDED"),
        ("edges","MAX_EDGES_EXCEEDED"),
        ("fan_out","MAX_FAN_OUT_EXCEEDED"),
        ("payload_bytes","MAX_PAYLOAD_BYTES_EXCEEDED"),
    ):
        if obs[key] > lim["max_" + key]:
            return {"queue_state":"INVALID","closable":False,
                    "requires_recovery":False,"reason":reason}
    return {"queue_state":"BOUNDS_ACCEPTED","closable":False,
            "requires_recovery":False,"reason":"AT_DECLARED_LIMIT"}

def crash_oracle(case: dict[str, Any]) -> dict[str, Any]:
    if case.get("job_started"):
        if case.get("automatic_replay_attempted"):
            return {"queue_state":"RECOVERY_REQUIRED","closable":False,
                    "requires_recovery":True,"reason":"AUTOMATIC_REPLAY_FORBIDDEN"}
        if case.get("authority_ambiguous"):
            return {"queue_state":"RECOVERY_REQUIRED","closable":False,
                    "requires_recovery":True,"reason":"RECOVERY_AMBIGUITY"}
        if not case.get("terminal_outcome_observed"):
            return {"queue_state":"RECOVERY_REQUIRED","closable":False,
                    "requires_recovery":True,"reason":"CRASH_AFTER_JOB_STARTED"}
    if not case.get("durable_dependency_observation"):
        return {"queue_state":"BLOCKED","closable":False,
                "requires_recovery":False,"reason":"DEPENDENCY_OBSERVATION_NOT_DURABLE"}
    return {"queue_state":"INVALID","closable":False,
            "requires_recovery":False,"reason":"UNEXPECTED_CRASH_PROBE"}

def closure_oracle(case: dict[str, Any]) -> dict[str, Any]:
    if case.get("close_attempted") and (
        case.get("queue_state") == "BLOCKED" or case.get("blocked_nodes", 0) > 0
    ):
        return {"queue_state":"INVALID","closable":False,
                "requires_recovery":False,"reason":"BLOCKED_QUEUE_NOT_CLOSABLE"}
    return {"queue_state":"EMPTY","closable":True,
            "requires_recovery":False,"reason":"NO_PENDING_OR_BLOCKED_NODES"}

def timing_oracle(case: dict[str, Any]) -> dict[str, Any]:
    if not case.get("predecessor_invalidated_after_selection"):
        return {"queue_state":"INVALID","job_started":bool(case.get("descendant_job_started")),
                "gate0_invoked":bool(case.get("gate0_invoked")),"closable":False,
                "requires_recovery":False,"reason":"TIMING_PROBE_MISSING_INVALIDATION"}
    if case.get("descendant_job_started"):
        return {"queue_state":"RECOVERY_REQUIRED","job_started":True,
                "gate0_invoked":False,"closable":False,
                "requires_recovery":True,"reason":"DEPENDENCY_INVALIDATED_POST_START_PRE_EFFECT"}
    return {"queue_state":"GLOBAL_HOLD","job_started":False,
            "gate0_invoked":False,"closable":False,
            "requires_recovery":False,"reason":"DEPENDENCY_INVALIDATED_BEFORE_JOB_STARTED"}

def evaluate(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "graph": graph_oracle, "snapshot": snapshot_oracle,
        "bounds": bounds_oracle, "crash": crash_oracle, "closure": closure_oracle, "timing": timing_oracle,
    }[case["probe"]](case)

class FixtureOracleTests(unittest.TestCase):
    def test_fixture_documents_are_independent_pre_candidate_corpus(self) -> None:
        for name in ("gate2_fanin_valid.json", "gate2_fanin_invalid.json"):
            doc = load_json(FIXTURES / name)
            self.assertEqual(doc["schema"], FIXTURE_SCHEMA)
            self.assertEqual(doc["preparation_baseline"], BASELINE)
            self.assertEqual(doc["design_binding"]["status"], "BOUND_EXACT")
            self.assertEqual(doc["design_binding"]["head"], BOUND_DESIGN_HEAD)
            self.assertEqual(doc["design_binding"]["design_document_sha256"], BOUND_DESIGN_DOCUMENT_SHA256)
            self.assertEqual(doc["design_binding"]["design_work_package_sha256"], BOUND_DESIGN_WORK_PACKAGE_SHA256)
            self.assertEqual(doc["authority_issue"], 182)
            self.assertEqual(doc["parent_design_issue"], 181)
            self.assertTrue(doc["oracle_principles"])

    def test_required_adversarial_surface_is_present(self) -> None:
        ids = {c["id"] for c in cases()}
        self.assertEqual(REQUIRED_ATTACK_IDS - ids, set())

    def test_every_case_matches_independent_oracle(self) -> None:
        for case in cases():
            with self.subTest(case=case["id"]):
                actual = evaluate(case)
                expected = case["expected"]
                for key, value in expected.items():
                    self.assertEqual(actual.get(key), value, f"{case['id']}:{key}")

    def test_deterministic_election_is_permutation_independent_and_single(self) -> None:
        base = next(c for c in cases() if c["id"] == "deterministic_election_multiple_runnable")
        for permutation in itertools.permutations(base["nodes"]):
            probe = dict(base, nodes=list(permutation))
            got = graph_oracle(probe)
            self.assertEqual(got["selected"], "A")
            self.assertEqual(got["runnable"], ["A","B","C"])
            self.assertFalse(got["closable"])

    def test_blocked_is_never_empty_or_closable(self) -> None:
        for cid in ("blocked_queue_not_empty","partial_fan_in","descendant_runnable_too_early"):
            got = evaluate(next(c for c in cases() if c["id"] == cid))
            self.assertFalse(got["closable"])
            self.assertNotEqual(got["queue_state"], "EMPTY")

    def test_started_replay_and_ambiguity_always_require_recovery(self) -> None:
        for cid in ("crash_after_job_started","automatic_replay_after_job_started",
                    "recovery_ambiguity","duplicate_terminal","pagination_instability"):
            got = evaluate(next(c for c in cases() if c["id"] == cid))
            self.assertTrue(got["requires_recovery"])
            self.assertEqual(got["queue_state"], "RECOVERY_REQUIRED")

class ExactDesignBindingTests(unittest.TestCase):
    def test_work_package_records_pre_candidate_then_exact_bound_hold(self) -> None:
        wp = load_json(WORK_PACKAGE)
        ex = wp["execution"]
        self.assertEqual(ex["stateHistory"][0]["state"], "PRE_CANDIDATE_ORACLE_READY")
        self.assertEqual(ex["stateHistory"][0]["verdict"], "PRE_CANDIDATE_GATE2_QA_READY")
        self.assertEqual(ex["designBinding"]["status"], "BOUND_EXACT")
        self.assertEqual(ex["designBinding"]["designHead"], BOUND_DESIGN_HEAD)
        self.assertEqual(ex["designBinding"]["designDocumentSha256"], BOUND_DESIGN_DOCUMENT_SHA256)
        self.assertEqual(ex["designBinding"]["designWorkPackageSha256"], BOUND_DESIGN_WORK_PACKAGE_SHA256)
        self.assertEqual(ex["verdict"], BOUND_HOLD)
        self.assertEqual(ex["finalVerdict"], BOUND_HOLD)
        self.assertFalse(ex["mergeAuthorized"])

    def test_blocking_finding_prevents_pass_on_bound_head(self) -> None:
        ex = load_json(WORK_PACKAGE)["execution"]
        findings = ex.get("findings", [])
        self.assertTrue(findings)
        self.assertEqual(findings[0]["id"], "G2-QA-013-F01")
        self.assertEqual(findings[0]["severity"], "blocking")
        self.assertEqual(findings[0]["designHead"], BOUND_DESIGN_HEAD)
        self.assertNotEqual(ex["finalVerdict"], "PASS_GATE2_DESIGN_CONTRADICTORY_QA")

def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True,
        capture_output=True,
    ).stdout.strip()

class RepositoryBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.is_repo = git("rev-parse","--is-inside-work-tree") == "true"
        except (OSError, subprocess.CalledProcessError):
            cls.is_repo = False

    def require_repo(self) -> None:
        if not self.is_repo:
            self.skipTest("requires exact repository checkout")

    def test_gate0_is_byte_identical_to_preparation_baseline(self) -> None:
        self.require_repo()
        for path in ("tools/codespace_evidence","tests/codespace_evidence"):
            self.assertEqual(git("rev-parse",f"{BASELINE}:{path}"),git("rev-parse",f"HEAD:{path}"))

    def test_gate1_runtime_is_unchanged_during_design_oracle_preparation(self) -> None:
        self.require_repo()
        self.assertEqual(
            git("rev-parse",f"{BASELINE}:tools/ai_jobs"),
            git("rev-parse","HEAD:tools/ai_jobs"),
        )

    def test_no_gate2_runtime_module_or_parallel_runtime_is_introduced(self) -> None:
        self.require_repo()
        names = {p.name.lower() for p in (ROOT/"tools/ai_jobs").glob("*.py")}
        self.assertFalse(any("gate2" in n or "fanin" in n for n in names))
        source = (ROOT/"tools/ai_jobs/__init__.py").read_text(encoding="utf-8")
        self.assertIn('"gate3-repository-write-job"', source)
        self.assertIn('"gate4-parallel-execution"', source)

    def test_gate0_operation_surface_remains_exactly_read_only_four(self) -> None:
        self.require_repo()
        import tools.ai_jobs as gate1
        self.assertEqual(set(gate1.GATE0_OPERATIONS), EXPECTED_GATE0_OPERATIONS)
        forbidden = {"repo-write","branch-create","commit","push","workflow-dispatch",
                     "merge","release","promotion","gate3-repository-write-job",
                     "gate4-parallel-execution"}
        self.assertFalse(set(gate1.GATE0_OPERATIONS) & forbidden)

    def test_gate1_cli_exposes_no_arbitrary_argv_shell_or_repository_write_switch(self) -> None:
        self.require_repo()
        tree = ast.parse((ROOT/"tools/ai_jobs/run.py").read_text(encoding="utf-8"))
        options = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_argument":
                for arg in n.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value,str) and arg.value.startswith("--"):
                        options.add(arg.value.lower())
        fragments=("command","argv","shell","script","repo-write","branch","commit","push",
                   "workflow","merge","release","gate2","gate3","gate4")
        self.assertEqual([o for o in sorted(options) if any(f in o for f in fragments)],[])

    def test_privileged_transport_has_no_repository_write_endpoints(self) -> None:
        self.require_repo()
        source=(ROOT/"tools/ai_jobs/github_transport.py").read_text(encoding="utf-8").lower()
        for token in ("/git/refs","/merges","/releases","/actions/workflows",
                      "workflow_dispatch","/deployments"):
            self.assertNotIn(token,source)

    def test_gate1_85_of_85_and_gate0_80_of_80_remain_mandatory_evidence(self) -> None:
        self.require_repo()
        parent=load_json(ROOT/"work-packages/OPS-WP-007.json")
        self.assertEqual(parent["result"]["gate1Runtime"]["tests"],85)
        self.assertEqual(parent["result"]["gate1Runtime"]["result"],"PASS")
        self.assertEqual(parent["result"]["gate1Runtime"]["skip"],0)
        self.assertEqual(parent["result"]["gate1Runtime"]["xfail"],0)
        self.assertEqual(parent["result"]["gate0Regression"]["tests"],80)
        self.assertEqual(parent["result"]["gate0Regression"]["result"],"PASS")
        evidence="\n".join(load_json(WORK_PACKAGE)["requiredEvidence"])
        self.assertIn("85/85 PASS",evidence)
        self.assertIn("80/80 PASS",evidence)

if __name__ == "__main__":
    unittest.main()
