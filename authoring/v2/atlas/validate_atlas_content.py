#!/usr/bin/env python3
"""Validate the two canonical Atlas M1 learnit.kit.v2 content packages."""
from __future__ import annotations

import argparse, copy, importlib.util, json, re, sys, unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT = tuple(ROOT / f"authoring/v2/atlas/{name}" for name in (
    "nombres_complexes_atlas.json", "signaux_electriques_atlas.json"))
BASE_PATH = ROOT / "authoring/v2/validate_kit.py"
SCHEMA = ROOT / "contracts/learnit-kit-v2.schema.json"
DURATIONS = (5, 15, 30)
SEQUENCE = (
    ("activation", "practice"), ("application", "practice"),
    ("consolidation", "practice"), ("validation", "validation"),
    ("transfer", "practice"),
)
BAD = re.compile(r"(?i)(?:\bTODO\b|\bTBD\b|\bDEBUG\b|\bundefined\b|\bNaN\b|\[BLANK\])")
URL = re.compile(r"(?i)\b(?:https?://|www\.)")

# package lineage, then duration -> (course lineage, objective lineage, ordered activity lineages)
FROZEN = {
 "nombres_complexes_atlas.json":("18161c92-758d-4616-820e-10f3e72e2cac",{
  5:("d487a74e-8e13-457e-bd83-2b7ffe77925e","390ab376-58de-4426-8288-c13e57851652","d515847e-8318-4a11-80af-cd8ec7eb8115 e184de0b-d41f-428c-bc92-788ab4d99ca5 4529a810-7bdd-45b4-9f88-5d328e7fb98e a4bcf41a-4968-4056-a8db-bd7d839badd0 0b2494f6-8fe4-41e1-9824-c8c7134500be".split()),
  15:("0f733b7c-461b-4d29-b7e0-a2fd4e1df089","ab97ee5c-a4ae-48f6-9010-38d543d62793","2eeae459-0d02-4127-aeac-9edf4ccea8a4 4bacbbeb-39d9-4b12-b377-35be5488a3eb bbe0ec8f-a717-4819-9461-dd3ace2bc497 5f6c87da-d059-4d96-83e5-c1706af4b3af 1ade5666-5944-48b0-9365-885f63c12d02".split()),
  30:("368fa0a0-2a57-410e-b892-0f423edcb6b1","faf8eb35-e35c-4fa5-985c-b51dfd958d5d","45789f55-592d-490d-b905-d9fd3448834f c8366bb1-e865-42e4-b1bf-6b9876d1093d a3b1f94b-acfa-42d7-8304-675f45eae5c4 eb150a35-4136-4dfd-8ea6-4aaf0c79c725 e74c04c6-c968-4a58-9d38-af9f66b8208b".split())}),
 "signaux_electriques_atlas.json":("86bf2506-f4a9-4bd7-a03e-1644fd034471",{
  5:("cd6e15b4-4e5b-43f8-992e-539656837b5f","a620f24f-9ae4-40f3-8ef9-57a7d2c19200","3e9dff6c-93e6-4680-9041-46c81669cd1b a03325a7-5d48-43c0-bc98-fe21bb83f33d 741470f5-85ce-4f96-8297-d374b0a4baf2 d07aaf4b-53ff-4284-8e0f-b7064446f240 357aff7e-553b-4bce-a081-cafd5ea9ba71".split()),
  15:("44fe5c7e-5fea-4af1-888f-150382503d45","a545d602-aa7e-4b0e-b36e-35f6e2716a6b","23855c6a-c973-45ae-aa01-cf1a0d961251 932544f5-21d1-4e14-9fef-b0b0d63b2d63 51e1113e-0a6e-4cea-8f60-4b4cd3914eef 81e219d2-c54c-4ba2-867a-252a2eec7a9a cdaa23e5-2664-4cbf-b0c1-1560d7393b84".split()),
  30:("78f7e66b-f80d-460e-8bcc-d37f58d213d3","0340451e-d736-407c-a03b-387da8b38027","4b107e0d-6fb0-48af-a6ad-e28b44396f83 e3e971c5-eb9e-48aa-ad0a-569c48bcf116 adf402df-c2e7-46fc-85cc-1dd5713f2778 6cfd9228-625e-4651-be66-5df04dc779cf bd210788-56b9-43d4-a4c5-7a3c990cd968".split())})}

spec = importlib.util.spec_from_file_location("learnit_v2_validator", BASE_PATH)
if spec is None or spec.loader is None: raise RuntimeError(f"cannot load {BASE_PATH}")
BASE = importlib.util.module_from_spec(spec); sys.modules[spec.name] = BASE; spec.loader.exec_module(BASE)

@dataclass
class Report:
 path: Path
 errors: list[str] = field(default_factory=list)
 warnings: list[str] = field(default_factory=list)
 courses: list[dict] = field(default_factory=list)
 @property
 def ok(self): return not self.errors

def error(r, path, message, value=None):
 suffix = "" if value is None else "; value=" + json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
 r.errors.append(f"{path}: {message}{suffix}")

def scan(r, value, path="$"):
 if isinstance(value, str):
  if BAD.search(value): error(r, path, "unresolved placeholder is forbidden", value)
  if URL.search(value): error(r, path, "remote URL is forbidden", value)
 elif isinstance(value, list):
  for i, item in enumerate(value): scan(r, item, f"{path}[{i}]")
 elif isinstance(value, dict):
  for key, item in value.items(): scan(r, item, f"{path}.{key}")

def normalized(text): return unicodedata.normalize("NFC", " ".join(text.split())).casefold()

