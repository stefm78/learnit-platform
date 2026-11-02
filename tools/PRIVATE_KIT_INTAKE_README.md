# LearnIT — private kit intake (draft integration)

This is a **governed planning and bounded private-copy engine**. The execution engine accepts only a provider adapter with real server-side create-only/conflict-fail semantics. It is **not** an activated OneDrive adapter or Factory hook. No Factory verdict, release set, source kit, historical job, public catalogue, or learner state is changed.

## Intended pipeline

1. The existing Factory V6 gate and `release_set_v6.verify_release_archive` verify a frozen exact release ZIP and its embedded Factory run evidence. Do not accept a caller-supplied `PASS` as proof.
2. Invoke `private_kit_intake_bridge.py` against a **governance-approved, clean checkout pinned to its exact commit**, current raw OneDrive `20_KITS/PRIVATE_INDEX.json`, and the release ZIP. It produces an immutable, read-only **plan** containing the exact lineage/revision/digest and actions.
3. `private_kit_intake_executor.py` provides the tested, provider-neutral bounded executor: it re-reads destination and parent ACLs, requires a provider adapter implementing genuinely atomic create-only/conflict-fail, and re-reads SHA-256 and owner-only ACL after each upload. Known identities are **verify-only**, using their actual historical destination filenames (never guessed or overwritten). **No production adapter has yet been qualified.**
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

**DRAFT / NOT OPERATIONAL**. PR includes planner, portable transport-independent copy engine, tests, README and one work-package. The actual OneDrive provider adapter, proven conditional index write, HTML regeneration and credentialed post-Factory hook are **unfulfilled gates**. Provider-neutral tests are not a live provider contract. **No merge, activation or student publication is implied.**

## R2 extension / provider adapter contract

`private_kit_intake_executor.execute_verified_plan(plan, exact_verified_members, port, course_root_id, authorization=True)` is for a **trusted caller** that has already verified current UCP/HEAD, current Operations admission, the exact V6 release and the clean canonical Git checker. The Boolean is an invocation guard **not a substitute for authorization**, and exposing this function as a public API without those checks would be unsafe.

The adapter must provide `child`, `create_folder_fail`, `create_file_fail`, `content`, `permissions`. Its create operations **must fail server-side on conflict** (read-before-create is not sufficient), must not rename, and must not blindly retry ambiguous commits. Every folder and kit is independently checked private; an unexpected ACL or byte mismatch is HOLD, including when a previous creation partly succeeded. The result `PASS_PRIVATE_COPIES_VERIFIED_INDEX_NOT_COMMITTED` is deliberately **not** final registration success. No code writes `PRIVATE_INDEX.json` or `NAVIGUER_KITS.html` here.

The active OneDrive personal `/content` REST documentation does not specify `If-Match` as an assured atomic precondition for existing content replacement. Do not assume it from ordinary `If-Match` metadata PATCH or a simulated provider. For the two derived views, require exact provider-tested CAS/controlled single-writer strategy, explicit recovery of possible partial writes, and live readback. Until independently qualified, HOLD activation. Likewise no GitHub Actions trigger, unattended delegated OneDrive token or new production job is installed by this PR.

Run all local checks (38 including executor simulations):

```sh
python -m unittest discover -s tools/tests -p 'test_private_kit_intake*.py' -v
python -m py_compile tools/private_kit_intake_bridge.py tools/private_kit_intake_executor.py
```
