'use strict';

const E = require('./atlas_evidence.js');

const ORACLE_VERSION = 'git:67d70e7307402242dbc1939d6cabfd87af617d74';
const EVIDENCE_ARTIFACT_DIGEST = 'sha256:6ca39dd107aea45c14cd7bec7c7ff447c36af1fc12e1c8b3f6c1a0fdc066028f';
const PACKAGE_LINEAGE_ID = 'd20ee1da-a436-43a6-9494-fa6c6ce6d0fe';
const PACKAGE_REVISION_ID = 'c79cdca8-feec-477f-87d4-c88143cbb6a5';
const PACKAGE_DIGEST = 'sha256:598ae3c56f68cbf7940334456194e08537b0f912561dbb536ec80144dfeab962';
const COURSE_LINEAGE_ID = '15e851b0-e438-48b6-b01a-a553fbcd0059';

const CONTENT_REVISION_REF = Object.freeze({
  packageLineageId: PACKAGE_LINEAGE_ID,
  packageRevisionId: PACKAGE_REVISION_ID,
  packageDigest: PACKAGE_DIGEST,
});

const COURSE_REF = Object.freeze({
  packageLineageId: PACKAGE_LINEAGE_ID,
  courseLineageId: COURSE_LINEAGE_ID,
});

function objectiveRef(objectiveId) {
  return Object.freeze({courseRef: COURSE_REF, objectiveId});
}

function activityRef(activityLineageId) {
  return Object.freeze({courseRef: COURSE_REF, activityLineageId});
}

const CLAIMS = Object.freeze([
  Object.freeze({
    claimVersion: 'atlas.independence.v1',
    claimId: 'atlas-claim-sha256:e9e466b7b14953df7f85257c03dbb9e13918cc7b649626330a838c7dda564d2f',
    objectiveRef: objectiveRef('4ae5623e-f707-49f1-b4dd-1102439b4c4a'),
    sourceActivityRef: activityRef('d2ae98fc-61fa-41f4-ac9a-95917fa9bd7e'),
    targetActivityRef: activityRef('4de1146e-c35f-4398-9a2b-8fdcb35ce987'),
    basisCode: 'new-instance',
    sourceStimulusDigest: 'sha256:7ce09a1d48dda183e71773502f91f988bb6f88dff39e5e97b7416051fb1d01c2',
    targetStimulusDigest: 'sha256:bd24eff3e978c4d59e4e40747fd3a65024517e172f8be3f19b7f7d5d6e0ff1d8',
  }),
  Object.freeze({
    claimVersion: 'atlas.independence.v1',
    claimId: 'atlas-claim-sha256:98de40e0629626f274617e4505c64e1b9737bd760a69e5c350fe78045d2b35ac',
    objectiveRef: objectiveRef('4ae5623e-f707-49f1-b4dd-1102439b4c4a'),
    sourceActivityRef: activityRef('4de1146e-c35f-4398-9a2b-8fdcb35ce987'),
    targetActivityRef: activityRef('06d208c3-00cb-46d5-a762-e462e926f4ca'),
    basisCode: 'new-context',
    sourceStimulusDigest: 'sha256:bd24eff3e978c4d59e4e40747fd3a65024517e172f8be3f19b7f7d5d6e0ff1d8',
    targetStimulusDigest: 'sha256:5fa099e094cfd9f3f0832ddd8449ef4cba35834e39bff0084dd67eac721106b2',
  }),
  Object.freeze({
    claimVersion: 'atlas.independence.v1',
    claimId: 'atlas-claim-sha256:27a295974474567c290f5c2720c675f3af47565eeb30463bf462ad67b043af1e',
    objectiveRef: objectiveRef('a42a4b0d-2ee1-4d1c-9a9e-5c3919418501'),
    sourceActivityRef: activityRef('9c36140e-ccfd-4b41-aa0c-43a81a48b833'),
    targetActivityRef: activityRef('4da38176-c283-4884-b48f-b5e6da821b0d'),
    basisCode: 'new-instance',
    sourceStimulusDigest: 'sha256:0507aed046a8bdc9cb8259c7ddc8249ab82b387f4a0b1e07666ce2f560dbac6a',
    targetStimulusDigest: 'sha256:0be94fdc878ce8f30a1f890aae683f5cd4955b46a97e11d2818e897853bceb4b',
  }),
  Object.freeze({
    claimVersion: 'atlas.independence.v1',
    claimId: 'atlas-claim-sha256:9c3fe05a3570f844cb5bf92ca38f087b981db7262acd3d7bd27494a15df2ddb4',
    objectiveRef: objectiveRef('a42a4b0d-2ee1-4d1c-9a9e-5c3919418501'),
    sourceActivityRef: activityRef('4da38176-c283-4884-b48f-b5e6da821b0d'),
    targetActivityRef: activityRef('c30cd87d-f131-418f-9bf6-681ce87de4fb'),
    basisCode: 'new-context',
    sourceStimulusDigest: 'sha256:0be94fdc878ce8f30a1f890aae683f5cd4955b46a97e11d2818e897853bceb4b',
    targetStimulusDigest: 'sha256:ca0426b85a3e925b5006ea53fd9a098f6f214beb875bb5f55fa4298976b8ea99',
  }),
]);

