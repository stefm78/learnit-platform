// Defensive, local-only media presentation for Student V0.1.
const SVG_TAGS = new Set([
  'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline',
  'polygon', 'text', 'tspan', 'defs', 'lineargradient', 'radialgradient',
  'stop', 'clippath', 'mask', 'title', 'desc',
]);

const SVG_ATTRS = new Set([
  'xmlns', 'viewbox', 'preserveaspectratio', 'width', 'height', 'x', 'y',
  'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'points', 'd',
  'fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin',
  'stroke-dasharray', 'stroke-dashoffset', 'opacity', 'fill-opacity',
  'stroke-opacity', 'transform', 'font-size', 'font-family', 'font-weight',
  'text-anchor', 'dominant-baseline', 'offset', 'stop-color', 'stop-opacity',
  'clip-path', 'mask', 'gradientunits', 'gradienttransform', 'id', 'role',
  'focusable', 'aria-label', 'aria-labelledby',
]);

const SVG_FRAGMENT_ATTRS = new Set(['fill', 'stroke', 'clip-path', 'mask']);
const MEDIA_FORMATS = new Set(['svg', 'png', 'jpeg', 'webp']);
const MAX_MEDIA_DATA_CHARS = 5_000_000;
const CANONICAL_XMLNS = 'http://www.w3.org/2000/svg';

function safeFragment(value) {
  return /^url\(\s*#[A-Za-z_][\w:.-]*\s*\)$/i.test(String(value));
}

function safeAttributeValue(name, value) {
  const text = String(value).trim();
  if (/[\u0000-\u001f\u007f]/.test(text)) return false;
  if (name === 'xmlns') return text === CANONICAL_XMLNS;
  if (/url\s*\(/i.test(text)) return SVG_FRAGMENT_ATTRS.has(name) && safeFragment(text);
  return !text.includes(':');
}

export function validateSvg(source) {
  const raw = typeof source === 'string' ? source.trim() : '';
  if (!raw || raw.length > MAX_MEDIA_DATA_CHARS || !/^<svg(?:\s|>)/i.test(raw)) {
    return Object.freeze({ ok: false, reason: 'svg-data-invalid', svg: '' });
  }
  if (raw.includes('<!') || raw.includes('<?')) {
    return Object.freeze({ ok: false, reason: 'svg-declaration-rejected', svg: '' });
  }
  if (typeof DOMParser !== 'function' || typeof XMLSerializer !== 'function') {
    return Object.freeze({ ok: false, reason: 'svg-parser-unavailable', svg: '' });
  }

  let parsed;
  try {
    parsed = new DOMParser().parseFromString(raw, 'image/svg+xml');
  } catch {
    return Object.freeze({ ok: false, reason: 'svg-parse-failed', svg: '' });
  }
  if (!parsed || parsed.querySelector('parsererror')) {
    return Object.freeze({ ok: false, reason: 'svg-parse-failed', svg: '' });
  }

  const root = parsed.documentElement;
  if (!root || String(root.localName || '').toLowerCase() !== 'svg') {
    return Object.freeze({ ok: false, reason: 'svg-root-rejected', svg: '' });
  }
  for (const node of [root, ...root.querySelectorAll('*')]) {
    const tag = String(node.localName || '').toLowerCase();
    if (!SVG_TAGS.has(tag)) return Object.freeze({ ok: false, reason: 'svg-element-rejected', svg: '' });
    for (const attribute of [...node.attributes]) {
      const name = String(attribute.name || '').toLowerCase();
      if (!SVG_ATTRS.has(name) || !safeAttributeValue(name, attribute.value)) {
        return Object.freeze({ ok: false, reason: 'svg-attribute-rejected', svg: '' });
      }
    }
  }

  root.setAttribute('xmlns', CANONICAL_XMLNS);
  root.setAttribute('focusable', 'false');
  return Object.freeze({ ok: true, reason: 'safe-svg', svg: new XMLSerializer().serializeToString(root) });
}

export function validateEmbeddedMedia(media) {
  if (!media || typeof media !== 'object') return Object.freeze({ ok: false, reason: 'media-shape-invalid' });
  const format = String(media.format || '').toLowerCase();
  const alt = typeof media.alt === 'string' ? media.alt.trim() : '';
  const data = typeof media.data === 'string' ? media.data.trim() : '';
  if (!MEDIA_FORMATS.has(format) || !alt || !data || data.length > MAX_MEDIA_DATA_CHARS) {
    return Object.freeze({ ok: false, reason: 'media-metadata-rejected' });
  }
  if (format === 'svg') {
    const result = validateSvg(data);
    return Object.freeze({ ...result, format, alt, data: result.ok ? result.svg : '' });
  }
  const expression = new RegExp(`^data:image/${format};base64,([A-Za-z0-9+/]+={0,2})$`, 'i');
  const match = data.match(expression);
  if (!match || match[1].length % 4 !== 0) return Object.freeze({ ok: false, reason: 'raster-data-rejected' });
  return Object.freeze({ ok: true, reason: 'safe-raster', format, alt, data });
}

function el(tag, attrs = {}, children = []) {
  const out = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value == null) continue;
    if (name === 'className') out.className = value;
    else if (name === 'text') out.textContent = String(value);
    else out.setAttribute(name, String(value));
  }
  for (const child of (Array.isArray(children) ? children : [children])) {
    if (child != null) out.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return out;
}

function rejected(media, reason) {
  return el('div', { className: 'activity-media-rejected', role: 'status', 'data-activity-media-rejected': reason }, [
    el('span', { text: `Le média « ${String(media?.alt || 'sans description')} » n’a pas pu être affiché en toute sécurité.` }),
  ]);
}

function sourceFor(result) {
  return result.format === 'svg'
    ? `data:image/svg+xml;charset=utf-8,${encodeURIComponent(result.data)}`
    : result.data;
}

export function renderEmbeddedMedia(media) {
  const result = validateEmbeddedMedia(media);
  if (!result.ok) return rejected(media, result.reason);
  const image = el('img', { src: sourceFor(result), alt: result.alt, loading: 'eager', decoding: 'async', 'data-activity-media-image': result.format });
  const display = media.display === 'full_width' ? 'full-width' : 'contained';
  const figure = el('figure', {
    className: `activity-media activity-media-${display}`,
    'data-activity-media': String(media.assetId || ''),
    'data-activity-media-placement': String(media.placement || 'content'),
  }, [image]);
  if (media.caption?.trim()) figure.append(el('figcaption', { text: media.caption.trim() }));
  if (media.zoomable === true) {
    image.classList.add('activity-media-open');
    image.setAttribute('role', 'button');
    image.setAttribute('tabindex', '0');
    image.setAttribute('aria-label', `Agrandir l’image : ${result.alt}`);
    image.setAttribute('data-activity-media-open', 'true');
    const open = () => openMediaViewer(image.src, result.alt, image);
    image.addEventListener('click', open);
    image.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); }
    });
  }
  return figure;
}

