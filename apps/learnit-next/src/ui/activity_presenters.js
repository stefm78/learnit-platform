import { renderEmbeddedMediaSet } from './media.js';

let sequence = 0;
const uid = prefix => `${prefix}-${++sequence}`;

function el(tag, attrs = {}, children = []) {
  const out = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value == null) continue;
    if (name === 'className') out.className = value;
    else if (name === 'text') out.textContent = String(value);
    else if (name === 'disabled') out.disabled = Boolean(value);
    else if (name === 'value') out.value = String(value);
    else out.setAttribute(name, String(value));
  }
  for (const child of (Array.isArray(children) ? children : [children])) {
    if (child == null) continue;
    out.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return out;
}

function required(message) {
  const error = new Error(message);
  error.code = 'ACTIVITY_RESPONSE_REQUIRED';
  return error;
}

function shell(presentation, children) {
  const root = el('section', {
    className: `activity-presentation activity-presentation-${presentation.type}`,
    'data-activity-presentation': presentation.type,
  }, children);
  if (presentation.media?.length) root.append(renderEmbeddedMediaSet(presentation.media));
  return root;
}

const prompt = text => el('p', { className: 'atlas-question activity-prompt' }, [el('strong', { text })]);

function qcm(presentation) {
  const fieldset = el('fieldset', { className: 'answer-fieldset' }, [el('legend', { text: 'Choisissez une réponse' })]);
  const name = uid('activity-qcm');
  presentation.choices.forEach((choice, index) => {
    const id = uid(`activity-qcm-choice-${index}`);
    fieldset.append(el('label', { className: 'choice-row', for: id }, [
      el('input', { id, type: 'radio', name, value: choice.choiceId, 'data-activity-choice': 'true' }),
      el('span', { text: choice.label }),
    ]));
  });
  return shell(presentation, [prompt(presentation.prompt), fieldset]);
}

function fill(presentation) {
  const sentence = el('div', { className: 'fill-sentence activity-fill-sentence' });
  let number = 0;
  for (const segment of presentation.segments) {
    if (Object.hasOwn(segment, 'text')) {
      sentence.append(el('span', { text: segment.text }));
      continue;
    }
    number += 1;
    const select = el('select', {
      'data-activity-slot': segment.slotId,
      'aria-label': `Réponse ${number}`,
    }, [el('option', { value: '', text: 'Choisir…' })]);
    presentation.tokens.forEach(token => select.append(el('option', { value: token.tokenId, text: token.label })));
    sentence.append(el('label', { className: 'atlas-fill-slot activity-fill-slot' }, [
      el('span', { className: 'visually-hidden sr-only', text: `Réponse ${number}` }), select,
    ]));
  }
  return shell(presentation, [
    prompt(presentation.prompt),
    el('fieldset', { className: 'answer-fieldset' }, [el('legend', { text: 'Complétez la phrase' }), sentence]),
  ]);
}

function lesson(presentation) {
  const body = el('div', { className: 'activity-lesson-body' });
  String(presentation.body || '').split(/\n\s*\n/).map(item => item.trim()).filter(Boolean)
    .forEach(item => body.append(el('p', { text: item })));
  const card = el('div', { className: 'activity-learning-card' }, [
    el('p', { className: 'activity-kind', text: 'À retenir' }), el('h2', { text: presentation.title }), body,
  ]);
  if (presentation.keyPoints?.length) card.append(el('section', { className: 'activity-key-points', 'aria-label': 'Points clés' }, [
    el('h3', { text: 'Points clés' }), el('ul', {}, presentation.keyPoints.map(item => el('li', { text: item }))),
  ]));
  if (presentation.contextNote?.trim()) card.append(el('aside', { className: 'activity-context-note', 'aria-label': 'Contexte' }, [
    el('strong', { text: 'Contexte' }), el('p', { text: presentation.contextNote.trim() }),
  ]));
  const button = el('button', { type: 'button', className: 'atlas-primary activity-continue', text: 'Continuer', 'data-activity-continue': 'lesson' });
  const root = shell(presentation, [card, el('div', { className: 'activity-local-actions' }, [button])]);
  button.addEventListener('click', () => {
    root.dataset.activityReady = 'true'; button.disabled = true; button.textContent = 'Prêt à continuer';
  });
  return root;
}

