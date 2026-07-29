import {
  atlasElement,
  getAtlasActionPresentation,
  normalizeAtlasSessionPlan,
  renderAtlasReasonList,
} from './atlas_today.js';

const PHASE_PRESENTATION = Object.freeze({
  practice: Object.freeze({
    label: 'Entraînement',
    description: 'Cette étape sert à essayer et à progresser.',
  }),
  correction: Object.freeze({
    label: 'Correction',
    description: 'Cette étape sert à comprendre puis corriger une erreur. Elle reste distincte d’une validation.',
  }),
  validation: Object.freeze({
    label: 'Validation',
    description: 'Cette étape est distincte de l’entraînement et de la correction.',
  }),
  maintenance: Object.freeze({
    label: 'Entretien',
    description: 'Cette étape entretient une validation récente sans conclusion supplémentaire.',
  }),
});

export const ATLAS_SESSION_PHASES = Object.freeze(Object.keys(PHASE_PRESENTATION));

function requireDocument(documentRef) {
  if (!documentRef || typeof documentRef.createElement !== 'function') {
    throw new TypeError('Un document DOM est requis pour générer la séance Atlas.');
  }
  return documentRef;
}

function requiredText(value, fieldName) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new TypeError(`${fieldName} doit être une chaîne non vide.`);
  }
  return value.trim();
}

function labelFromMap(labelsById, identifier) {
  if (labelsById instanceof Map) return labelsById.get(identifier) ?? identifier;
  if (labelsById && typeof labelsById === 'object' && !Array.isArray(labelsById)) {
    return labelsById[identifier] ?? identifier;
  }
  return identifier;
}

function phasePresentation(action) {
  const phase = getAtlasActionPresentation(action).phase;
  const presentation = PHASE_PRESENTATION[phase];
  if (!presentation) throw new RangeError(`Phase Atlas non prise en charge : ${phase}`);
  return { phase, ...presentation };
}

export function getAtlasSessionPhase(action) {
  return phasePresentation(action);
}

function normalizeSessionData(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new TypeError('La séance guidée doit recevoir un objet data.');
  }
  const plan = normalizeAtlasSessionPlan(data.plan);
  if (plan.items.length === 0) {
    throw new TypeError('Une séance guidée doit contenir au moins une étape.');
  }
  if (!Number.isInteger(data.activeIndex) || data.activeIndex < 0 || data.activeIndex >= plan.items.length) {
    throw new RangeError('activeIndex doit désigner une étape existante du plan.');
  }
  return {
    sessionId: requiredText(data.sessionId, 'sessionId'),
    plan,
    activeIndex: data.activeIndex,
  };
}

function renderStepRail(documentRef, plan, activeIndex, options) {
  const list = atlasElement(documentRef, 'ol', {
    className: 'atlas-session__rail',
    'aria-label': 'Étapes de la séance',
  });
  for (const item of plan.items) {
    const index = item.position - 1;
    const phase = phasePresentation(item.action);
    const current = index === activeIndex;
    const completed = index < activeIndex;
    list.appendChild(atlasElement(documentRef, 'li', {
      className: [
        'atlas-session__rail-item',
        `atlas-session__rail-item--${phase.phase}`,
        current ? 'is-current' : '',
        completed ? 'is-completed' : '',
      ].filter(Boolean).join(' '),
      'aria-current': current ? 'step' : null,
      'data-position': item.position,
      'data-phase': phase.phase,
    }, [
      atlasElement(documentRef, 'span', {
        className: 'atlas-session__rail-number',
        text: String(item.position),
        'aria-hidden': 'true',
      }),
      atlasElement(documentRef, 'span', {
        className: 'atlas-session__rail-label',
        text: labelFromMap(options.objectiveLabelsById, item.objectiveId),
      }),
    ]));
  }
  return list;
}

function renderActivitySurface(documentRef, item, session, options) {
  const activityTitle = labelFromMap(options.activityLabelsById, item.activityLineageId);
  const region = atlasElement(documentRef, 'section', {
    className: 'atlas-session__activity',
    'aria-label': `Activité : ${activityTitle}`,
    'data-activity-lineage-id': item.activityLineageId,
  });
  if (typeof options.renderActivity === 'function') {
    const rendered = options.renderActivity({
      sessionId: session.sessionId,
      planId: session.plan.planId,
      activeIndex: session.activeIndex,
      item: { ...item, reasonCodes: [...item.reasonCodes] },
    });
    if (rendered !== null && rendered !== undefined) {
      if (typeof rendered !== 'object' || typeof rendered.setAttribute !== 'function') {
        throw new TypeError('renderActivity doit retourner un nœud DOM ou null.');
      }
      region.appendChild(rendered);
      return region;
    }
  }
  region.appendChild(atlasElement(documentRef, 'div', {
    className: 'atlas-session__activity-placeholder',
    role: 'status',
  }, [
    atlasElement(documentRef, 'strong', { text: activityTitle }),
    atlasElement(documentRef, 'p', {
      text: 'Le composant d’activité sera fourni par l’intégration sans modifier ce plan.',
    }),
  ]));
  return region;
}

