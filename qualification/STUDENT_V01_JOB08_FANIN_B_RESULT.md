# Student V0.1 — JOB08 Fan-in B Result

Status: PASS
Work package: `ATLAS-WP-044`
Authority issue: `#425`
Pull request: `#426`

## Exact candidate binding

- JOB08_BASE: `d5050bace4c7dcbb63dcfe44a64ef344434e9bc2`
- G3_R1_RESULT_SHA: `f0b8af8adeab132bec0ebe9410951e6add294c5b`
- REPAIRED_PRODUCT_SHA: `bdb66bffefd6738e3cb4004d304159e9d3d048ce`
- JOB05_R1_RESULT_SHA: `1c92cad7ea576a613b6f198768bbebd114a06082`
- JOB06_R1_RESULT_SHA: `80ec72fef535e78013a9f0fb10bedb57f05bc761`
- JOB07_R2_RESULT_SHA: `5e492fddc4d5cf00c71bdb770eb1aeac11a63803`
- RESULT_SHA: `757ed15e840bfca603de0eac3bef1e9d5ff3483d`
- GitHub main during qualification: `21d25c36aec6c04fdfe8126c95e71cbf80771a1b`

No merge or cherry-pick was used.

## Human Control Plane binding

Fresh bootstrap and operational authority were validated before governed mutation.

- UCP: `UCP-CONTROL-PLANE`, `ACTIVE`, version `1.1-R4`
- UCP SHA-256: `c499abc9d1045b3cbe0b632d7470ccbbe52d4dc726968e5206cfdde393f2cfb4`
- CONTROL_PLANE_HEAD Git blob: `2a9014e2b2051b0ede746a9772cdbbe471f55e3a`
- UAO 2.6 SHA-256: `dad404793b931bc4b7448d546dd6a54397fe32ea6a57213d3c42a3546441140e`
- Kernel registry 2.5 SHA-256: `41abb5e2b36607bbdc246d64f32e03584689bd2efc599921ca7406c404f476d6`
- Compatibility contract SHA-256: `0d2c2c566aa5059adf7854d5a062476945dd4e09032955fd1f421cc53b8acbc4`

The selected UAR/UAS/UAB/UAA/UAL payloads and active governance rules were reread and byte-SHA-256 verified against CONTROL_PLANE_HEAD before execution.

## Frozen Fan-in B manifest and exact role payloads

Manifest:
`qualification/STUDENT_V01_G3_R1_FANIN_B_INPUT_MANIFEST.json`

Required/observed Git blob:
`d76d624b6e76655b60b1a43b1dafbce22d3eb087`

The 18 role payload files were materialized individually by exact Git blob identity from the immutable result SHAs. No sibling commit was merged or cherry-picked, and no role-owned byte was edited afterward.

JOB05 R1:
- `qa/student-v0.1/JOB05_CANONICAL_V4_FIXTURE.json` — `c190fc4f04a7cee5731627e4f6276ee08e39d746`
- `qa/student-v0.1/browser_job05_r1_contradictory_qa.py` — `9c33a185a957b3b3513822a4cc3f72294a867fae`
- `qa/student-v0.1/job05_r1_contradictory_qa.py` — `a7a1ac5baa93df355cc687d4635ff5f9837e30d9`

JOB06 R1:
- `showcase/student-v0.1/nombres-complexes/AUTHOR_AUDIT.md` — `dcbd252559292c9a9b1949b3cf85007cc60949e0`
- `FACTORY_CONTEXT.json` — `ea5ce453421bfe25db8e1a16597953cad77ac2db`
- `FACTORY_REVIEW_REQUEST.md` — `4e6903e9854c357a6d99178d0b8b4ba2614a5c67`
- `LEARNER_BRIEF.json` — `6c4fb770f12690a3cb338c82fc77bf9b323c3b06`
- `PEDAGOGICAL_QUALITY_REPORT.json` — `747daee9ad0ff3dc8c4c6b7c2edd621bbc26e963`
- `PROVENANCE_MAP.json` — `7fb0a7153a22c8e2b9bb6b899b152867e89f0cfc`
- `SOURCE_BASIS.md` — `f10e8f0f78512f4b3c95befb28e9fe565e8c99c9`
- `V4_VALIDATION_REPORT.json` — `711ebee54d9007364ffadfa964e907b09bdc550d`
- `nombres_complexes_student_v01_v4.json` — `03ed1d5819911c23734980f89716f4ca18a6bca4`

JOB07 R2:
- `pilot/student-v0.1/browser_generated_v4_probe.py` — `b5a4ecbf5879effb698929e17fb5c263ba8400c7`
- `browser_pilot_package.py` — `ae86fb159e322b24c1ce37ca662d4d5674422b43`
- `build_pilot_package.py` — `47ccfd8a7f6df23bc2c77b057f54f4502cff09a0`
- `ci_job07_r2.py` — `8c27a4dbdb9e2b16051da6d77b1a6a243705b555`
- `materialize_qualification_kit.py` — `2c805242f23825bca87fdacc46bdb0c241bb5b39`
- `test_pilot_package.py` — `6726504f8ca6540cb21a4372c5035a29cd848443`