function flashcard(presentation) {
  const revealRegion = el('div', { className: 'activity-flashcard-reveal-region', 'aria-live': 'polite' });
  const reveal = el('button', { type: 'button', className: 'secondary', text: 'Afficher la réponse', 'data-flashcard-reveal': 'true' });
  const next = el('button', { type: 'button', className: 'atlas-primary', text: 'Continuer', disabled: true, 'data-activity-continue': 'flashcard' });
  const root = shell(presentation, [el('article', { className: 'activity-flashcard' }, [
    el('p', { className: 'activity-kind', text: 'Carte de rappel' }),
    el('div', { className: 'activity-flashcard-front' }, [el('p', { text: presentation.front })]),
    revealRegion, el('div', { className: 'activity-local-actions' }, [reveal, next]),
  ])]);
  reveal.addEventListener('click', () => {
    if (root.dataset.flashcardRevealed === 'true') return;
    revealRegion.replaceChildren(el('div', { className: 'activity-flashcard-back', 'data-flashcard-back': 'true' }, [
      el('p', { className: 'activity-flashcard-answer', text: presentation.back }),
      el('p', { className: 'activity-flashcard-explanation', text: presentation.explanation }),
    ]));
    root.dataset.flashcardRevealed = 'true'; reveal.disabled = true; reveal.textContent = 'Réponse affichée'; next.disabled = false; next.focus();
  });
  next.addEventListener('click', () => {
    if (root.dataset.flashcardRevealed !== 'true') return;
    root.dataset.activityReady = 'true'; next.disabled = true; next.textContent = 'Prêt à continuer';
  });
  return root;
}

function associations(root) {
  return new Map([...root.querySelectorAll('[data-matching-association]')]
    .map(item => [item.dataset.leftItemId, item.dataset.rightItemId]));
}

function paintMatching(root, presentation, selected) {
  const map = associations(root);
  const list = root.querySelector('[data-matching-associations]');
  list.replaceChildren(...presentation.leftItems.flatMap(left => {
    const right = presentation.rightItems.find(item => item.itemId === map.get(left.itemId));
    return right ? [el('li', {
      'data-matching-association': 'true', 'data-left-item-id': left.itemId, 'data-right-item-id': right.itemId,
    }, [el('span', { text: left.label }), el('span', { className: 'activity-association-arrow', 'aria-hidden': 'true', text: '→' }), el('span', { text: right.label })])] : [];
  }));
  root.querySelectorAll('[data-matching-left]').forEach(button => {
    const active = button.dataset.matchingLeft === selected;
    button.setAttribute('aria-pressed', String(active)); button.classList.toggle('is-selected', active);
  });
  root.querySelectorAll('[data-matching-right]').forEach(button => {
    const used = [...map.values()].includes(button.dataset.matchingRight);
    button.dataset.associated = String(used); button.classList.toggle('is-associated', used);
  });
  root.querySelector('[data-matching-status]').textContent = selected
    ? 'Élément de gauche sélectionné. Choisissez maintenant un élément de droite.'
    : `${map.size} association${map.size > 1 ? 's' : ''} créée${map.size > 1 ? 's' : ''}.`;
}

