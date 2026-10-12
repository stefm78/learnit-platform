# Atlas Independent Kit Review V6 — PASSAGE release path

Status: candidate reviewer skill for `atlas.semantic-review.v6-r2`.

Review in an independent context: do not reuse author scratchpad or active author reasoning. Bind the review target exactly to `contextDigest`, `kitSha256`, `sourceSetDigest`, and `briefSha256`. A target mismatch is a HOLD. Reviews under `atlas.semantic-review.v6-r1` are stale for this profile and cannot PASS the current Factory.

Review all six core dimensions: `sourceFidelity`, `answerCorrectness`, `ambiguity`, `objectiveCoverage`, `validationTransfer`, and `learnerFit`. Blocking or major findings prevent PASS. Evidence for material claims must map to an authorized Role B source and declared claim identifier. If learner-facing Role A references exist, verify that they are useful and supplemental rather than hidden source truth.

For `learnerFit`, review the exact confirmed `learningIntent` in the learner brief, not an inferred replacement. Compare candidate kit objectives to `learningIntent.objectiveScope`: unexplained objective addition, removal, or material semantic drift is a HOLD and may also affect `objectiveCoverage`. Challenge fit to `priorKnowledge`, `timeBudgetMinutes`, and the selected mode. A mode/profile mismatch is a HOLD.

Apply mode-specific falsification. For `DISCOVERY`, HOLD when dense material is front-loaded without appropriate segmentation/scaffolding or when independent validation is not genuinely independent. For `REVISION`, HOLD when the path mainly replays exposition instead of retrieval/application and targeted remediation. For `EXAM`, HOLD on answer-revealing hints before assessed responses or certification/grade claims. For `EXPLORATION`, HOLD when selective exploration is presented as exhaustive mastery or exam readiness. For `COMPLETE`, HOLD when a scope that cannot reasonably fit the time budget is silently compressed instead of being split/re-scoped before authoring.

Record exactly these V6 checks: `reviewerSkill`, `hintProgression`, `hintAnswerLeak`, `roleAReferenceUsefulness`, `roleBClaimMapping`, `productiveCorrectness`, and `visualAdequacy`. The first five are `pass|hold`; `productiveCorrectness` and `visualAdequacy` are `pass|hold|not_applicable`. `productiveCorrectness` must be `pass` when any productive activity exists. The review schema remains `learnit.atlas.semantic_review.v3`; PASS/HOLD identities are `PASS_SEMANTIC_REVIEW_V6_R2` and `HOLD_SEMANTIC_REVIEW_V6_R2`.

For `visualAdequacy`, use `not_applicable` only when no objective/activity materially requires interpretation of a visual representation. Use `pass` only when the exact embedded media is pedagogically faithful and sufficient. Use `hold` when a graph, diagram, image, geometry, circuit, schema, or other material visual has been silently reduced to text or is misleading/inadequate. Decorative media never improves the verdict.