def check_course(r, course, index):
 path=f"$.courses[{index}]"; duration=course.get("estimatedMinutes")
 objectives=course.get("objectives",[]); activities=course.get("activities",[])
 if duration not in DURATIONS: error(r,path+".estimatedMinutes","Atlas M1 requires 5, 15 or 30",duration)
 if not isinstance(objectives,list) or len(objectives)!=1: error(r,path+".objectives","each profile must expose exactly one explicit objective",objectives)
 if not isinstance(activities,list) or len(activities)!=5: error(r,path+".activities","each profile must contain exactly five ordered activities",activities)
 objective_id=objectives[0].get("objectiveId") if len(objectives)==1 and isinstance(objectives[0],dict) else None
 actual=[]
 for i, activity in enumerate(activities if isinstance(activities,list) else []):
  if not isinstance(activity,dict): continue
  actual.append((activity.get("learningPhase"),activity.get("assessmentRole")))
  if activity.get("objectiveIds") != [objective_id]: error(r,f"{path}.activities[{i}].objectiveIds","activity must reference exactly the profile objective",activity.get("objectiveIds"))
  seen={}
  for j, choice in enumerate(activity.get("choices",[]) if isinstance(activity.get("choices",[]),list) else []):
   label=choice.get("label") if isinstance(choice,dict) else None
   if isinstance(label,str):
    key=normalized(label)
    if key in seen: error(r,f"{path}.activities[{i}].choices[{j}].label","ambiguous duplicate label",label)
    else: seen[key]=j
 if actual != list(SEQUENCE): error(r,path+".activities","objective sequence must be training <= error < correction < validation < transfer",actual)
 r.courses.append({"estimatedMinutes":duration,"activities":len(activities) if isinstance(activities,list) else 0,"objectives":[{"objectiveId":objective_id,"training":[0,1],"errorOpportunity":[1],"correction":[2],"validation":[3],"transfer":[4]}]})

def check_frozen(r, document):
 expected=FROZEN.get(r.path.name)
 if not expected: r.warnings.append(f"$: no frozen identity manifest for {r.path.name!r}"); return
 package, profiles=expected
 if document.get("packageLineageId") != package: error(r,"$.packageLineageId","canonical package lineage drift")
 by_duration={c.get("estimatedMinutes"):c for c in document.get("courses",[]) if isinstance(c,dict)}
 for duration,(course_id,objective_id,activity_ids) in profiles.items():
  course=by_duration.get(duration); prefix=f"$.courses[estimatedMinutes={duration}]"
  if not course: error(r,"$.courses",f"missing canonical {duration} minute profile"); continue
  if course.get("courseLineageId") != course_id: error(r,prefix+".courseLineageId","canonical course lineage drift")
  if [o.get("objectiveId") for o in course.get("objectives",[]) if isinstance(o,dict)] != [objective_id]: error(r,prefix+".objectives","canonical objective identity or order drift")
  actual=[a.get("activityLineageId") for a in course.get("activities",[]) if isinstance(a,dict)]
  if actual != activity_ids: error(r,prefix+".activities","canonical activity lineage identity or order drift",actual)

def validate_document(path, document):
 r=Report(Path(path)); baseline=BASE.validate(Path(path),document,BASE.load(SCHEMA),False)
 r.errors.extend(baseline.errors); r.warnings.extend(baseline.warnings); scan(r,document)
 courses=document.get("courses",[])
 if not isinstance(courses,list) or len(courses)!=3: error(r,"$.courses","must contain exactly the 5, 15 and 30 minute profiles",courses); courses=courses if isinstance(courses,list) else []
 for i,course in enumerate(courses):
  if isinstance(course,dict): check_course(r,course,i)
 durations=[c.get("estimatedMinutes") for c in courses if isinstance(c,dict)]
 if durations != list(DURATIONS): error(r,"$.courses","session profiles must be ordered exactly 5, 15, 30 minutes",durations)
 check_frozen(r,document); return r

def validate_paths(paths):
 reports=[]
 for path in paths:
  try: reports.append(validate_document(Path(path),BASE.load(Path(path))))
  except Exception as exc: report=Report(Path(path)); report.errors.append(f"{path}: invalid UTF-8 JSON: {exc}"); reports.append(report)
 return reports

def refresh_digests(document):
 output=copy.deepcopy(document)
 for course in output.get("courses",[]):
  for activity in course.get("activities",[]): activity["activityRevisionDigest"]=BASE.digest(activity,"activityRevisionDigest")[0]
  course["courseRevisionDigest"]=BASE.digest(course,"courseRevisionDigest")[0]
 output["packageRevisionDigest"]=BASE.digest(output,"packageRevisionDigest")[0]; return output

def payload(reports): return {"ok":all(r.ok for r in reports),"files":[{"path":str(r.path),"ok":r.ok,"errors":r.errors,"warnings":r.warnings,"profiles":r.courses} for r in reports]}
def human(reports):
 lines=[]
 for r in reports:
  lines += [f"FILE {r.path}",f"  status: {'PASS' if r.ok else 'FAIL'}"]
  lines += [f"  profile {c['estimatedMinutes']} min: activities={c['activities']}, complete-objective-loops=1/1" for c in r.courses]
  lines += ["  WARNING: "+x for x in r.warnings]+["  ERROR: "+x for x in r.errors]
 lines.append("OVERALL "+("PASS" if all(r.ok for r in reports) else "FAIL")); return "\n".join(lines)
def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("kits",nargs="*",type=Path,default=list(DEFAULT)); parser.add_argument("--format",choices=("human","json"),default="human")
 args=parser.parse_args(argv); reports=validate_paths(args.kits); print(json.dumps(payload(reports),ensure_ascii=False,indent=2,sort_keys=True) if args.format=="json" else human(reports)); return 0 if all(r.ok for r in reports) else 1
if __name__=="__main__": raise SystemExit(main())
