#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(os.environ["PRODUCT_ROOT"])
INTEGRATION = ROOT / "apps/learnit-next/src/integration/atlas/session.js"
MANIFEST = ROOT / "apps/learnit-next/source_manifest.json"
SEAM_TEST = ROOT / "apps/learnit-next/tests/atlas_activity_ui_seam.py"
INT_TEST = ROOT / "apps/learnit-next/tests/atlas_m1_int.py"


def git_blob_sha1(data: bytes) -> str:
    prefix = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(prefix + data).hexdigest()


def update_integration() -> None:
    source = INTEGRATION.read_text(encoding="utf-8")

    if "function learnerSafeActivity(activity)" in source:
        raise RuntimeError("learner-safe activity projection already present")

    anchor = "function scoringAnswer(activity) {"
    if source.count(anchor) != 1:
        raise RuntimeError("scoringAnswer anchor drift")

    helper = '''function learnerSafeActivity(activity) {
  if (activity.type === 'qcm') {
    return Object.freeze({
      type: 'qcm',
      prompt: activity.prompt,
      choices: Object.freeze(
        activity.choices.map(choice => Object.freeze({
          choiceId: choice.choiceId,
          label: choice.label,
        })),
      ),
    });
  }

  if (activity.type === 'fill') {
    return Object.freeze({
      type: 'fill',
      prompt: activity.prompt,
      tokens: Object.freeze(
        activity.tokens.map(token => Object.freeze({
          tokenId: token.tokenId,
          label: token.label,
        })),
      ),
      segments: Object.freeze(
        activity.segments.map(segment => (
          Object.hasOwn(segment, 'text')
            ? Object.freeze({ text: segment.text })
            : Object.freeze({ slotId: segment.slotId })
        )),
      ),
    });
  }

  throw new Error(
    `ATLAS_ACTIVITY_TYPE_UNSUPPORTED: ${activity.type}`,
  );
}

'''
    source = source.replace(anchor, helper + anchor, 1)

    activity_block = '''      const activity =
        sourceActivity(
          context,
          item.activityRef,
        );

      const wrapper = node('div');
'''
    replacement = '''      const activity =
        sourceActivity(
          context,
          item.activityRef,
        );

      const presentation =
        learnerSafeActivity(activity);

      const wrapper = node('div');
'''
    if source.count(activity_block) != 1:
        raise RuntimeError("active activity block drift")
    source = source.replace(activity_block, replacement, 1)

    if source.count("renderAtlasActivityMarkup(activity)") != 1:
        raise RuntimeError("render call-site drift")
    source = source.replace(
        "renderAtlasActivityMarkup(activity)",
        "renderAtlasActivityMarkup(presentation)",
        1,
    )

    if source.count("readAtlasActivityResponse(wrapper, activity)") != 1:
        raise RuntimeError("response call-site drift")
    source = source.replace(
        "readAtlasActivityResponse(wrapper, activity)",
        "readAtlasActivityResponse(wrapper, presentation)",
        1,
    )

    INTEGRATION.write_text(source, encoding="utf-8")


def update_int_test() -> None:
    source = INT_TEST.read_text(encoding="utf-8")
    old = 'self.assertIn("renderAtlasActivityMarkup(activity)", session)'
    new = 'self.assertIn("renderAtlasActivityMarkup(presentation)", session)'
    if source.count(old) != 1:
        raise RuntimeError("Atlas M1 INT render seam oracle drift")
    INT_TEST.write_text(source.replace(old, new, 1), encoding="utf-8")


