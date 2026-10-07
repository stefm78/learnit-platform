# Atlas Independent Kit Review V6 — PASSAGE release path

Status: candidate reviewer skill for `atlas.semantic-review.v6-r1`.

Review in an independent context: do not reuse author scratchpad or active author reasoning. Bind the review target exactly to `contextDigest`, `kitSha256`, `sourceSetDigest`, and `briefSha256`. A target mismatch is a HOLD.

Review all six core dimensions: `sourceFidelity`, `answerCorrectness`, `ambiguity`, `objectiveCoverage`, `validationTransfer`, and `learnerFit`. Blocking or major findings prevent PASS. Evidence for material claims must map to an authorized Role B source and declared claim identifier. If learner-facing Role A references exist, verify that they are useful and supplemental rather than hidden source truth.

Record exactly these V6 checks: `reviewerSkill`, `hintProgression`, `hintAnswerLeak`, `roleAReferenceUsefulness`, `roleBClaimMapping`, `productiveCorrectness`, and `visualAdequacy`. The first five are `pass|hold`; `productiveCorrectness` and `visualAdequacy` are `pass|hold|not_applicable`. `productiveCorrectness` must be `pass` when any productive activity exists.

For `visualAdequacy`, use `not_applicable` only when no objective/activity materially requires interpretation of a visual representation. Use `pass` only when the exact embedded media is pedagogically faithful and sufficient. Use `hold` when a graph, diagram, image, geometry, circuit, schema, or other material visual has been silently reduced to text or is misleading/inadequate. Decorative media never improves the verdict.
