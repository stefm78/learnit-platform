'use strict';

(() => {
  const scriptUrl = new URL(document.currentScript.src);
  const APP_BASE = new URL('.', scriptUrl);
  const AUTHORITY_BASE = new URL('_authority/', APP_BASE);
  const PYODIDE_BASE = 'https://cdn.jsdelivr.net/pyodide/v0.29.4/full/';
  const API_PATHS = new Set(['/api/import', '/api/edit', '/api/validate', '/api/preview', '/api/export']);
  const rawFetch = window.fetch.bind(window);
  let pyodide = null;

  function pathOf(input) {
    const raw = typeof input === 'string' ? input : input.url;
    return new URL(raw, window.location.href);
  }

  function methodOf(input, init) {
    return String(init?.method || (typeof input === 'string' ? 'GET' : input.method) || 'GET').toUpperCase();
  }

  function bodyOf(input, init) {
    if (init && Object.prototype.hasOwnProperty.call(init, 'body')) return init.body;
    return typeof input === 'string' ? null : input.body;
  }

  async function externalGuard(input, init) {
    const url = pathOf(input);
    const method = methodOf(input, init);
    const body = bodyOf(input, init);
    if (url.origin !== window.location.origin) {
      if (!url.href.startsWith(PYODIDE_BASE) || method !== 'GET' || body != null) {
        throw new Error('M3_PAGES_EXTERNAL_NETWORK_BLOCKED');
      }
    } else if (method !== 'GET') {
      throw new Error('M3_PAGES_SAME_ORIGIN_NON_API_WRITE_BLOCKED');
    }
    return rawFetch(input, init);
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const node = document.createElement('script');
      node.src = src;
      node.async = true;
      node.onload = resolve;
      node.onerror = () => reject(new Error('PYODIDE_SCRIPT_LOAD_FAILED'));
      document.head.appendChild(node);
    });
  }

  async function fetchAuthority(relative) {
    const response = await rawFetch(new URL(relative, AUTHORITY_BASE), {method: 'GET', cache: 'no-store'});
    if (!response.ok) throw new Error('AUTHORITY_ASSET_LOAD_FAILED:' + relative);
    return response.text();
  }

  function writeText(path, text) {
    const parts = path.split('/');
    parts.pop();
    pyodide.FS.mkdirTree(parts.join('/'));
    pyodide.FS.writeFile(path, text, {encoding: 'utf8'});
  }

  const PYTHON_BRIDGE = String.raw`
import base64
import json
import sys

sys.path.insert(0, "/repo")
from authoring.studio import core as _core

def _browser_dispatch(operation, payload_json, raw_b64, source_name):
    try:
        payload = json.loads(payload_json) if payload_json else {}
        if operation == "import":
            draft = _core.create_draft(base64.b64decode(raw_b64), source_name or "kit.json")
            body = {"ok": True, "draft": draft, "validation": _core.validate_draft(draft)}
            return json.dumps({"status": 200, "kind": "json", "body": body}, ensure_ascii=False, separators=(",", ":"))
        if operation == "edit":
            draft = _core.apply_edit(payload.get("draft"), payload.get("path"), payload.get("value"))
            body = {"ok": True, "draft": draft, "validation": _core.validate_draft(draft)}
            return json.dumps({"status": 200, "kind": "json", "body": body}, ensure_ascii=False, separators=(",", ":"))
        if operation == "validate":
            body = {"ok": True, "validation": _core.validate_draft(payload.get("draft"))}
            return json.dumps({"status": 200, "kind": "json", "body": body}, ensure_ascii=False, separators=(",", ":"))
        if operation == "preview":
            preview = _core.build_preview(payload.get("draft"), payload.get("courseIndex"), payload.get("activityIndex"))
            return json.dumps({"status": 200, "kind": "json", "body": {"ok": True, "preview": preview}}, ensure_ascii=False, separators=(",", ":"))
        if operation == "export":
            data, digest = _core.export_draft(payload.get("draft"))
            body = {"dataBase64": base64.b64encode(data).decode("ascii"), "digest": digest}
            return json.dumps({"status": 200, "kind": "bytes", "body": body}, separators=(",", ":"))
        raise _core.AuthoringError("PAGES_ROUTE_UNKNOWN", "Unsupported browser adapter operation")
    except _core.AuthoringError as exc:
        return json.dumps({"status": 422, "kind": "json", "body": {"ok": False, "diagnostic": exc.diagnostic()}}, ensure_ascii=False, separators=(",", ":"))
    except Exception as exc:
        body = {"ok": False, "diagnostic": {"severity": "blocking", "code": "BROWSER_ENGINE_FAILURE", "path": "$", "cause": str(exc)}}
        return json.dumps({"status": 500, "kind": "json", "body": body}, ensure_ascii=False, separators=(",", ":"))
`;

  const engineReady = (async () => {
    await loadScript(PYODIDE_BASE + 'pyodide.js');
    if (typeof window.loadPyodide !== 'function') throw new Error('PYODIDE_GLOBAL_MISSING');
    pyodide = await window.loadPyodide({indexURL: PYODIDE_BASE});
    await pyodide.loadPackage('jsonschema');

    const [core, v2, atlas, schema] = await Promise.all([
      fetchAuthority('authoring/studio/core.py'),
      fetchAuthority('authoring/v2/validate_kit.py'),
      fetchAuthority('authoring/v2/atlas/validate_atlas_content.py'),
      fetchAuthority('contracts/learnit-kit-v2.schema.json'),
    ]);
    writeText('/repo/authoring/studio/core.py', core);
    writeText('/repo/authoring/v2/validate_kit.py', v2);
    writeText('/repo/authoring/v2/atlas/validate_atlas_content.py', atlas);
    writeText('/repo/contracts/learnit-kit-v2.schema.json', schema);
    pyodide.runPython(PYTHON_BRIDGE);
    window.__learnitPagesReady = true;
    window.dispatchEvent(new CustomEvent('learnit-pages-ready'));
  })().catch(error => {
    window.__learnitPagesReady = false;
    window.__learnitPagesError = String(error && error.message ? error.message : error);
    throw error;
  });

  function toBase64(bytes) {
    let binary = '';
    const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    const chunk = 0x8000;
    for (let offset = 0; offset < view.length; offset += chunk) {
      binary += String.fromCharCode(...view.subarray(offset, offset + chunk));
    }
    return btoa(binary);
  }

  function fromBase64(value) {
    const binary = atob(value);
    const out = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) out[i] = binary.charCodeAt(i);
    return out;
  }

  async function bodyBytes(body) {
    if (body == null) return new Uint8Array();
    if (body instanceof ArrayBuffer) return new Uint8Array(body);
    if (ArrayBuffer.isView(body)) return new Uint8Array(body.buffer, body.byteOffset, body.byteLength);
    if (body instanceof Blob) return new Uint8Array(await body.arrayBuffer());
    throw new Error('M3_PAGES_IMPORT_BODY_UNSUPPORTED');
  }

  async function bodyText(body) {
    if (body == null) return '{}';
    if (typeof body === 'string') return body;
    if (body instanceof Blob) return body.text();
    if (body instanceof ArrayBuffer || ArrayBuffer.isView(body)) {
      return new TextDecoder('utf-8', {fatal: true}).decode(await bodyBytes(body));
    }
    throw new Error('M3_PAGES_JSON_BODY_UNSUPPORTED');
  }

  function headerValue(input, init, name) {
    const headers = new Headers(init?.headers || (typeof input === 'string' ? undefined : input.headers));
    return headers.get(name);
  }

  async function dispatchApi(input, init, url) {
    await engineReady;
    const operation = url.pathname.slice('/api/'.length);
    let payloadJson = '{}';
    let rawB64 = '';
    let sourceName = 'kit.json';
    if (operation === 'import') {
      rawB64 = toBase64(await bodyBytes(bodyOf(input, init)));
      sourceName = headerValue(input, init, 'X-Learnit-Source-Name') || 'kit.json';
    } else {
      payloadJson = await bodyText(bodyOf(input, init));
    }

    pyodide.globals.set('_browser_operation', operation);
    pyodide.globals.set('_browser_payload_json', payloadJson);
    pyodide.globals.set('_browser_raw_b64', rawB64);
    pyodide.globals.set('_browser_source_name', sourceName);
    const packed = pyodide.runPython(
      '_browser_dispatch(_browser_operation, _browser_payload_json, _browser_raw_b64, _browser_source_name)'
    );
    const result = JSON.parse(String(packed));

    if (result.kind === 'bytes') {
      return new Response(fromBase64(result.body.dataBase64), {
        status: result.status,
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
          'Content-Disposition': 'attachment; filename="learnit-atlas-export.json"',
          'X-Learnit-Sha256': result.body.digest,
        },
      });
    }
    return new Response(JSON.stringify(result.body), {
      status: result.status,
      headers: {'Content-Type': 'application/json; charset=utf-8'},
    });
  }

  window.fetch = async function guardedPagesFetch(input, init = {}) {
    const url = pathOf(input);
    if (url.origin === window.location.origin && API_PATHS.has(url.pathname)) {
      if (methodOf(input, init) !== 'POST') {
        return new Response(JSON.stringify({ok: false, cause: 'Method not allowed'}), {
          status: 405,
          headers: {'Content-Type': 'application/json'},
        });
      }
      return dispatchApi(input, init, url);
    }
    return externalGuard(input, init);
  };

  document.addEventListener('DOMContentLoaded', () => {
    const subtitle = document.querySelector('.subtitle');
    if (subtitle) {
      subtitle.insertAdjacentHTML('afterend',
        '<p class="muted" id="pages-mode">Mode GitHub Pages · moteur Python exécuté dans ce navigateur.</p>');
    }
  });
})();