function matching(presentation) {
  let selected = null;
  const pool = (items, side) => el('div', { className: 'activity-choice-pool', role: 'group', 'aria-label': side === 'left' ? 'Éléments de gauche' : 'Éléments de droite' },
    items.map(item => el('button', { type: 'button', className: 'activity-pool-button', text: item.label, [`data-matching-${side}`]: item.itemId, ...(side === 'left' ? { 'aria-pressed': 'false' } : { 'data-associated': 'false' }) })));
  const list = el('ul', { className: 'activity-association-list', 'data-matching-associations': 'true' });
  const status = el('p', { className: 'activity-interaction-status', role: 'status', 'aria-live': 'polite', 'data-matching-status': 'true', text: 'Sélectionnez un élément de gauche puis un élément de droite.' });
  const root = shell(presentation, [
    prompt(presentation.prompt),
    el('div', { className: 'activity-matching-pools' }, [
      el('section', {}, [el('h3', { text: 'À associer' }), pool(presentation.leftItems, 'left')]),
      el('section', {}, [el('h3', { text: 'Correspondances' }), pool(presentation.rightItems, 'right')]),
    ]),
    el('section', { className: 'activity-current-associations', 'aria-label': 'Associations actuelles' }, [el('h3', { text: 'Associations créées' }), list]), status,
  ]);
  root.addEventListener('click', event => {
    const left = event.target.closest?.('[data-matching-left]');
    if (left && root.contains(left)) { selected = left.dataset.matchingLeft; paintMatching(root, presentation, selected); return; }
    const right = event.target.closest?.('[data-matching-right]');
    if (!right || !root.contains(right) || !selected) return;
    const map = associations(root);
    for (const [leftId, rightId] of [...map]) if (leftId === selected || rightId === right.dataset.matchingRight) map.delete(leftId);
    map.set(selected, right.dataset.matchingRight);
    list.replaceChildren(...[...map].map(([leftId, rightId]) => el('li', { 'data-matching-association': 'true', 'data-left-item-id': leftId, 'data-right-item-id': rightId })));
    selected = null; paintMatching(root, presentation, selected);
  });
  return root;
}

function order(presentation) {
  const list = el('ol', { className: 'activity-order-list', 'data-order-list': 'true' });
  const update = () => [...list.querySelectorAll('[data-order-item]')].forEach((row, index, rows) => {
    row.querySelector('[data-order-move="up"]').disabled = index === 0;
    row.querySelector('[data-order-move="down"]').disabled = index === rows.length - 1;
    row.querySelector('[data-order-position]').textContent = `Position ${index + 1}`;
  });
  presentation.items.forEach((item, index) => list.append(el('li', { className: 'activity-order-item', 'data-order-item': item.itemId }, [
    el('span', { className: 'activity-order-position', 'data-order-position': 'true', text: `Position ${index + 1}` }),
    el('span', { className: 'activity-order-label', text: item.label }),
    el('span', { className: 'activity-order-controls' }, [
      el('button', { type: 'button', className: 'activity-icon-button', text: '↑', 'aria-label': `Monter « ${item.label} »`, 'data-order-move': 'up' }),
      el('button', { type: 'button', className: 'activity-icon-button', text: '↓', 'aria-label': `Descendre « ${item.label} »`, 'data-order-move': 'down' }),
    ]),
  ])));
  list.addEventListener('click', event => {
    const button = event.target.closest?.('[data-order-move]');
    if (!button || !list.contains(button)) return;
    const row = button.closest('[data-order-item]');
    if (button.dataset.orderMove === 'up' && row.previousElementSibling) list.insertBefore(row, row.previousElementSibling);
    if (button.dataset.orderMove === 'down' && row.nextElementSibling) list.insertBefore(row.nextElementSibling, row);
    update(); button.focus();
  });
  update();
  return shell(presentation, [prompt(presentation.prompt), list]);
}

function classify(presentation) {
  const unclassified = el('div', { className: 'activity-classify-items', 'data-classify-target': '', 'data-classify-unclassified': 'true' });
  const targets = new Map();
  const board = el('div', { className: 'activity-classify-board' }, [el('section', { className: 'activity-classify-bucket activity-classify-unclassified' }, [el('h3', { text: 'À classer' }), unclassified])]);
  presentation.buckets.forEach(bucket => {
    const target = el('div', { className: 'activity-classify-items', 'data-classify-target': bucket.bucketId }); targets.set(bucket.bucketId, target);
    board.append(el('section', { className: 'activity-classify-bucket' }, [el('h3', { text: bucket.label }), target]));
  });
  presentation.items.forEach(item => {
    const select = el('select', { id: uid('activity-classify-select'), 'data-classify-select': item.itemId, 'aria-label': `Classer « ${item.label} »` }, [el('option', { value: '', text: 'Choisir une catégorie…' })]);
    presentation.buckets.forEach(bucket => select.append(el('option', { value: bucket.bucketId, text: bucket.label })));
    unclassified.append(el('article', { className: 'activity-classify-item', 'data-classify-item': item.itemId }, [el('p', { text: item.label }), select]));
  });
  board.addEventListener('change', event => {
    const select = event.target.closest?.('[data-classify-select]');
    if (!select || !board.contains(select)) return;
    (select.value ? targets.get(select.value) : unclassified)?.append(select.closest('[data-classify-item]'));
  });
  return shell(presentation, [prompt(presentation.prompt), board]);
}