def write_seam_test() -> None:
    content = r'''#!/usr/bin/env python3
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
integration = (ROOT / "apps/learnit-next/src/integration/atlas/session.js").read_text(encoding="utf-8")
ui = (ROOT / "apps/learnit-next/src/ui/render.js").read_text(encoding="utf-8")
core = (ROOT / "apps/learnit-next/src/core/session.js").read_text(encoding="utf-8")

assert "from '../../ui/render.js'" in integration
assert "function learnerSafeActivity(activity)" in integration
assert "const presentation =\n        learnerSafeActivity(activity);" in integration
assert "renderAtlasActivityMarkup(presentation)" in integration
assert "readAtlasActivityResponse(wrapper, presentation)" in integration
assert "renderAtlasActivityMarkup(activity)" not in integration
assert "readAtlasActivityResponse(wrapper, activity)" not in integration
assert "function renderActivity(" not in integration
assert "function readResponse(" not in integration
assert "data-atlas-choice=\"true\"" not in integration
assert "[data-atlas-slot]" not in integration
assert "export function renderAtlasActivityMarkup" in ui
assert "export function readAtlasActivityResponse" in ui
assert "[data-atlas-choice=\"true\"]:checked" in ui
assert "[data-atlas-slot]" in ui
assert "querySelector" not in core
assert "document." not in core

match = re.search(
    r"function learnerSafeActivity\(activity\) \{.*?\n\}\n\nfunction scoringAnswer",
    integration,
    re.S,
)
assert match, "learnerSafeActivity implementation not found"
helper = match.group(0).rsplit("\n\nfunction scoringAnswer", 1)[0]

probe = helper + r'''
const forbidden = new Set([
  'correctChoiceId',
  'answers',
  'acceptedValues',
  'evaluator',
  'score',
  'scoringRuleId',
]);
function assertNoForbidden(value) {
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    if (forbidden.has(key)) {
      throw new Error(`FORBIDDEN_KEY_CROSSED_UI_BOUNDARY:${key}`);
    }
    assertNoForbidden(child);
  }
}
const qcm = {
  type: 'qcm',
  prompt: 'Prompt QCM',
  choices: [
    { choiceId: 'a', label: 'A', correctChoiceId: 'NESTED_SECRET' },
    { choiceId: 'b', label: 'B', acceptedValues: ['NESTED_SECRET'] },
  ],
  correctChoiceId: 'a',
  answers: ['SECRET'],
  acceptedValues: ['SECRET'],
  evaluator: 'SECRET',
  score: 'SECRET',
  scoringRuleId: 'SECRET',
};
const qcmPresentation = learnerSafeActivity(qcm);
assertNoForbidden(qcmPresentation);
if (JSON.stringify(Object.keys(qcmPresentation).sort()) !== JSON.stringify(['choices','prompt','type'])) {
  throw new Error('QCM_PRESENTATION_SHAPE_DRIFT');
}
if (JSON.stringify(Object.keys(qcmPresentation.choices[0]).sort()) !== JSON.stringify(['choiceId','label'])) {
  throw new Error('QCM_CHOICE_SHAPE_DRIFT');
}

const fill = {
  type: 'fill',
  prompt: 'Prompt fill',
  tokens: [
    { tokenId: 't1', label: 'T1', answers: ['NESTED_SECRET'], maxUses: 7 },
  ],
  segments: [
    { text: 'Avant ', acceptedValues: ['NESTED_SECRET'] },
    { slotId: 's1', evaluator: 'NESTED_SECRET' },
  ],
  correctChoiceId: 'SECRET',
  answers: { s1: 't1' },
  acceptedValues: ['SECRET'],
  evaluator: 'SECRET',
  score: 'SECRET',
  scoringRuleId: 'SECRET',
};
const fillPresentation = learnerSafeActivity(fill);
assertNoForbidden(fillPresentation);
if (JSON.stringify(Object.keys(fillPresentation).sort()) !== JSON.stringify(['prompt','segments','tokens','type'])) {
  throw new Error('FILL_PRESENTATION_SHAPE_DRIFT');
}
if (JSON.stringify(Object.keys(fillPresentation.tokens[0]).sort()) !== JSON.stringify(['label','tokenId'])) {
  throw new Error('FILL_TOKEN_SHAPE_DRIFT');
}
if (JSON.stringify(Object.keys(fillPresentation.segments[0]).sort()) !== JSON.stringify(['text'])) {
  throw new Error('FILL_TEXT_SEGMENT_SHAPE_DRIFT');
}
if (JSON.stringify(Object.keys(fillPresentation.segments[1]).sort()) !== JSON.stringify(['slotId'])) {
  throw new Error('FILL_SLOT_SEGMENT_SHAPE_DRIFT');
}
console.log('ATLAS_ACTIVITY_UI_SECRET_BOUNDARY_PASS');
'''
subprocess.run(
    ["node", "--input-type=module", "-e", probe],
    check=True,
    cwd=ROOT,
)

print("ATLAS_ACTIVITY_UI_SEAM_PASS")
'''
    SEAM_TEST.write_text(content, encoding="utf-8")


def rebind_manifest() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_path = {item["path"]: item for item in manifest["workingFiles"]}

    session_item = by_path.get("apps/learnit-next/src/integration/atlas/session.js")
    if session_item is None:
        raise RuntimeError("session.js manifest entry missing")
    session_item["fingerprint"]["kind"] = "git-blob-sha1"
    session_item["fingerprint"]["value"] = git_blob_sha1(INTEGRATION.read_bytes())
    session_item["owner"] = "ATLAS-LEARNING-SEAM"
    session_item["provenance"] = "post-R15 learner-safe activity presentation boundary"

    self_item = by_path.get("apps/learnit-next/source_manifest.json")
    if self_item is None:
        raise RuntimeError("manifest self entry missing")
    self_item["fingerprint"]["kind"] = "canonical-self-sha256"
    self_item["fingerprint"]["value"] = None
    self_item["owner"] = "ATLAS-LEARNING-SEAM"
    self_item["provenance"] = "post-R15 deterministic source rebind after secret-boundary repair"

    canonical = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    self_item["fingerprint"]["value"] = hashlib.sha256(canonical).hexdigest()

    MANIFEST.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
        encoding="utf-8",
    )


def main() -> None:
    update_integration()
    update_int_test()
    write_seam_test()
    rebind_manifest()
    print("ATLAS_WP_025_SECRET_BOUNDARY_REPAIR_APPLIED")


if __name__ == "__main__":
    main()