function renderControls(documentRef, session, options) {
  const last = session.activeIndex === session.plan.items.length - 1;
  const controls = atlasElement(documentRef, 'div', {
    className: 'atlas-session__controls',
    role: 'group',
    'aria-label': 'Commandes de la séance',
  });
  const previous = atlasElement(documentRef, 'button', {
    className: 'atlas-button atlas-button--secondary',
    type: 'button',
    disabled: session.activeIndex === 0,
    'aria-disabled': session.activeIndex === 0 ? 'true' : 'false',
    text: 'Étape précédente',
  });
  if (typeof options.onPrevious === 'function') {
    previous.addEventListener('click', () => {
      if (session.activeIndex > 0) options.onPrevious(session.activeIndex - 1);
    });
  }
  const interrupt = atlasElement(documentRef, 'button', {
    className: 'atlas-button atlas-button--quiet',
    type: 'button',
    text: 'Interrompre et reprendre plus tard',
  });
  if (typeof options.onInterrupt === 'function') {
    interrupt.addEventListener('click', () => options.onInterrupt({
      sessionId: session.sessionId,
      planId: session.plan.planId,
      activeIndex: session.activeIndex,
    }));
  }
  const next = atlasElement(documentRef, 'button', {
    className: 'atlas-button atlas-button--primary',
    type: 'button',
    text: last ? 'Terminer et voir le bilan' : 'Étape suivante',
  });
  if (last && typeof options.onComplete === 'function') {
    next.addEventListener('click', () => options.onComplete({
      sessionId: session.sessionId,
      planId: session.plan.planId,
    }));
  } else if (!last && typeof options.onNext === 'function') {
    next.addEventListener('click', () => options.onNext(session.activeIndex + 1));
  }
  controls.appendChild(previous);
  controls.appendChild(interrupt);
  controls.appendChild(next);
  return controls;
}

export function renderAtlasGuidedSession(data, options = {}) {
  const documentRef = requireDocument(options.documentRef ?? globalThis.document);
  const session = normalizeSessionData(data);
  const item = session.plan.items[session.activeIndex];
  const phase = phasePresentation(item.action);
  const objectiveLabel = labelFromMap(options.objectiveLabelsById, item.objectiveId);
  const titleId = 'atlas-session-title';
  const section = atlasElement(documentRef, 'section', {
    className: `atlas-session atlas-session--${phase.phase}`,
    'aria-labelledby': titleId,
    'data-session-id': session.sessionId,
    'data-plan-id': session.plan.planId,
    'data-active-index': session.activeIndex,
    'data-phase': phase.phase,
  }, [
    atlasElement(documentRef, 'header', { className: 'atlas-session__header' }, [
      atlasElement(documentRef, 'div', {}, [
        atlasElement(documentRef, 'p', {
          className: 'atlas-kicker',
          text: `Étape ${item.position} sur ${session.plan.items.length}`,
        }),
        atlasElement(documentRef, 'h2', { id: titleId, text: objectiveLabel }),
      ]),
      atlasElement(documentRef, 'div', { className: 'atlas-session__phase' }, [
        atlasElement(documentRef, 'strong', { text: phase.label }),
        atlasElement(documentRef, 'span', { text: `${item.estimatedMinutes} min` }),
      ]),
    ]),
    atlasElement(documentRef, 'p', {
      className: 'atlas-session__phase-description',
      text: phase.description,
    }),
    renderStepRail(documentRef, session.plan, session.activeIndex, options),
    atlasElement(documentRef, 'aside', {
      className: 'atlas-session__why',
      'aria-label': 'Pourquoi cette étape',
    }, [
      atlasElement(documentRef, 'h3', { text: 'Pourquoi maintenant ?' }),
      renderAtlasReasonList(item.reasonCodes, {
        documentRef,
        ariaLabel: 'Raisons de cette étape',
      }),
    ]),
    renderActivitySurface(documentRef, item, session, options),
    renderControls(documentRef, session, options),
  ]);
  return section;
}
