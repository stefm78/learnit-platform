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
  'focusable', 'aria-label',
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
  if (media.zoomable === true) figure.append(el('details', { className: 'activity-media-zoom' }, [
    el('summary', { text: 'Agrandir l’image' }),
    el('img', { src: image.src, alt: result.alt, 'data-activity-media-zoom-image': 'true' }),
  ]));
  return figure;
}

export function renderEmbeddedMediaSet(mediaItems = []) {
  const fragment = document.createDocumentFragment();
  if (Array.isArray(mediaItems)) mediaItems.forEach(media => fragment.append(renderEmbeddedMedia(media)));
  return fragment;
}
