import { atlasElement } from './atlas_today.js';

const REWARD_PRESENTATION = Object.freeze({
  'correction-completed': Object.freeze({
    title: 'Erreur comprise et corrigée',
    description: 'Une correction a été terminée. Elle reste distincte d’une validation.',
    icon: '↺',
  }),
  'independent-success': Object.freeze({
    title: 'Réussite autonome',
    description: 'Une activité a été réussie sans aide déclarée.',
    icon: '✓',
  }),
  'validation-completed': Object.freeze({
    title: 'Validation distincte réussie',
    description: 'Une activité de validation séparée a été réussie.',
    icon: '◇',
  }),
  'resumed-after-interruption': Object.freeze({
    title: 'Séance reprise',
    description: 'Une séance interrompue a été reprise sans perdre sa continuité.',
    icon: '→',
  }),
  'transfer-completed': Object.freeze({
    title: 'Application dans un autre contexte',
    description: 'Une tâche de transfert déclarée a été réalisée.',
    icon: '↗',
  }),
});

const FORBIDDEN_REWARD_FIELDS = Object.freeze([
  'clickCount',
  'elapsedMinutes',
  'points',
  'coins',
  'currency',
  'rank',
  'leaderboard',
  'streak',
  'loot',
  'randomValue',
]);

export const ATLAS_PEDAGOGICAL_REWARD_KINDS = Object.freeze(Object.keys(REWARD_PRESENTATION));

function requireDocument(documentRef) {
  if (!documentRef || typeof documentRef.createElement !== 'function') {
    throw new TypeError('Un document DOM est requis pour générer les récompenses Atlas.');
  }
  return documentRef;
}

function requiredText(value, fieldName) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new TypeError(`${fieldName} doit être une chaîne non vide.`);
  }
  return value.trim();
}

function positiveInteger(value, fieldName) {
  if (!Number.isInteger(value) || value <= 0) {
    throw new TypeError(`${fieldName} doit être un entier strictement positif.`);
  }
  return value;
}

function labelFromMap(labelsById, identifier) {
  if (labelsById instanceof Map) return labelsById.get(identifier) ?? identifier;
  if (labelsById && typeof labelsById === 'object' && !Array.isArray(labelsById)) {
    return labelsById[identifier] ?? identifier;
  }
  return identifier;
}

export function normalizeAtlasReward(reward) {
  if (!reward || typeof reward !== 'object' || Array.isArray(reward)) {
    throw new TypeError('Une récompense Atlas doit être un objet data.');
  }
  for (const field of FORBIDDEN_REWARD_FIELDS) {
    if (Object.hasOwn(reward, field)) {
      throw new TypeError(`Champ de récompense non pédagogique interdit : ${field}`);
    }
  }
  const kind = requiredText(reward.kind, 'reward.kind');
  if (!Object.hasOwn(REWARD_PRESENTATION, kind)) {
    throw new RangeError(`Type de récompense Atlas non pris en charge : ${kind}`);
  }
  if (!Array.isArray(reward.evidenceEventIds) || reward.evidenceEventIds.length === 0) {
    throw new TypeError('reward.evidenceEventIds doit être un tableau non vide.');
  }
  const evidenceEventIds = reward.evidenceEventIds.map((value, index) => (
    requiredText(value, `reward.evidenceEventIds[${index}]`)
  ));
  if (new Set(evidenceEventIds).size !== evidenceEventIds.length) {
    throw new TypeError('reward.evidenceEventIds ne doit pas contenir de doublon.');
  }
  const objectiveId = reward.objectiveId === null || reward.objectiveId === undefined
    ? null
    : requiredText(reward.objectiveId, 'reward.objectiveId');
  if (kind !== 'resumed-after-interruption' && objectiveId === null) {
    throw new TypeError(`reward.objectiveId est requis pour ${kind}.`);
  }
  return {
    rewardId: requiredText(reward.rewardId, 'reward.rewardId'),
    rewardVersion: positiveInteger(reward.rewardVersion, 'reward.rewardVersion'),
    kind,
    objectiveId,
    occurredAt: requiredText(reward.occurredAt, 'reward.occurredAt'),
    evidenceEventIds,
  };
}

export function getAtlasRewardPresentation(kind) {
  const normalized = requiredText(kind, 'kind');
  const presentation = REWARD_PRESENTATION[normalized];
  if (!presentation) throw new RangeError(`Type de récompense Atlas non pris en charge : ${normalized}`);
  return presentation;
}

export function renderAtlasReward(reward, options = {}) {
  const documentRef = requireDocument(options.documentRef ?? globalThis.document);
  const data = normalizeAtlasReward(reward);
  const presentation = getAtlasRewardPresentation(data.kind);
  const card = atlasElement(documentRef, 'article', {
    className: `atlas-reward atlas-reward--${data.kind}`,
    'data-reward-id': data.rewardId,
    'data-reward-kind': data.kind,
    'data-reward-origin': 'provided-evidence',
  }, [
    atlasElement(documentRef, 'span', {
      className: 'atlas-reward__icon',
      text: presentation.icon,
      'aria-hidden': 'true',
    }),
    atlasElement(documentRef, 'div', { className: 'atlas-reward__content' }, [
      atlasElement(documentRef, 'h3', { text: presentation.title }),
      atlasElement(documentRef, 'p', { text: presentation.description }),
    ]),
  ]);
  if (data.objectiveId) {
    card.appendChild(atlasElement(documentRef, 'p', {
      className: 'atlas-reward__objective',
      text: `Objectif : ${labelFromMap(options.objectiveLabelsById, data.objectiveId)}`,
    }));
  }
  return card;
}

export function renderAtlasRewards(rewards, options = {}) {
  const documentRef = requireDocument(options.documentRef ?? globalThis.document);
  if (!Array.isArray(rewards)) throw new TypeError('rewards doit être un tableau.');
  const normalized = rewards.map(normalizeAtlasReward);
  const identifiers = normalized.map((reward) => reward.rewardId);
  if (new Set(identifiers).size !== identifiers.length) {
    throw new TypeError('rewards ne doit pas contenir deux fois le même rewardId.');
  }
  const titleId = options.titleId ?? 'atlas-rewards-title';
  const section = atlasElement(documentRef, 'section', {
    className: 'atlas-rewards',
    'aria-labelledby': titleId,
  }, [
    atlasElement(documentRef, 'div', { className: 'atlas-section-heading' }, [
      atlasElement(documentRef, 'p', { className: 'atlas-kicker', text: 'Étapes utiles' }),
      atlasElement(documentRef, 'h2', {
        id: titleId,
        text: options.title ?? 'Ce qui mérite d’être reconnu',
      }),
    ]),
    atlasElement(documentRef, 'p', {
      className: 'atlas-rewards__boundary',
      text: 'Ces repères reconnaissent des preuves pédagogiques précises. Ils ne créent ni score ni compétition.',
    }),
  ]);
  if (normalized.length === 0) {
    section.appendChild(atlasElement(documentRef, 'p', {
      className: 'atlas-rewards__empty',
      role: 'status',
      text: 'Aucun nouveau repère pédagogique pour cette séance.',
    }));
    return section;
  }
  const list = atlasElement(documentRef, 'div', { className: 'atlas-rewards__list' });
  for (const reward of normalized) {
    list.appendChild(renderAtlasReward(reward, {
      documentRef,
      objectiveLabelsById: options.objectiveLabelsById,
    }));
  }
  section.appendChild(list);
  return section;
}
