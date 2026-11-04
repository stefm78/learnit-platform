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

**DRAFT / NOT OPERATIONAL**. PR includes planner, portable transport-independent copy engine, a draft Graph upload-session contract, deterministic private index/navigation generation, a read-only post-Factory PASS binding, tests, README and one work-package. The actual qualified OneDrive provider, proven live conditional index/navigation update and credentialed automatic post-Factory hook are **unfulfilled gates**. Provider-neutral tests are not a live provider contract. **No merge, activation or student publication is implied.**

## R2 extension / provider adapter contract

`private_kit_intake_executor.execute_verified_plan(plan, exact_verified_members, port, course_root_id, authorization=True)` is for a **trusted caller** that has already verified current UCP/HEAD, current Operations admission, the exact V6 release and the clean canonical Git checker. The Boolean is an invocation guard **not a substitute for authorization**, and exposing this function as a public API without those checks would be unsafe.

The adapter must provide `child`, `create_folder_fail`, `create_file_fail`, `content`, `permissions`. Its create operations **must fail server-side on conflict** (read-before-create is not sufficient), must not rename, and must not blindly retry ambiguous commits. Every folder and kit is independently checked private; an unexpected ACL or byte mismatch is HOLD, including when a previous creation partly succeeded. The result `PASS_PRIVATE_COPIES_VERIFIED_INDEX_NOT_COMMITTED` is deliberately **not** final registration success. No code writes `PRIVATE_INDEX.json` or `NAVIGUER_KITS.html` here.

The active OneDrive personal `/content` REST documentation does not specify `If-Match` as an assured atomic precondition for existing content replacement. Do not assume it from ordinary `If-Match` metadata PATCH or a simulated provider. For the two derived views, require exact provider-tested CAS/controlled single-writer strategy, explicit recovery of possible partial writes, and live readback. Until independently qualified, HOLD activation. Likewise no GitHub Actions trigger, unattended delegated OneDrive token or new production job is installed by this PR.

Run all local checks (38 including executor simulations):

```sh
python -m unittest discover -s tools/tests -p 'test_private_kit_intake*.py' -v
python -m py_compile tools/private_kit_intake_bridge.py tools/private_kit_intake_executor.py
```

## Inactive post-PASS integration candidate (PR #511)

- `graph_session_create.py`: draft Microsoft Graph `createUploadSession` conflict-fail contract; requires externally qualified credentials and transport, with no production authorization or live provider claim.
- `private_kit_views.py`: validates the existing private index schema, builds deterministic searchable/grouped HTML, and coordinates two distinct conditional view writes only through a provider that proves real concurrency safety. Partial failure is HOLD and can be reconciled on replay.
- `post_pass_factory_step.py`: read-only event-to-canonical-release binding from a clean pinned Git checkout. It neither registers an unattended hook nor performs a remote write.
- The three corresponding tests under `tools/tests/` are local simulations (47/47 PASS at candidate staging); they are not proof of actual Graph authentication, CAS, owner-only ACL or real event delivery.

Until those live gates and separate human approvals pass, the existing Factory remains unchanged; never interpret a code commit, unit-test PASS or private navigator entry as release, publication or activation.

## Future ChatGPT scheduled kit generation — human-controlled handoff (not activated)

The **scheduled ChatGPT task prompt** is the AI entry point, not this PR, an old
`AI_RUNBOOK.md` alias, the historical J9 job, or a GitHub Actions timer. This PR
only provides a read-only, callable *post-qualification* adapter and a human
handoff. Installing/activating a schedule and authorizing Factory mutations are
separate governed steps.

At **each** scheduled occurrence (never rely on an earlier chat/snapshot):

1. Verify the human-installed UCP anchor, active HEAD, Operations charter,
   allowed source/write scope, and exact authority versions. Resolve
   `80_CONTROL/AI_CONTINUATION/AI_CONTINUATION_AUTHORITY_RESOLUTION_V1.json`,
   reconstruct the complete `AUTHORITY_STATELOG` and load only the versioned
   runbook/contract/selection/conflict artifacts of the *activated* set. The
   observed historical set was `AI_CONTINUATION_J3R2_SET_1`; recheck it live.
2. If course discovery or planning is authorized, reuse the exact, SHA-verified
   `80_CONTROL/SCALE_AUTOMATION/V1/learnit_scale.py` (J9) for **course planning**,
   not pedagogical V6 kit authoring or publication. J3R2 work selection is not
   permission to mutate. Do not reopen historical terminal J6/J7/J9 jobs.
3. Run V6 generation/review only under a current *separately admitted* job and
   its allowed outputs. Require a durable release ZIP, exact FactoryRun IDs,
   and fresh canonical `authoring/factory/release_set_v6.py verify` result
   `PASS_QUALIFIED_RELEASE_SET_V6_VERIFICATION_R1`. An intermediate build PASS,
   chat assertion or stale release is insufficient.
4. With a governance-approved clean checkout, just-fetched **raw** private
   index, and a durable matching event, invoke the read-only CLI below. Show
   the **human command** in the ChatGPT report; do not send it as an automatic
   instruction or infer the user's GO. A fully indexed release yields a
   verification-only message with **no write GO**.
5. If a source, connector, canonical release, ledger, authorization, or
   freshness check fails, return HOLD and identify the exact missing gate;
   no fallback to old aliases, historical results, or local project uploads.

```sh
python tools/post_pass_factory_step.py \
  --release /exact/path/QUALIFIED_V6_RELEASE_SET.zip \
  --checkout /exact/path/CLEAN_GOVERNED_LEARNIT_PLATFORM \
  --commit EXACT_APPROVED_FACTORY_GIT_SHA40 \
  --index-raw /exact/path/LIVE_RAW_PRIVATE_INDEX.json \
  --event /exact/path/FACTORY_V6_QUALIFIED_RELEASE_DURABLE.json \
  --human-command
```

The CLI must be run **only after** current J3R2/J9/Factory/Operations gates
have passed. It independently checks the clean Git checkout, re-runs the
canonical release verifier, binds the event and exact ZIP, and re-plans using
raw index bytes. Exit **0** returns an operator-facing message; exit **8** is
HOLD and never a GO. Omit `--human-command` to keep the original JSON receipt
(`manual_handoff`, `remote_mutation=false`, `automatic_hook_installed=false`).
Event JSON with duplicate object keys is rejected before processing.

**Strict separation:** neither this flag, a future ChatGPT scheduled run, nor
PR merge authorizes OneDrive `20_KITS`, `PRIVATE_INDEX.json`,
`NAVIGUER_KITS.html`, `05_CATALOGUE`, Graph ACL changes, public/student release,
or any task/runner activation. Every private-copy/index/view update requires
its own fresh human GO, live source/permissions checks, conflict=fail and
post-write SHA-256/ACL verification. No schedule, hook, credential or new job
is installed by this change; the draft PR remains non-operational until its
independent gates pass.