The repaired showcase is exactly SHA-256
`da2beb6df6f490c6637d5de22ce1c8fc99fafe89a2ba4b0e6c698b0544c193ff`.

## Product immutability and scope

No change from JOB08_BASE to RESULT_SHA exists under:
- `apps/learnit-next/src/**`
- `apps/learnit-next/build.py`
- `apps/learnit-next/index.template.html`
- `apps/learnit-next/source_manifest.json`
- `contracts/**`
- `authoring/**`

The only integrator-owned functional additions/changes are:
- `apps/learnit-next/tests/student_v01_fanin_b.py`
- `.github/workflows/learnit-next-ci.yml`

The RESULT tree contains no JOB08 qualification file. The qualification file is added only by the EVIDENCE_HEAD child.

## Qualification results

- Fan-in manifest identity: PASS
- 18/18 role payload blob identities: PASS
- Product immutability: PASS
- Fan-in B oracle: PASS
- Canonical V4: PASS
- Pedagogical quality: `PASS_ATLAS_PEDAGOGICAL_PROFILE_V1`
- Quality band: `EXCELLENT_BY_PROFILE`; blocking/warning/advice `0/0/0`
- Factory gate: `PASS_AI_KIT_FACTORY_V1`
- Contradictory QA: PASS
- Product/runtime regressions: PASS
- Exact repaired showcase 11/11 journey: PASS
- Desktop `1365x768`: PASS
- Mobile `390x844`: PASS
- Reload/resume/completion persistence: PASS
- Secret boundary: PASS
- Unexpected external HTTP(S): 0

Factory retained exact G3 R1 bindings:
- semantic review blob: `e9b0aa9d9b521a11cf83f9dfd741a5617124a267`
- source blob: `7f83784e8719917496a694b2ad170d724190fd04`
- context digest: `sha256:eab953d540af138f1da0b030d9cee97fdeab4060b76bfc832ab018f7abd89123`

## Deterministic repaired application

Two independent builds were byte-identical and exactly:
- bytes: `478657`
- SHA-256: `85dbeeef4207c9e4deb846d2b2e15f1e6979b1d32144ead3c1097bd5bf15630e`

## Deterministic exact integrated package

The unchanged JOB07 R2 builder produced byte-identical packages:
- bytes: `496658`
- SHA-256: `a3d3db4c63fae89b47e1d7a1341ebb522f31df69e1b107ada2ecbb9a11c4ac10`

Package integrity/manifest binding: PASS.
Extracted package browser smoke: PASS.
Accepted start mode: `DIRECT_FILE`.
The exact extracted 11-activity repaired kit completed with no external HTTP(S) request.

## Exact-head CI and repository governance

Learn-it Next CI:
- run: `35615307946`
- exact-head job: `106384356718`
- exact target: `757ed15e840bfca603de0eac3bef1e9d5ff3483d`
- conclusion: success

Repository governance:
- run: `35615307943`
- validate-repository job: `106384356177` — success
- aggregate Repository governance job: `106384411872` — success

## Audit / bounded integrator repair

The first evidence-only carrier exposed one integrator-owned CI recomposition defect: the functional scope guard rejected the authorized JOB08 qualification file on the evidence child. The failure occurred after the initial functional candidate had already passed, and did not implicate product or JOB05/JOB06/JOB07 bytes.

The correction changed only the central JOB08 CI recomposition. The final route now:
- runs the full functional matrix only when the JOB08 qualification file is absent;
- for a later evidence child, requires exactly one parent;
- requires RESULT→EVIDENCE to contain exactly `qualification/STUDENT_V01_JOB08_FANIN_B_RESULT.md`;
- requires that evidence to bind its functional parent as RESULT_SHA;
- emits only evidence-carrier PASS markers and does not restate functional PASS on EVIDENCE_HEAD.

The corrected functional candidate was fully requalified from scratch at the RESULT_SHA above.

Defect owner after repair: `NONE`.

## Rollback and gate boundary

Rollback target remains `JOB08_BASE=d5050bace4c7dcbb63dcfe44a64ef344434e9bc2` by closing PR #426 / deleting the JOB08 branch; accepted role result/evidence SHAs remain immutable.

This PASS is G4 Fan-in B exact-candidate qualification only. It authorizes preparation of JOB09 / G5 human student-readiness. It does not authorize main merge, release or real-student use.

## Verdict

`PASS_STUDENT_V01_JOB08_FANIN_B_G4_QUALIFIED_FOR_G5`
