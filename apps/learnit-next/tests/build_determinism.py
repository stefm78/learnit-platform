#!/usr/bin/env python3
"""Contradictory clean-build, manifest and artifact-identity tests."""
from __future__ import annotations
import hashlib, json, os, shlex, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from typing import Any, Iterable

ROOT=Path(__file__).resolve().parents[3]
APP_REL=Path("apps/learnit-next");BUILD_REL=APP_REL/"build.py";MANIFEST_REL=APP_REL/"source_manifest.json"
ARTIFACT_REL=APP_REL/"dist/learnit-next.html";FILE_PLAN_REL=Path("docs/architecture/clean-generation/FILE_PLAN_V1.json")
STRICT=os.environ.get("LEARNIT_NEXT_STRICT_INTEGRATION")=="1"
PLANNED_BUILD_INPUTS={
"apps/learnit-next/index.template.html","apps/learnit-next/src/styles.css","apps/learnit-next/src/main.js",
"apps/learnit-next/src/core/canonical_json.js","apps/learnit-next/src/core/identity.js",
"apps/learnit-next/src/core/contract.js","apps/learnit-next/src/core/import.js",
"apps/learnit-next/src/core/library.js","apps/learnit-next/src/core/session.js",
"apps/learnit-next/src/core/progress.js","apps/learnit-next/src/ports/storage.js",
"apps/learnit-next/src/adapters/indexeddb.js","apps/learnit-next/src/ui/render.js"}
QA_PATHS={"contracts/fixtures/v2-valid-minimal.json","contracts/fixtures/v2-invalid-legacy.json",
"contracts/fixtures/v2-invalid-digest-mismatch.json","apps/learnit-next/tests/contract_v2.py",
"apps/learnit-next/tests/storage_isolation.py","apps/learnit-next/tests/browser_vertical_slice.py",
"apps/learnit-next/tests/build_determinism.py"}
GENERATED_DIRS=(APP_REL/"dist",APP_REL/"release",APP_REL/".agent-runtime",APP_REL/".agent-result")

def require_or_skip(condition,message):
    if condition:return
    if STRICT:raise RuntimeError(message)
    raise unittest.SkipTest(message)
def load_json(path):return json.loads(path.read_text(encoding="utf-8"))
def sha256_bytes(data):return hashlib.sha256(data).hexdigest()
def iter_strings(v):
    if isinstance(v,str):yield v
    elif isinstance(v,dict):
        for x in v.values():yield from iter_strings(x)
    elif isinstance(v,list):
        for x in v:yield from iter_strings(x)
def iter_string_lists(v):
    if isinstance(v,list):
        if v and all(isinstance(x,str) for x in v):yield v
        for x in v:yield from iter_string_lists(x)
    elif isinstance(v,dict):
        for x in v.values():yield from iter_string_lists(x)
def normalise_repo_path(entry):
    value=entry.replace("\\","/").lstrip("./")
    for candidate in (value,f"apps/learnit-next/{value}"):
        if candidate in PLANNED_BUILD_INPUTS:return candidate
    return None
def extract_ordered_sources(manifest):
    candidates=[]
    for values in iter_string_lists(manifest):
        n=[normalise_repo_path(x) for x in values]
        if all(x is not None for x in n) and set(n)==PLANNED_BUILD_INPUTS:candidates.append(n)
    if len(candidates)!=1:raise AssertionError(f"manifest must expose exactly one planned ordered list; found {len(candidates)}")
    if len(candidates[0])!=len(set(candidates[0])):raise AssertionError("duplicate manifest source")
    return candidates[0]
def extract_declared_artifact_paths(v):
    out=set()
    for s in iter_strings(v):
        n=s.replace("\\","/").lstrip("./")
        if n.endswith("dist/learnit-next.html"):out.add(ARTIFACT_REL.as_posix())
    return out
def extract_sha256_values(v):
    out=set()
    for s in iter_strings(v):
        c=s.lower();c=c[7:] if c.startswith("sha256:") else c
        if len(c)==64 and all(x in "0123456789abcdef" for x in c):out.add(c)
    return out