const ACCEPTED_CLAIM_IDS = Object.freeze(
  CLAIMS.map(claim => claim.claimId).slice().sort(),
);

const ACCEPTED_CLAIM_SET = Object.freeze({
  schemaVersion: 'atlas.accepted-validation-claims.v1',
  contentRevisionRef: CONTENT_REVISION_REF,
  oracleVersion: ORACLE_VERSION,
  artifactDigest: EVIDENCE_ARTIFACT_DIGEST,
  acceptedClaimIds: ACCEPTED_CLAIM_IDS,
});

for (const claim of CLAIMS) {
  E.assertClaim(claim);
}
E.assertAcceptedClaimSet(ACCEPTED_CLAIM_SET, {
  contentRevisionRef: CONTENT_REVISION_REF,
  oracleVersion: ORACLE_VERSION,
  artifactDigest: EVIDENCE_ARTIFACT_DIGEST,
});

function sameContentRevision(ref) {
  try {
    return E.canonicalJson(ref) === E.canonicalJson(CONTENT_REVISION_REF);
  } catch (_) {
    return false;
  }
}

function contextAccepted(context) {
  return Boolean(
    context
    && context.packageLineageId === PACKAGE_LINEAGE_ID
    && context.packageRevisionId === PACKAGE_REVISION_ID
    && context.packageDigest === PACKAGE_DIGEST
    && context.course?.courseLineageId === COURSE_LINEAGE_ID
  );
}

function claimsForContext(context) {
  return contextAccepted(context) ? CLAIMS : Object.freeze([]);
}

function targetsForBasis({context, objectiveRef: objective, sourceActivityRef}) {
  return Object.freeze(
    claimsForContext(context)
      .filter(claim => (
        E.sameRef(claim.objectiveRef, objective)
        && E.sameRef(claim.sourceActivityRef, sourceActivityRef)
      ))
      .map(claim => Object.freeze({
        claimId: claim.claimId,
        targetActivityRef: claim.targetActivityRef,
      })),
  );
}

function validateRuntimeClaim(planItem, details) {
  if (!planItem || !details || !sameContentRevision(details.contentRevisionRef)) return false;
  const claim = CLAIMS.find(candidate => candidate.claimId === details.independenceClaimId);
  if (!claim || planItem.independenceClaimId !== claim.claimId) return false;
  return E.sameRef(claim.objectiveRef, details.objectiveRef)
    && E.sameRef(claim.sourceActivityRef, details.sourceActivityRef)
    && E.sameRef(claim.targetActivityRef, details.targetActivityRef)
    && E.claimIsAccepted({
      claim,
      acceptedClaimSet: ACCEPTED_CLAIM_SET,
      contentRevisionRef: CONTENT_REVISION_REF,
      artifactDigest: EVIDENCE_ARTIFACT_DIGEST,
      oracleVersion: ORACLE_VERSION,
      sourceActivityRef: details.sourceActivityRef,
      targetActivityRef: details.targetActivityRef,
      objectiveRef: details.objectiveRef,
    });
}

module.exports = Object.freeze({
  ORACLE_VERSION,
  EVIDENCE_ARTIFACT_DIGEST,
  CONTENT_REVISION_REF,
  COURSE_REF,
  CLAIMS,
  ACCEPTED_CLAIM_IDS,
  ACCEPTED_CLAIM_SET,
  sameContentRevision,
  contextAccepted,
  claimsForContext,
  targetsForBasis,
  validateRuntimeClaim,
});
