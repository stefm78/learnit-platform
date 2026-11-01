# LearnIT — private kit intake (draft integration)

This is a **governed, read-only intake planner**, not a released OneDrive writer or an automatic Factory hook. No Factory verdict, release set, source kit, historical job, public catalogue, or learner state is changed.

## Intended pipeline

1. The existing Factory V6 gate and `release_set_v6.verify_release_archive` verify a frozen exact release ZIP and its embedded Factory run evidence. Do not accept a caller-supplied `PASS` as proof.
2. Invoke `private_kit_intake_bridge.py` against a **governance-approved, clean checkout pinned to its exact commit**, current raw OneDrive `20_KITS/PRIVATE_INDEX.json`, and the release ZIP. It produces an immutable, read-only **plan** containing the exact lineage/revision/digest and actions.
3. The **future qualified OneDrive executor** must re-read current destination and parent ACLs, use create-only/conflict-fail and verify each uploaded file's raw SHA-256, unique path and owner-only ACL. Known identities are **verify-only** (never overwritten), even when the index claims `STORED_PRIVATE_VERIFIED`.
4. Update the private index and navigator only after all new copies have been verified and a qualified concurrency/CAS protocol covers those existing files. An index and HTML file are two separate mutations, so a partial failure is HOLD and must never be declared PASS. Do not treat read-before-write as atomic.
5. Activate automatic post-Factory PASS scheduling only after independent PR head qualification, source/credentials/permission review, a real end-to-end test and explicit governed authorization. Do not auto-enable on merge.

## Local, dependency-free tests

```sh
python -m unittest discover -s tools/tests -p 'test_private_kit_intake_bridge.py' -v
python -m py_compile tools/private_kit_intake_bridge.py
```

## Operator planning CLI

```sh
python tools/private_kit_intake_bridge.py \
  --release /path/to/QUALIFIED_V6_RELEASE_SET.zip \
  --verified-repository-checkout /path/to/CLEAN_LEARNIT_PLATFORM \
  --expected-repository-commit EXACT_APPROVED_SHA40 \
  --current-index /path/to/RAW_PRIVATE_INDEX.json \
  --output /tmp/PRIVATE_KIT_PLAN_NEW.json
```

The index must have been just retrieved from OneDrive as **raw bytes**. Output uses exclusive-create semantics and will not replace an existing plan. The caller must verify current UCP/HEAD and Operations/Factory authorities independently. The output is not mutation authority.

## Status

**DRAFT / NOT OPERATIONAL**. PR scope is strictly limited to this reader/validation module, its tests, this README and one work-package. The OneDrive adapter, atomic index update, HTML regeneration and automatic trigger are **separate unfulfilled gates**, not claimed by this candidate.
