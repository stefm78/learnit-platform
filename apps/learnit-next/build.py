#!/usr/bin/env python3
"""Deterministic, fail-closed Learn-it Next single-file build."""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps/learnit-next"
MANIFEST_PATH = APP / "source_manifest.json"
DEFAULT_OUTPUT = APP / "dist/learnit-next.html"
ARTIFACT_REL = "apps/learnit-next/dist/learnit-next.html"
SELF_PATH = "apps/learnit-next/source_manifest.json"
SELF_KIND = "canonical-self-sha256"
BLOB_KIND = "git-blob-sha1"
IMPORT_RE = re.compile(
    r"""(?P<prefix>\b(?:import|export)\s+(?:(?:[^'";]*?)\s+from\s+)?)(?P<quote>['"])(?P<spec>[^'"]+)(?P=quote)""",
    re.MULTILINE,
)


class BuildError(RuntimeError):
    """A deterministic build contract was violated."""


def duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BuildError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=duplicate_rejecting_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot read JSON {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise BuildError(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def manifest_self_digest(manifest: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(manifest, ensure_ascii=False))
    hits = [
        item for item in clone.get("workingFiles", [])
        if item.get("path") == SELF_PATH
    ]
    if len(hits) != 1:
        raise BuildError("manifest must contain its own path exactly once")
    hits[0]["fingerprint"]["value"] = None
    return sha256(canonical_bytes(clone))


def git_blob_bytes(blob_sha: str) -> bytes:
    if not (ROOT / ".git").exists():
        raise BuildError(
            f"declared file is absent and Git object access is unavailable: {blob_sha}"
        )
    process = subprocess.run(
        ["git", "cat-file", "blob", blob_sha],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode:
        detail = process.stderr.decode("utf-8", "replace").strip()
        raise BuildError(f"cannot read declared Git blob {blob_sha}: {detail}")
    return process.stdout


def item_bytes(item: dict[str, Any]) -> bytes:
    path = str(item["path"])
    target = ROOT / path
    if target.is_file():
        return target.read_bytes()
    fingerprint = item.get("fingerprint", {})
    if fingerprint.get("kind") != BLOB_KIND:
        raise BuildError(f"missing non-blob manifest file: {path}")
    return git_blob_bytes(str(fingerprint.get("value", "")))


def validate_manifest() -> tuple[dict[str, Any], list[str], dict[str, bytes]]:
    manifest = load_json(MANIFEST_PATH)
    if manifest.get("schema") != "learnit.next.source-manifest.v2":
        raise BuildError("unsupported source manifest schema")
    if manifest.get("workPackage") != "ATLAS-WP-001":
        raise BuildError("source manifest work package differs")

    items = manifest.get("workingFiles")
    if not isinstance(items, list) or not items:
        raise BuildError("workingFiles must be a non-empty list")
    paths = [item.get("path") for item in items if isinstance(item, dict)]
    if len(paths) != len(items) or len(set(paths)) != len(paths):
        raise BuildError("workingFiles paths must be unique strings")
    if manifest.get("fileBudget") != len(items):
        raise BuildError("manifest fileBudget differs from workingFiles count")

    ordered = manifest.get("build", {}).get("orderedSources")
    if not isinstance(ordered, list) or not ordered or len(set(ordered)) != len(ordered):
        raise BuildError("build.orderedSources must be a unique non-empty list")
    required = {
        "apps/learnit-next/index.template.html",
        "apps/learnit-next/src/styles.css",
        "apps/learnit-next/src/main.js",
    }
    if not required.issubset(set(ordered)):
        raise BuildError("canonical template, stylesheet or main module is absent")
    if not set(ordered).issubset(set(paths)):
        raise BuildError("ordered build source is absent from workingFiles")

    commonjs = manifest.get("build", {}).get("commonJsSources", [])
    styles = manifest.get("build", {}).get("orderedStyles", ["apps/learnit-next/src/styles.css"])

    if not isinstance(commonjs, list) or len(set(commonjs)) != len(commonjs):
        raise BuildError("build.commonJsSources must be a unique list")
    if not isinstance(styles, list) or not styles or len(set(styles)) != len(styles):
        raise BuildError("build.orderedStyles must be a unique non-empty list")
    if not set(commonjs).issubset(set(ordered)):
        raise BuildError("CommonJS source is absent from orderedSources")
    if not set(styles).issubset(set(paths)):
        raise BuildError("ordered style is absent from workingFiles")

    if manifest.get("artifact", {}).get("path") != ARTIFACT_REL:
        raise BuildError("manifest artifact path is not canonical")

    data_by_path: dict[str, bytes] = {}
    for item in items:
        path = str(item["path"])
        fingerprint = item.get("fingerprint", {})
        kind = fingerprint.get("kind")
        declared = fingerprint.get("value")
        if path == SELF_PATH:
            actual = manifest_self_digest(manifest)
            if kind != SELF_KIND or declared != actual:
                raise BuildError(
                    f"source manifest self fingerprint is stale: expected={declared} actual={actual}"
                )
            data_by_path[path] = MANIFEST_PATH.read_bytes()
            continue
        data = item_bytes(item)
        actual = git_blob_sha1(data)
        if kind != BLOB_KIND or declared != actual:
            raise BuildError(
                f"stale Git blob fingerprint: {path}: expected={declared} actual={actual}"
            )
        data_by_path[path] = data

    actual_source_files: set[str] = set()
    template = APP / "index.template.html"
    if template.is_file():
        actual_source_files.add(template.relative_to(ROOT).as_posix())
    source_root = APP / "src"
    if source_root.exists():
        actual_source_files.update(
            path.relative_to(ROOT).as_posix()
            for path in source_root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    extras = actual_source_files - set(ordered)
    missing = set(ordered) - set(data_by_path)
    if extras or missing:
        raise BuildError(f"source tree drift: extra={sorted(extras)}, missing={sorted(missing)}")

    return manifest, ordered, data_by_path


def resolve_import(current: str, specifier: str, known: set[str]) -> str:
    if not specifier.startswith("."):
        raise BuildError(f"external module import is forbidden: {current} -> {specifier}")
    target = posixpath.normpath(posixpath.join(posixpath.dirname(current), specifier))
    if target not in known:
        raise BuildError(f"undeclared module import: {current} -> {target}")
    return target


def prepare_modules(
    ordered: list[str],
    data_by_path: dict[str, bytes],
    commonjs_paths: set[str] | None = None,
) -> tuple[dict[str, str], dict[str, list[tuple[str, str]]], list[str]]:
    commonjs = commonjs_paths or set()
    module_paths = [
        path
        for path in ordered
        if path.endswith(".js") and path not in commonjs
    ]
    known = set(module_paths)
    sources: dict[str, str] = {}
    dependencies: dict[str, list[tuple[str, str]]] = {}
    token_counter = 0

    for path in module_paths:
        try:
            source = data_by_path[path].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BuildError(f"JavaScript source is not UTF-8: {path}") from exc
        deps: list[tuple[str, str]] = []

        def replace(match: re.Match[str]) -> str:
            nonlocal token_counter
            target = resolve_import(path, match.group("spec"), known)
            token = f"__LEARNIT_MODULE_URL_{token_counter:04d}__"
            token_counter += 1
            deps.append((token, target))
            return f"{match.group('prefix')}{match.group('quote')}{token}{match.group('quote')}"

        sources[path] = IMPORT_RE.sub(replace, source)
        dependencies[path] = deps

    order: list[str] = []
    state: dict[str, int] = {}

    def visit(path: str) -> None:
        status = state.get(path, 0)
        if status == 1:
            raise BuildError(f"cyclic ES module graph is unsupported: {path}")
        if status == 2:
            return
        state[path] = 1
        for _, target in dependencies[path]:
            visit(target)
        state[path] = 2
        order.append(path)

    for path in module_paths:
        visit(path)
    return sources, dependencies, order


def safe_json(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_commonjs_runtime(
    commonjs_paths: list[str],
    data_by_path: dict[str, bytes],
) -> str:
    sources: dict[str, str] = {}
    for path in commonjs_paths:
        try:
            sources[path] = data_by_path[path].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BuildError(f"CommonJS source is not UTF-8: {path}") from exc

    return (
        "const __atlasCjsSources=Object.freeze("
        + safe_json(sources)
        + ");\n"
        + r"""
const __atlasCjsCache=Object.create(null);
const __atlasShaK=new Uint32Array([
  0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
  0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
  0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
  0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
  0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
  0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
  0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
  0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
]);

function __atlasRotr(value,bits){
  return (value>>>bits)|(value<<(32-bits));
}

function __atlasSha256(bytes){
  const bitLength=bytes.length*8;
  const totalLength=Math.ceil((bytes.length+9)/64)*64;
  const message=new Uint8Array(totalLength);
  message.set(bytes);
  message[bytes.length]=0x80;

  const high=Math.floor(bitLength/0x100000000);
  const low=bitLength>>>0;
  const view=new DataView(message.buffer);
  view.setUint32(totalLength-8,high);
  view.setUint32(totalLength-4,low);

  const state=new Uint32Array([
    0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
    0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19
  ]);
  const words=new Uint32Array(64);

  for(let offset=0;offset<message.length;offset+=64){
    for(let index=0;index<16;index+=1){
      const base=offset+index*4;
      words[index]=(
        (message[base]<<24)|
        (message[base+1]<<16)|
        (message[base+2]<<8)|
        message[base+3]
      )>>>0;
    }

    for(let index=16;index<64;index+=1){
      const x=words[index-15];
      const y=words[index-2];
      const s0=__atlasRotr(x,7)^__atlasRotr(x,18)^(x>>>3);
      const s1=__atlasRotr(y,17)^__atlasRotr(y,19)^(y>>>10);
      words[index]=(words[index-16]+s0+words[index-7]+s1)>>>0;
    }

    let a=state[0],b=state[1],c=state[2],d=state[3];
    let e=state[4],f=state[5],g=state[6],h=state[7];

    for(let index=0;index<64;index+=1){
      const sum1=(
        __atlasRotr(e,6)^__atlasRotr(e,11)^__atlasRotr(e,25)
      )>>>0;
      const choice=((e&f)^((~e)&g))>>>0;
      const temp1=(h+sum1+choice+__atlasShaK[index]+words[index])>>>0;
      const sum0=(
        __atlasRotr(a,2)^__atlasRotr(a,13)^__atlasRotr(a,22)
      )>>>0;
      const majority=((a&b)^(a&c)^(b&c))>>>0;
      const temp2=(sum0+majority)>>>0;

      h=g;
      g=f;
      f=e;
      e=(d+temp1)>>>0;
      d=c;
      c=b;
      b=a;
      a=(temp1+temp2)>>>0;
    }

    state[0]=(state[0]+a)>>>0;
    state[1]=(state[1]+b)>>>0;
    state[2]=(state[2]+c)>>>0;
    state[3]=(state[3]+d)>>>0;
    state[4]=(state[4]+e)>>>0;
    state[5]=(state[5]+f)>>>0;
    state[6]=(state[6]+g)>>>0;
    state[7]=(state[7]+h)>>>0;
  }

  return Array.from(state)
    .map(value=>value.toString(16).padStart(8,'0'))
    .join('');
}

function __atlasBytes(value,encoding='utf8'){
  if(value instanceof Uint8Array)return new Uint8Array(value);
  if(value instanceof ArrayBuffer)return new Uint8Array(value.slice(0));
  if(Array.isArray(value))return Uint8Array.from(value);
  if(typeof value==='string'){
    if(encoding==='hex'){
      if(value.length%2!==0||!/^[0-9a-f]*$/i.test(value)){
        throw new Error('ATLAS_INVALID_HEX_BUFFER');
      }
      const output=new Uint8Array(value.length/2);
      for(let index=0;index<output.length;index+=1){
        output[index]=Number.parseInt(value.slice(index*2,index*2+2),16);
      }
      return output;
    }
    if(encoding!=='utf8'&&encoding!=='utf-8'){
      throw new Error(`ATLAS_UNSUPPORTED_BUFFER_ENCODING: ${encoding}`);
    }
    return new TextEncoder().encode(value);
  }
  throw new TypeError('ATLAS_UNSUPPORTED_BUFFER_INPUT');
}

const __atlasBuffer=Object.freeze({
  from(value,encoding='utf8'){
    return __atlasBytes(value,encoding);
  },
  concat(chunks){
    if(!Array.isArray(chunks))throw new TypeError('ATLAS_BUFFER_LIST_REQUIRED');
    const normalized=chunks.map(chunk=>__atlasBytes(chunk));
    const length=normalized.reduce((sum,chunk)=>sum+chunk.length,0);
    const output=new Uint8Array(length);
    let offset=0;
    for(const chunk of normalized){
      output.set(chunk,offset);
      offset+=chunk.length;
    }
    return output;
  },
  isBuffer(value){
    return value instanceof Uint8Array;
  }
});

const __atlasCrypto=Object.freeze({
  createHash(algorithm){
    if(algorithm!=='sha256')throw new Error(`ATLAS_UNSUPPORTED_HASH: ${algorithm}`);
    const chunks=[];
    return {
      update(value,encoding='utf8'){
        chunks.push(__atlasBytes(value,encoding));
        return this;
      },
      digest(encoding){
        const bytes=__atlasBuffer.concat(chunks);
        const hexadecimal=__atlasSha256(bytes);
        if(encoding===undefined)return __atlasBytes(hexadecimal,'hex');
        if(encoding==='hex')return hexadecimal;
        throw new Error(`ATLAS_UNSUPPORTED_DIGEST_ENCODING: ${encoding}`);
      }
    };
  }
});

function __atlasNormalize(parts){
  const output=[];
  for(const part of parts){
    if(!part||part==='.')continue;
    if(part==='..'){
      if(!output.length)throw new Error('ATLAS_MODULE_PATH_ESCAPE');
      output.pop();
      continue;
    }
    output.push(part);
  }
  return output.join('/');
}

function __atlasResolve(from,specifier){
  if(specifier==='crypto')return 'crypto';
  if(typeof specifier!=='string'||!specifier.startsWith('.')){
    throw new Error(`ATLAS_EXTERNAL_MODULE_FORBIDDEN: ${specifier}`);
  }
  const slash=from.lastIndexOf('/');
  const directory=slash>=0?from.slice(0,slash):'';
  let resolved=__atlasNormalize(
    `${directory}/${specifier}`.split('/')
  );
  if(!resolved.endsWith('.js'))resolved+='.js';
  if(!Object.prototype.hasOwnProperty.call(__atlasCjsSources,resolved)){
    throw new Error(`ATLAS_MODULE_NOT_DECLARED: ${from} -> ${specifier}`);
  }
  return resolved;
}

function __atlasRequire(specifier,from=null){
  const resolved=from?__atlasResolve(from,specifier):specifier;
  if(resolved==='crypto')return __atlasCrypto;

  if(!Object.prototype.hasOwnProperty.call(__atlasCjsSources,resolved)){
    throw new Error(`ATLAS_MODULE_NOT_DECLARED: ${resolved}`);
  }

  if(__atlasCjsCache[resolved])return __atlasCjsCache[resolved].exports;

  const module={exports:{}};
  __atlasCjsCache[resolved]=module;

  try{
    const source=__atlasCjsSources[resolved];
    const factory=new Function(
      'require',
      'module',
      'exports',
      'Buffer',
      `${source}\n//# sourceURL=${resolved}`
    );
    factory(
      requested=>__atlasRequire(requested,resolved),
      module,
      module.exports,
      __atlasBuffer
    );
    return module.exports;
  }catch(error){
    delete __atlasCjsCache[resolved];
    throw error;
  }
}

Object.defineProperty(globalThis,'__LEARNIT_ATLAS_CJS__',{
  configurable:false,
  enumerable:false,
  writable:false,
  value:Object.freeze({
    require(modulePath){
      return __atlasRequire(modulePath,null);
    },
    modulePaths:Object.freeze(Object.keys(__atlasCjsSources).sort())
  })
});
"""
    )



def render_artifact(
    manifest: dict[str, Any],
    ordered: list[str],
    data_by_path: dict[str, bytes],
) -> bytes:
    template_path = "apps/learnit-next/index.template.html"
    css_path = "apps/learnit-next/src/styles.css"
    main_path = "apps/learnit-next/src/main.js"
    try:
        template = data_by_path[template_path].decode("utf-8")
        style_paths = manifest.get("build", {}).get(
            "orderedStyles",
            [css_path],
        )
        css = "\n\n".join(
            data_by_path[path].decode("utf-8").rstrip()
            for path in style_paths
        )
    except UnicodeDecodeError as exc:
        raise BuildError("template or stylesheet is not UTF-8") from exc

    commonjs_paths = manifest.get("build", {}).get("commonJsSources", [])
    sources, dependencies, module_order = prepare_modules(
        ordered,
        data_by_path,
        set(commonjs_paths),
    )
    commonjs_runtime = render_commonjs_runtime(
        commonjs_paths,
        data_by_path,
    )
    if main_path not in sources:
        raise BuildError("main.js is absent from the module graph")

    bootstrap = (
        commonjs_runtime
        + "\n"
        + "const __sources=Object.freeze(" + safe_json(sources) + ");\n"
        "const __dependencies=Object.freeze(" + safe_json(dependencies) + ");\n"
        "const __order=Object.freeze(" + safe_json(module_order) + ");\n"
        "const __urls=Object.create(null);\n"
        "for(const __id of __order){\n"
        "  let __source=__sources[__id];\n"
        "  for(const [__token,__target] of __dependencies[__id]){\n"
        "    const __url=__urls[__target];\n"
        "    if(!__url)throw new Error(`Unresolved bundled module: ${__id} -> ${__target}`);\n"
        "    __source=__source.split(__token).join(__url);\n"
        "  }\n"
        "  __urls[__id]=URL.createObjectURL(new Blob([__source],{type:'text/javascript'}));\n"
        "}\n"
        "await import(__urls[" + json.dumps(main_path) + "]);\n"
    )

    link = '<link rel="stylesheet" href="./src/styles.css">'
    module = '<script type="module" src="./src/main.js"></script>'
    if template.count(link) != 1 or template.count(module) != 1:
        raise BuildError("template entry points are not the frozen expected form")
    artifact = template.replace(link, f"<style>\n{css}\n</style>").replace(
        module, f'<script type="module">\n{bootstrap}</script>'
    )
    return (artifact.rstrip() + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        manifest, ordered, data_by_path = validate_manifest()
        artifact = render_artifact(manifest, ordered, data_by_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(artifact)
        print(
            json.dumps(
                {
                    "artifact": (
                        output.relative_to(ROOT).as_posix()
                        if output.is_relative_to(ROOT)
                        else output.as_posix()
                    ),
                    "bytes": len(artifact),
                    "sha256": sha256(artifact),
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:
        print(f"LEARNIT_NEXT_BUILD_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
