#!/usr/bin/env python3
"""Fail-closed state/session/package validator for limited pilot R1."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
STATE_PATH = ROOT / "qualification" / "student-v0.1" / "limited-pilot-r1" / "PILOT_STATE.json"
LEDGER_PATH = ROOT / "qualification" / "student-v0.1" / "limited-pilot-r1" / "COHORT_LEDGER.json"
SESSIONS_DIR = ROOT / "qualification" / "student-v0.1" / "limited-pilot-r1" / "sessions"
KIT_PATH = ROOT / "showcase" / "student-v0.1" / "nombres-complexes" / "nombres_complexes_student_v01_v5.json"

CANDIDATE_SHA = "e04cf62963faae83e073cde9cffd9d33ae42dc9c"
KIT_SHA256 = "aeac0925e686d6055405382142ad14831c27f73992401a1748ec76b85665c62b"
MAX_SESSIONS = 6
SESSION_IDS = [f"LP0{i}" for i in range(1, 7)]
SESSION_STATUS = {"COMPLETED", "PARTIAL", "ABORTED"}
LEDGER_STATUS = {"NOT_RUN"} | SESSION_STATUS
STATES = {"PREPARING", "READY_NOT_STARTED", "ACTIVE", "HOLD_PENDING_HUMAN", "HOLD", "COHORT_TARGET_REACHED", "COHORT_COMPLETE"}
PERMISSIONS = {"CONFIRMED", "NOT_REQUIRED"}
SEVERITIES = {"BLOCKER", "MAJOR", "MINOR", "NOTE"}
CATEGORIES = {"TECHNICAL", "UX", "ACCESSIBILITY", "PEDAGOGICAL", "FEEDBACK_TRUST", "PROGRESS_CLARITY", "RECOVERY", "OTHER"}
KNOWN_LIMITATIONS = {"HR24_003", "NONE"}
RATINGS = {"startClarity", "flowClarity", "feedbackTrust", "progressClarity", "overallEase"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_KEY = re.compile(r"(?:^|_)(name|email|birth|dob|address|location|ip|account|credential|audio|video|photo|image)(?:$|_)", re.I)
EMAIL_LIKE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
IP_LIKE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def activity_count() -> int:
    raw = KIT_PATH.read_bytes()
    assert sha256(raw) == KIT_SHA256, "V5 kit identity drift"
    kit = json.loads(raw.decode("utf-8"))
    return sum(len(course.get("activities", [])) for course in kit.get("courses", []))

def assert_no_pii_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert not FORBIDDEN_KEY.search(key), f"forbidden identifying key {path}.{key}"
            assert_no_pii_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            assert_no_pii_keys(child, f"{path}[{i}]")
    elif isinstance(value, str):
        assert not EMAIL_LIKE.search(value), f"email-like identifier in {path}"
        assert not IP_LIKE.search(value), f"IP-like identifier in {path}"

def validate_state(state: dict) -> None:
    assert state["schema"] == "student.v0.1.limited-pilot-state.v1"
    assert state["job"] == "JOB_31_LIMITED_PILOT_5_6_STUDENTS_EXECUTION_R1"
    assert state["workPackage"] == "ATLAS-WP-073"
    assert state["candidateSha"] == CANDIDATE_SHA
    assert state["maxAuthorizedStudentSessions"] == MAX_SESSIONS
    assert state["state"] in STATES
    assert state["completedRealSessions"] in range(0, 7)
    assert state["holdStatus"] in {"NONE", "HOLD_PENDING_HUMAN", "HOLD"}
    hr = state["hr24_003"]
    assert hr["status"] == "CONFIRMED_SEPARATE_ENGINE_JOB_REQUIRED"
    assert hr["pilotAcceptance"] == "ACCEPT"
    if state["state"] == "PREPARING":
        assert state["learnerPackageSha256"] == "PENDING_QUALIFICATION"
        assert state["facilitatorPackageSha256"] == "PENDING_QUALIFICATION"
    else:
        assert HEX64.fullmatch(state["learnerPackageSha256"])
        assert HEX64.fullmatch(state["facilitatorPackageSha256"])

def validate_record(record: dict, state: dict, activity_max: int, *, existing_ids: set[str]) -> None:
    required = {
        "schema","sessionId","candidateSha","learnerPackageSha256","permissionStatus","sessionStatus",
        "durationMinutes","courseCompleted","activitiesCompleted","facilitatorAssistanceCount",
        "recoveryOrResumeObserved","technicalIncidents","findings","postSessionRatings",
        "sanitizedFacilitatorSummary","evidenceSource","recordedAt"
    }
    assert set(record) == required, f"session record fields mismatch: {sorted(set(record)^required)}"
    assert record["schema"] == "student.v0.1.limited-pilot-session.v1"
    sid = record["sessionId"]
    assert sid in SESSION_IDS, "invalid session id"
    assert sid not in existing_ids, "duplicate session id"
    assert record["candidateSha"] == CANDIDATE_SHA
    assert HEX64.fullmatch(state["learnerPackageSha256"])
    assert record["learnerPackageSha256"] == state["learnerPackageSha256"], "learner package identity drift"
    assert record["permissionStatus"] in PERMISSIONS, "permission not confirmed/not-required"
    assert record["sessionStatus"] in SESSION_STATUS
    assert isinstance(record["durationMinutes"], int) and record["durationMinutes"] >= 0
    assert isinstance(record["courseCompleted"], bool)
    assert isinstance(record["activitiesCompleted"], int) and 0 <= record["activitiesCompleted"] <= activity_max
    assert isinstance(record["facilitatorAssistanceCount"], int) and record["facilitatorAssistanceCount"] >= 0
    assert isinstance(record["recoveryOrResumeObserved"], bool)
    assert isinstance(record["technicalIncidents"], list)
    assert isinstance(record["findings"], list)
    for finding in record["findings"]:
        assert set(finding) == {"severity","category","summary","knownLimitation"}
        assert finding["severity"] in SEVERITIES
        assert finding["category"] in CATEGORIES
        assert isinstance(finding["summary"], str)
        assert finding["knownLimitation"] in KNOWN_LIMITATIONS
    ratings = record["postSessionRatings"]
    assert isinstance(ratings, dict) and set(ratings) == RATINGS
    for value in ratings.values():
        assert value is None or (isinstance(value, int) and 1 <= value <= 5)
    assert isinstance(record["sanitizedFacilitatorSummary"], str)
    assert record["evidenceSource"] == "REAL_HUMAN_FACILITATOR_USER_PROVIDED_EVIDENCE"
    assert isinstance(record["recordedAt"], str) and record["recordedAt"].strip()
    assert_no_pii_keys(record)
    if state["state"] in {"HOLD", "HOLD_PENDING_HUMAN"}:
        raise AssertionError("session admission forbidden while pilot is on hold")
    if state["completedRealSessions"] >= MAX_SESSIONS:
        raise AssertionError("seventh session forbidden")
    if state["completedRealSessions"] == 5 and sid == "LP06" and state["state"] != "ACTIVE":
        raise AssertionError("LP06 requires explicit post-five human continuation reflected as ACTIVE")

def validate_ledger(ledger: dict, state: dict) -> None:
    assert ledger["schema"] == "student.v0.1.limited-pilot-ledger.v1"
    assert ledger["candidateSha"] == CANDIDATE_SHA
    assert ledger["maxAuthorizedStudentSessions"] == MAX_SESSIONS
    slots = ledger["slots"]
    assert [slot["sessionId"] for slot in slots] == SESSION_IDS
    assert len({slot["sessionId"] for slot in slots}) == 6
    for slot in slots:
        assert slot["status"] in LEDGER_STATUS
    count = sum(slot["status"] in SESSION_STATUS for slot in slots)
    assert count == state["completedRealSessions"], (count, state["completedRealSessions"])
    if count == 0:
        assert all(slot["status"] == "NOT_RUN" for slot in slots)
    if count == 5:
        assert state["state"] in {"COHORT_TARGET_REACHED","ACTIVE","HOLD","HOLD_PENDING_HUMAN","COHORT_COMPLETE"}
    if count == 6:
        assert state["state"] == "COHORT_COMPLETE"

def validate_repo_state() -> None:
    state = load_json(STATE_PATH)
    ledger = load_json(LEDGER_PATH)
    validate_state(state)
    validate_ledger(ledger, state)
    count_max = activity_count()
    existing: set[str] = set()
    records = sorted(SESSIONS_DIR.glob("LP*.json")) if SESSIONS_DIR.exists() else []
    for path in records:
        record = load_json(path)
        validate_record(record, state, count_max, existing_ids=existing)
        existing.add(record["sessionId"])
        slot = next(s for s in ledger["slots"] if s["sessionId"] == record["sessionId"])
        assert slot["status"] == record["sessionStatus"]
    assert len(existing) == state["completedRealSessions"], "durable session-record count mismatch"

def validate_zip(path: Path, expected_names: list[str]) -> None:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        assert names == sorted(expected_names), names
        assert z.comment == b""
        for info in z.infolist():
            p = Path(info.filename)
            assert not p.is_absolute() and ".." not in p.parts
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.extra == b"" and info.comment == b""

def package_check(learner: Path, facilitator: Path, state: dict) -> None:
    validate_zip(learner, ["START_HERE.html","course.learnit.json","learnit-next.html","pilot_identity.json"])
    validate_zip(facilitator, [
        "CHECKSUMS.json","COHORT_LEDGER_TEMPLATE.json","FACILITATOR_RUNBOOK.md",
        "KNOWN_LIMITATION_HR24_003.md","PRIVACY_DATA_MINIMIZATION.md",
        "SESSION_RECORD_TEMPLATE.json","SEVERITY_RUBRIC.md","pilot_identity.json"
    ])
    with zipfile.ZipFile(learner) as z:
        assert len(z.read("learnit-next.html")) == 583764
        assert sha256(z.read("learnit-next.html")) == "7ee493b8855e4cda7703deccbf5c813391afaa5a9674d6760b75a277e0267553"
        assert sha256(z.read("course.learnit.json")) == KIT_SHA256
        identity = json.loads(z.read("pilot_identity.json"))
        assert identity["candidateSha"] == CANDIDATE_SHA
        assert identity["kitContract"] == "learnit.kit.v5"
        start = z.read("START_HERE.html").decode("utf-8").lower()
        assert "http://" not in start and "https://" not in start
        assert "facilitator" not in start and "évalu" not in start and "evalu" not in start
    if state["state"] != "PREPARING":
        assert sha256(learner.read_bytes()) == state["learnerPackageSha256"]
        assert sha256(facilitator.read_bytes()) == state["facilitatorPackageSha256"]

def expect_reject(record: dict, state: dict, count: int, existing: set[str] | None = None) -> None:
    try:
        validate_record(record, state, count, existing_ids=existing or set())
    except AssertionError:
        return
    raise AssertionError("adversarial record unexpectedly accepted")

def self_test() -> None:
    count = activity_count()
    base_state = {
        "schema":"student.v0.1.limited-pilot-state.v1",
        "job":"JOB_31_LIMITED_PILOT_5_6_STUDENTS_EXECUTION_R1",
        "workPackage":"ATLAS-WP-073",
        "candidateSha":CANDIDATE_SHA,
        "learnerPackageSha256":"0"*64,
        "facilitatorPackageSha256":"1"*64,
        "completedRealSessions":0,
        "maxAuthorizedStudentSessions":6,
        "state":"ACTIVE",
        "holdStatus":"NONE",
        "hr24_003":{"status":"CONFIRMED_SEPARATE_ENGINE_JOB_REQUIRED","pilotAcceptance":"ACCEPT"},
    }
    valid = {
        "schema":"student.v0.1.limited-pilot-session.v1","sessionId":"LP01","candidateSha":CANDIDATE_SHA,
        "learnerPackageSha256":"0"*64,"permissionStatus":"CONFIRMED","sessionStatus":"COMPLETED",
        "durationMinutes":30,"courseCompleted":True,"activitiesCompleted":count,"facilitatorAssistanceCount":0,
        "recoveryOrResumeObserved":False,"technicalIncidents":[],"findings":[],
        "postSessionRatings":{k:None for k in RATINGS},"sanitizedFacilitatorSummary":"",
        "evidenceSource":"REAL_HUMAN_FACILITATOR_USER_PROVIDED_EVIDENCE","recordedAt":"2026-09-29T00:00:00Z"
    }
    validate_record(valid, base_state, count, existing_ids=set())
    bad = dict(valid); bad["sessionId"]="LP07"; expect_reject(bad, base_state, count)
    bad = dict(valid); bad["candidateSha"]="f"*40; expect_reject(bad, base_state, count)
    bad = dict(valid); bad.pop("durationMinutes"); expect_reject(bad, base_state, count)
    expect_reject(valid, base_state, count, {"LP01"})
    hold = dict(base_state); hold["state"]="HOLD"; hold["holdStatus"]="HOLD"; expect_reject(valid, hold, count)
    six = dict(base_state); six["completedRealSessions"]=6; expect_reject(valid, six, count)
    five = dict(base_state); five["completedRealSessions"]=5; five["state"]="COHORT_TARGET_REACHED"
    lp6=dict(valid); lp6["sessionId"]="LP06"; expect_reject(lp6, five, count)
    pii=dict(valid); pii["sanitizedFacilitatorSummary"]="contact student@example.com"; expect_reject(pii, base_state, count)
    print("SESSION_VALIDATOR_ADVERSARIAL=PASS")
    print("MACHINE_SMOKE_ONLY_NOT_A_REAL_STUDENT_SESSION")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--learner-package", type=Path)
    parser.add_argument("--facilitator-package", type=Path)
    parser.add_argument("--self-test-adversarial", action="store_true")
    args = parser.parse_args()
    validate_repo_state()
    if args.self_test_adversarial:
        self_test()
    if args.learner_package or args.facilitator_package:
        assert args.learner_package and args.facilitator_package
        package_check(args.learner_package, args.facilitator_package, load_json(STATE_PATH))
    print("PILOT_STATE_AND_LEDGER=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