def source_tree_files(root):
    app=root/APP_REL;out=set()
    for rel in (Path("index.template.html"),Path("src")):
        target=app/rel
        if target.is_file():out.add(target.relative_to(root).as_posix())
        elif target.exists():out|={p.relative_to(root).as_posix() for p in target.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    return out
def assert_planned_source_tree(root):
    actual=source_tree_files(root);extra=sorted(actual-PLANNED_BUILD_INPUTS);missing=sorted(PLANNED_BUILD_INPUTS-actual)
    if extra or missing:raise AssertionError(f"source tree drift: extra={extra}, missing={missing}")
def clean_generated(root):
    for rel in GENERATED_DIRS:shutil.rmtree(root/rel,ignore_errors=True)
    for cache in list(root.rglob("__pycache__"))+list(root.rglob(".pytest_cache")):shutil.rmtree(cache,ignore_errors=True)
def copy_repository(destination):
    target=destination/"repo"
    def ignore(directory,names):
        ignored={".git","__pycache__",".pytest_cache"}&set(names)
        if Path(directory).name=="learnit-next":ignored|={"dist","release",".agent-runtime",".agent-result"}&set(names)
        return ignored
    shutil.copytree(ROOT,target,ignore=ignore);clean_generated(target);return target
def build_command(root):
    configured=os.environ.get("LEARNIT_NEXT_BUILD_COMMAND")
    return [p.format(repo=str(root)) for p in shlex.split(configured)] if configured else [sys.executable,str(root/BUILD_REL)]
def run_build(root):
    return subprocess.run(build_command(root),cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                          timeout=int(os.environ.get("LEARNIT_NEXT_BUILD_TIMEOUT","120")),check=False,
                          env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
def declaration_files(root):
    files=[root/MANIFEST_REL]
    for generated in (root/APP_REL/"dist",root/APP_REL/"release"):
        if generated.exists():files.extend(p for p in generated.rglob("*.json") if p.is_file())
    return list(dict.fromkeys(p for p in files if p.exists()))
def assert_artifact_declared(root,artifact_hash):
    joint=[]
    for path in declaration_files(root):
        try:payload=load_json(path)
        except (json.JSONDecodeError,UnicodeDecodeError):continue
        if ARTIFACT_REL.as_posix() in extract_declared_artifact_paths(payload) and artifact_hash in extract_sha256_values(payload):joint.append(path)
    if len(joint)!=1:raise AssertionError(f"exactly one declaration must bind artifact path and SHA-256; found {joint}")

class BuildHarnessOracleTests(unittest.TestCase):
    def test_file_plan_is_exact_and_assigns_the_seven_qa_paths(self):
        plan=load_json(ROOT/FILE_PLAN_REL);self.assertEqual(32,plan["workingFileBudget"]);self.assertEqual(QA_PATHS,set(plan["roles"]["qa-fixture-agent"]["paths"]))
        all_paths={e["path"] for e in plan["frozenSharedFiles"]}
        for role in plan["roles"].values():
            for path in role["paths"]:self.assertNotIn(path,all_paths);all_paths.add(path)
        self.assertEqual(32,len(all_paths))
    def test_manifest_source_extractor_is_shape_independent_and_order_preserving(self):
        ordered=sorted(PLANNED_BUILD_INPUTS,reverse=True);self.assertEqual(ordered,extract_ordered_sources({"arbitrary":{"ordered":ordered}}))
    def test_source_tree_auditor_rejects_an_unplanned_file(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for rel in PLANNED_BUILD_INPUTS:
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("planned")
            assert_planned_source_tree(root);probe=root/"apps/learnit-next/src/qa_unplanned_probe.js";probe.write_text("x")
            with self.assertRaisesRegex(AssertionError,"source tree drift"):assert_planned_source_tree(root)

class IntegratedBuildDeterminismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_or_skip((ROOT/BUILD_REL).exists() and (ROOT/MANIFEST_REL).exists(),
                        "WAITING_FOR_INTEGRATION: build.py and source_manifest.json are integrator-owned")
    def make_copy(self,parent,name):
        d=parent/name;d.mkdir();return copy_repository(d)
    def build(self,root):
        assert_planned_source_tree(root);manifest=load_json(root/MANIFEST_REL);self.assertEqual(PLANNED_BUILD_INPUTS,set(extract_ordered_sources(manifest)))
        p=run_build(root);self.assertEqual(0,p.returncode,p.stdout);artifact=root/ARTIFACT_REL;self.assertTrue(artifact.is_file())
        data=artifact.read_bytes();return data,sha256_bytes(data),p.stdout
    def test_two_clean_builds_and_browser_artifact_are_identical(self):
        proposed=Path(os.environ.get("LEARNIT_NEXT_ARTIFACT",ROOT/ARTIFACT_REL))
        require_or_skip(proposed.is_file(),f"WAITING_FOR_INTEGRATION: browser artifact absent at {proposed}")
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d);first=self.make_copy(parent,"first");second=self.make_copy(parent,"second")
            b1,h1,o1=self.build(first);b2,h2,o2=self.build(second);browser=proposed.read_bytes();hb=sha256_bytes(browser)
            self.assertEqual(b1,b2,f"clean builds differ\n{o1}\n{o2}");self.assertEqual(h1,h2);self.assertEqual(b1,browser,"browser-tested/proposed artifact differs from clean builds");self.assertEqual(h1,hb)
            assert_artifact_declared(first,h1);assert_artifact_declared(second,h2)
    def test_source_manifest_is_coherent_and_declares_the_tested_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.make_copy(Path(d),"declaration");before=(root/MANIFEST_REL).read_bytes();_,h,_=self.build(root)
            self.assertEqual(before,(root/MANIFEST_REL).read_bytes(),"build mutated source manifest");assert_artifact_declared(root,h)
    def test_build_fails_closed_when_an_unplanned_source_file_appears(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.make_copy(Path(d),"unplanned");(root/"apps/learnit-next/src/qa_unplanned_probe.js").write_text("throw Error('probe')")
            with self.assertRaisesRegex(AssertionError,"source tree drift"):assert_planned_source_tree(root)
            self.assertNotEqual(0,run_build(root).returncode,"build accepted unplanned source")
    def test_build_fails_closed_when_a_manifest_source_is_missing(self):
        with tempfile.TemporaryDirectory() as d:
            root=self.make_copy(Path(d),"missing");(root/"apps/learnit-next/src/core/identity.js").unlink()
            with self.assertRaisesRegex(AssertionError,"source tree drift"):assert_planned_source_tree(root)
            self.assertNotEqual(0,run_build(root).returncode,"build accepted missing declared source")

if __name__=="__main__":unittest.main(verbosity=2)