function constructed(presentation) {
  const id = uid('activity-constructed');
  return shell(presentation, [prompt(presentation.prompt), el('div', { className: 'activity-constructed' }, [
    el('label', { for: id, text: 'Votre réponse' }),
    el('textarea', { id, rows: '6', maxlength: '4000', 'data-constructed-response': 'true' }),
    el('p', { className: 'help', text: 'Réponse attendue : un texte non vide.' }),
  ])]);
}

export function renderActivityPresentation(presentation) {
  if (!presentation || typeof presentation !== 'object') throw new TypeError('ActivityPresentation object is required');
  switch (presentation.type) {
    case 'qcm': return qcm(presentation);
    case 'fill': return fill(presentation);
    case 'lesson': return lesson(presentation);
    case 'flashcard': return flashcard(presentation);
    case 'matching': return matching(presentation);
    case 'order': return order(presentation);
    case 'classify': return classify(presentation);
    case 'constructed': return constructed(presentation);
    default: throw new Error(`ACTIVITY_PRESENTATION_TYPE_UNSUPPORTED: ${presentation.type}`);
  }
}

export function readActivityResponse(container, presentation) {
  if (!(container instanceof Element) || !presentation || typeof presentation !== 'object') throw new TypeError('Activity response container and presentation are required');
  if (presentation.type === 'qcm') {
    const selected = container.querySelector('[data-activity-choice="true"]:checked');
    if (!selected) throw required('Choisissez une réponse avant de continuer.');
    return { choiceId: selected.value };
  }
  if (presentation.type === 'fill') {
    const answer = {};
    for (const select of container.querySelectorAll('[data-activity-slot]')) {
      if (!select.value) throw required('Complétez toutes les réponses avant de continuer.');
      answer[select.dataset.activitySlot] = select.value;
    }
    return answer;
  }
  const root = container.querySelector(`[data-activity-presentation="${presentation.type}"]`);
  if (presentation.type === 'lesson') {
    if (root?.dataset.activityReady !== 'true') throw required('Utilisez Continuer après avoir lu la leçon.');
    return { acknowledged: true };
  }
  if (presentation.type === 'flashcard') {
    if (root?.dataset.flashcardRevealed !== 'true' || root.dataset.activityReady !== 'true') throw required('Affichez la réponse puis utilisez Continuer.');
    return { revealed: true };
  }
  if (presentation.type === 'matching') {
    const map = associations(root);
    if (map.size !== presentation.leftItems.length) throw required('Associez chaque élément de gauche avant de continuer.');
    return { associations: presentation.leftItems.map(item => ({ leftItemId: item.itemId, rightItemId: map.get(item.itemId) })) };
  }
  if (presentation.type === 'order') {
    const orderedItemIds = [...root.querySelectorAll('[data-order-item]')].map(item => item.dataset.orderItem);
    if (orderedItemIds.length !== presentation.items.length) throw required('Ordre incomplet.');
    return { orderedItemIds };
  }
  if (presentation.type === 'classify') {
    const assignments = [...root.querySelectorAll('[data-classify-select]')].map(select => ({ itemId: select.dataset.classifySelect, bucketId: select.value })).filter(item => item.bucketId);
    if (assignments.length !== presentation.items.length) throw required('Classez chaque élément avant de continuer.');
    return { assignments };
  }
  if (presentation.type === 'constructed') {
    const text = root.querySelector('[data-constructed-response]')?.value?.trim() || '';
    if (!text) throw required('Saisissez une réponse avant de continuer.');
    return { text };
  }
  throw new Error(`ACTIVITY_PRESENTATION_TYPE_UNSUPPORTED: ${presentation.type}`);
}
