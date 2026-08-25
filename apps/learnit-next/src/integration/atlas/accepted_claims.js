const EVIDENCE_ORACLE_VERSION = 'git:67d70e7307402242dbc1939d6cabfd87af617d74';
const EVIDENCE_ARTIFACT_DIGEST = 'sha256:6ca39dd107aea45c14cd7bec7c7ff447c36af1fc12e1c8b3f6c1a0fdc066028f';

const EVIDENCE_CONTENT_REVISION = Object.freeze({
  packageLineageId: 'd20ee1da-a436-43a6-9494-fa6c6ce6d0fe',
  packageRevisionId: 'c79cdca8-feec-477f-87d4-c88143cbb6a5',
  packageDigest: 'sha256:598ae3c56f68cbf7940334456194e08537b0f912561dbb536ec80144dfeab962',
});

const ACCEPTED_CLAIM_IDS = Object.freeze([
  'atlas-claim-sha256:27a295974474567c290f5c2720c675f3af47565eeb30463bf462ad67b043af1e',
  'atlas-claim-sha256:98de40e0629626f274617e4505c64e1b9737bd760a69e5c350fe78045d2b35ac',
  'atlas-claim-sha256:9c3fe05a3570f844cb5bf92ca38f087b981db7262acd3d7bd27494a15df2ddb4',
  'atlas-claim-sha256:e9e466b7b14953df7f85257c03dbb9e13918cc7b649626330a838c7dda564d2f',
]);

const ACCEPTED_CLAIM_SET = Object.freeze({
  schemaVersion: 'atlas.accepted-validation-claims.v1',
  contentRevisionRef: EVIDENCE_CONTENT_REVISION,
  oracleVersion: EVIDENCE_ORACLE_VERSION,
  artifactDigest: EVIDENCE_ARTIFACT_DIGEST,
  acceptedClaimIds: ACCEPTED_CLAIM_IDS,
});

function sameRevision(context) {
  return Boolean(
    context
    && context.packageLineageId === EVIDENCE_CONTENT_REVISION.packageLineageId
    && context.packageRevisionId === EVIDENCE_CONTENT_REVISION.packageRevisionId
    && context.packageDigest === EVIDENCE_CONTENT_REVISION.packageDigest
  );
}

function courseRef(context) {
  return Object.freeze({
    packageLineageId: context.packageLineageId,
    courseLineageId: context.course.courseLineageId,
  });
}

function qualifyClaim(context, source) {
  const ref = courseRef(context);
  return Object.freeze({
    claimVersion: source.claimVersion,
    claimId: source.claimId,
    objectiveRef: Object.freeze({
      courseRef: ref,
      objectiveId: source.objectiveId,
    }),
    sourceActivityRef: Object.freeze({
      courseRef: ref,
      activityLineageId: source.sourceActivityLineageId,
    }),
    targetActivityRef: Object.freeze({
      courseRef: ref,
      activityLineageId: source.targetActivityLineageId,
    }),
    basisCode: source.basisCode,
    sourceStimulusDigest: source.sourceStimulusDigest,
    targetStimulusDigest: source.targetStimulusDigest,
  });
}

export function acceptedClaimEvidence() {
  return Object.freeze({
    oracleVersion: EVIDENCE_ORACLE_VERSION,
    evidenceArtifactDigest: EVIDENCE_ARTIFACT_DIGEST,
    contentRevisionRef: EVIDENCE_CONTENT_REVISION,
    acceptedClaimSet: ACCEPTED_CLAIM_SET,
  });
}

export function acceptedClaimsForContext(context, evidenceModule) {
  if (!sameRevision(context)) return Object.freeze([]);
  if (!evidenceModule || typeof evidenceModule.claimIsAccepted !== 'function') {
    throw new Error('ATLAS_M2_CLAIM_EVIDENCE_MODULE_REQUIRED');
  }

  const sourceClaims = context.course.atlasValidationIndependenceClaims;
  if (!Array.isArray(sourceClaims)) return Object.freeze([]);

  const accepted = [];
  for (const source of sourceClaims) {
    if (!source || !ACCEPTED_CLAIM_IDS.includes(source.claimId)) continue;
    const claim = qualifyClaim(context, source);
    const valid = evidenceModule.claimIsAccepted({
      claim,
      acceptedClaimSet: ACCEPTED_CLAIM_SET,
      contentRevisionRef: EVIDENCE_CONTENT_REVISION,
      artifactDigest: EVIDENCE_ARTIFACT_DIGEST,
      oracleVersion: EVIDENCE_ORACLE_VERSION,
      sourceActivityRef: claim.sourceActivityRef,
      targetActivityRef: claim.targetActivityRef,
      objectiveRef: claim.objectiveRef,
    });
    if (valid) accepted.push(claim);
  }

  accepted.sort((left, right) => left.claimId.localeCompare(right.claimId));
  return Object.freeze(accepted);
}

export function findAcceptedClaim({
  context,
  evidenceModule,
  objectiveRef,
  sourceActivityRef,
  targetActivityRef,
  claimId = null,
}) {
  const claims = acceptedClaimsForContext(context, evidenceModule);
  const same = (left, right) => evidenceModule.sameRef(left, right);

  return claims.find(claim => (
    (!claimId || claim.claimId === claimId)
    && same(claim.objectiveRef, objectiveRef)
    && same(claim.sourceActivityRef, sourceActivityRef)
    && same(claim.targetActivityRef, targetActivityRef)
  )) ?? null;
}

export const ATLAS_M2_ACCEPTED_CLAIM_IDS = ACCEPTED_CLAIM_IDS;