export function renderEmbeddedMediaSet(mediaItems = []) {
  const fragment = document.createDocumentFragment();
  if (Array.isArray(mediaItems)) mediaItems.forEach(media => fragment.append(renderEmbeddedMedia(media)));
  return fragment;
}

// Shared, local-only accessible image viewer; 100% means fitted to the viewport.
const MEDIA_MAX_ZOOM = 8;
let closeActiveMediaViewer = null;

function openMediaViewer(src, alt, opener) {
  closeActiveMediaViewer?.();
  const previousOverflow = document.body.style.overflow;
  const viewer = el('div', {
    className: 'activity-media-viewer', role: 'dialog', 'aria-modal': 'true',
    'aria-label': 'Image agrandie : ' + alt, 'data-activity-media-viewer': 'true',
  });
  const stage = el('div', { className: 'activity-media-viewer-stage', 'data-activity-media-stage': 'true' });
  const image = el('img', {
    className: 'activity-media-viewer-image', src, alt, draggable: 'false',
    'data-activity-media-viewer-image': 'true',
  });
  const percent = el('output', {
    className: 'activity-media-viewer-percent', 'aria-live': 'polite',
    'data-activity-media-zoom-percent': 'true', text: '100 %',
  });
  const state = { zoom: 1, x: 0, y: 0, pointers: new Map(), gesture: null, closed: false };
  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
  function recenterBounds() {
    const w = stage.clientWidth, h = stage.clientHeight;
    if (w <= 0 || h <= 0 || !image.naturalWidth || !image.naturalHeight) {
      state.x = 0; state.y = 0; return;
    }
    const fit = Math.min(w / image.naturalWidth, h / image.naturalHeight);
    const maxX = Math.max(0, (image.naturalWidth * fit * state.zoom - w) / 2);
    const maxY = Math.max(0, (image.naturalHeight * fit * state.zoom - h) / 2);
    state.x = clamp(state.x, -maxX, maxX);
    state.y = clamp(state.y, -maxY, maxY);
  }
  function update() {
    recenterBounds();
    image.style.transform = 'translate3d(' + state.x + 'px, ' + state.y + 'px, 0) scale(' + state.zoom + ')';
    percent.textContent = Math.round(state.zoom * 100) + ' %';
    viewer.dataset.zoom = String(state.zoom);
    viewer.dataset.panX = String(state.x);
    viewer.dataset.panY = String(state.y);
  }
  function localPoint(clientX, clientY) {
    const r = stage.getBoundingClientRect();
    return { x: clientX - r.left - r.width / 2, y: clientY - r.top - r.height / 2 };
  }
  function zoomTo(target, anchor = { x: 0, y: 0 }) {
    const next = clamp(target, 1, MEDIA_MAX_ZOOM);
    const ratio = next / state.zoom;
    state.x = anchor.x - (anchor.x - state.x) * ratio;
    state.y = anchor.y - (anchor.y - state.y) * ratio;
    state.zoom = next;
    update();
  }
  function fit() { state.zoom = 1; state.x = 0; state.y = 0; update(); }
  function action(label, attribute, fn) {
    const button = el('button', { type: 'button', className: 'activity-media-viewer-control', [attribute]: 'true', text: label });
    button.addEventListener('click', fn);
    return button;
  }
  const controls = el('div', { className: 'activity-media-viewer-controls' });
  controls.append(
    action('−', 'data-activity-media-zoom-out', () => zoomTo(state.zoom / 1.5)),
    percent,
    action('+', 'data-activity-media-zoom-in', () => zoomTo(state.zoom * 1.5)),
    action('Ajuster', 'data-activity-media-fit', fit),
  );
  const closeButton = action('Fermer', 'data-activity-media-close', close);
  const toolbar = el('div', { className: 'activity-media-viewer-toolbar' }, [
    el('span', { className: 'activity-media-viewer-label', text: alt }),
    controls,
    closeButton,
  ]);
  stage.append(image);
  viewer.append(toolbar, stage);
  function release(event) {
    state.pointers.delete(event.pointerId);
    state.gesture = null;
    if (state.pointers.size === 1) {
      const p = state.pointers.values().next().value;
      state.gesture = { type: 'drag', x: p.x, y: p.y };
    }
    if (stage.hasPointerCapture?.(event.pointerId)) stage.releasePointerCapture(event.pointerId);
  }
  function pointerDown(event) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    event.preventDefault();
    stage.setPointerCapture?.(event.pointerId);
    state.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (state.pointers.size === 1) {
      state.gesture = { type: 'drag', x: event.clientX, y: event.clientY };
    } else if (state.pointers.size === 2) {
      const [a, b] = [...state.pointers.values()];
      state.gesture = { type: 'pinch', x: (a.x + b.x) / 2, y: (a.y + b.y) / 2,
        distance: Math.hypot(a.x - b.x, a.y - b.y) };
    }
  }
  function pointerMove(event) {
    if (!state.pointers.has(event.pointerId)) return;
    event.preventDefault();
    state.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (state.pointers.size === 1 && state.gesture?.type === 'drag') {
      state.x += event.clientX - state.gesture.x;
      state.y += event.clientY - state.gesture.y;
      state.gesture.x = event.clientX;
      state.gesture.y = event.clientY;
      update();
    } else if (state.pointers.size === 2 && state.gesture?.type === 'pinch') {
      const [a, b] = [...state.pointers.values()];
      const x = (a.x + b.x) / 2, y = (a.y + b.y) / 2;
      const distance = Math.hypot(a.x - b.x, a.y - b.y);
      state.x += x - state.gesture.x;
      state.y += y - state.gesture.y;
      if (state.gesture.distance > 0 && distance > 0) {
        zoomTo(state.zoom * distance / state.gesture.distance, localPoint(x, y));
      } else update();
      state.gesture = { type: 'pinch', x, y, distance };
    }
  }
  function onWheel(event) {
    event.preventDefault();
    zoomTo(state.zoom * (event.deltaY < 0 ? 1.25 : 0.8), localPoint(event.clientX, event.clientY));
  }
  function onKey(event) {
    if (event.key === 'Escape') { event.preventDefault(); close(); return; }
    if (event.key === 'Tab') {
      const focusables = [...viewer.querySelectorAll('button:not([disabled])')];
      if (!focusables.length) return;
      const first = focusables[0], last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      return;
    }
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.key === '+' || event.key === '=') { event.preventDefault(); zoomTo(state.zoom * 1.5); }
    else if (event.key === '-') { event.preventDefault(); zoomTo(state.zoom / 1.5); }
    else if (event.key === '0') { event.preventDefault(); fit(); }
    else if (state.zoom > 1 && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
      event.preventDefault();
      state.x += event.key === 'ArrowLeft' ? -45 : event.key === 'ArrowRight' ? 45 : 0;
      state.y += event.key === 'ArrowUp' ? -45 : event.key === 'ArrowDown' ? 45 : 0;
      update();
    }
  }
  function close() {
    if (state.closed) return;
    state.closed = true;
    stage.removeEventListener('wheel', onWheel);
    document.removeEventListener('keydown', onKey, true);
    window.removeEventListener('resize', update);
    observer.disconnect();
    state.pointers.clear();
    viewer.remove();
    document.body.style.overflow = previousOverflow;
    if (closeActiveMediaViewer === close) closeActiveMediaViewer = null;
    if (opener.isConnected) opener.focus();
  }
  const observer = new MutationObserver(() => { if (!opener.isConnected) close(); });
  stage.addEventListener('pointerdown', pointerDown);
  stage.addEventListener('pointermove', pointerMove);
  stage.addEventListener('pointerup', release);
  stage.addEventListener('pointercancel', release);
  stage.addEventListener('lostpointercapture', release);
  stage.addEventListener('wheel', onWheel, { passive: false });
  image.addEventListener('load', fit);
  image.addEventListener('dragstart', event => event.preventDefault());
  document.addEventListener('keydown', onKey, true);
  window.addEventListener('resize', update);
  document.body.append(viewer);
  document.body.style.overflow = 'hidden';
  observer.observe(document.body, { childList: true, subtree: true });
  closeActiveMediaViewer = close;
  closeButton.focus();
  fit();
}
