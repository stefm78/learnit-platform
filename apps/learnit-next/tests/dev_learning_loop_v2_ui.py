#!/usr/bin/env python3
"""Developer checks for Learning Loop V2 isolated objective-progress UI helpers."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "apps/learnit-next/src/ui/objective_progress.js"
STYLES = ROOT / "apps/learnit-next/src/styles.css"

DOM_HARNESS = r"""
class FakeNode {
  constructor(tagName) {
    this.tagName = tagName;
    this.attributes = new Map();
    this.childNodes = [];
    this._text = '';
    this.listeners = new Map();
  }
  set className(value) { this.setAttribute('class', value); }
  get className() { return this.attributes.get('class') || ''; }
  set textContent(value) { this._text = String(value); this.childNodes = []; }
  get textContent() { return this._text + this.childNodes.map(child => child.textContent).join(''); }
  setAttribute(name, value) { this.attributes.set(String(name), String(value)); }
  getAttribute(name) { return this.attributes.get(String(name)) ?? null; }
  appendChild(child) {
    if (!(child instanceof FakeNode)) throw new TypeError('FakeNode child required');
    this.childNodes.push(child);
    return child;
  }
  addEventListener(name, listener) { this.listeners.set(name, listener); }
  click() { this.listeners.get('click')?.({type: 'click'}); }
  get outerHTML() {
    const attrs = [...this.attributes.entries()]
      .map(([name, value]) => ` ${name}="${escapeHtml(value)}"`).join('');
    const content = escapeHtml(this._text) + this.childNodes.map(child => child.outerHTML).join('');
    return `<${this.tagName}${attrs}>${content}</${this.tagName}>`;
  }
}
function escapeHtml(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}
class FakeDocument { createElement(tag) { return new FakeNode(tag); } }
const documentRef = new FakeDocument();
"""

NODE_TESTS = r"""
import assert from 'node:assert/strict';
import {
  OBJECTIVE_PROGRESS_STATUSES,
  getObjectiveStatusPresentation,
  renderObjectiveProgressItem,
  renderObjectiveProgressList,
  renderRecommendedAction,
  renderObjectiveProgressPanel,
} from './objective_progress.mjs';

__DOM_HARNESS__

const progress = (objectiveId, status, overrides = {}) => ({
  objectiveId,
  trainingAttempts: 1,
  latestTrainingCorrect: true,
  needsReview: false,
  validationAttempts: 0,
  latestValidationCorrect: null,
  status,
  ...overrides,
});

const results = [];
async function test(name, fn) {
  try { await fn(); results.push({name, status: 'PASS'}); }
  catch (error) { results.push({name, status: 'FAIL', error: String(error?.stack || error)}); }
}

await test('01 status vocabulary and all supported states', () => {
  assert.deepEqual(OBJECTIVE_PROGRESS_STATUSES, [
    'not-started', 'training', 'review-needed', 'ready-for-validation', 'validated-recently',
  ]);
  assert.equal(getObjectiveStatusPresentation('training').label, 'En entraînement');
  assert.equal(getObjectiveStatusPresentation('review-needed').label, 'Révision nécessaire');
  assert.equal(getObjectiveStatusPresentation('ready-for-validation').label, 'Prêt pour validation');
  assert.equal(getObjectiveStatusPresentation('validated-recently').label, 'Validation récente');
  assert.throws(() => getObjectiveStatusPresentation('unknown'), RangeError);
});

await test('02 generated objective HTML is semantic and readable without colour', () => {
  const item = renderObjectiveProgressItem(progress('obj-1', 'review-needed', {
    trainingAttempts: 2,
    latestTrainingCorrect: false,
    needsReview: true,
  }), {documentRef, label: 'Résoudre une équation'});
  const html = item.outerHTML;
  assert.match(html, /^<article/);
  assert.match(html, /aria-labelledby=/);
  assert.match(html, /aria-describedby=/);
  assert.match(html, /data-progress-status="review-needed"/);
  assert.match(html, /État : <\/span><strong>Révision nécessaire<\/strong>/);
  assert.match(html, /Révision à effectuer<\/dt><dd>Oui<\/dd>/);
  assert.match(html, /Dernier entraînement<\/dt><dd>À reprendre<\/dd>/);
});

await test('03 list preserves input reading order and authored labels', () => {
  const objectives = [
    progress('obj-b', 'training'),
    progress('obj-a', 'ready-for-validation'),
    progress('obj-c', 'validated-recently', {validationAttempts: 1, latestValidationCorrect: true}),
  ];
  const list = renderObjectiveProgressList(objectives, {
    documentRef,
    labelsById: new Map([
      ['obj-b', 'Deuxième dans le contrat'],
      ['obj-a', 'Premier identifiant lexical'],
      ['obj-c', 'Dernier objectif'],
    ]),
  });
  const html = list.outerHTML;
  const first = html.indexOf('Deuxième dans le contrat');
  const second = html.indexOf('Premier identifiant lexical');
  const third = html.indexOf('Dernier objectif');
  assert.ok(first > 0 && first < second && second < third);
  assert.equal((html.match(/<li/g) || []).length, 3);
});

await test('04 objective and recommendation empty states are explicit', () => {
  const list = renderObjectiveProgressList([], {documentRef});
  assert.match(list.outerHTML, /role="status"/);
  assert.match(list.outerHTML, /Aucun objectif à afficher pour le moment/);
  assert.doesNotMatch(list.outerHTML, /<ol/);
  const action = renderRecommendedAction(null, {documentRef});
  assert.match(action.outerHTML, /Aucune action recommandée pour le moment/);
  assert.doesNotMatch(action.outerHTML, /<button|<a/);
});

await test('05 recommendation renders native keyboard controls only when actionable', () => {
  const link = renderRecommendedAction({
    title: 'Reprendre une activité',
    description: 'Une activité demande une nouvelle tentative.',
    actionLabel: 'Ouvrir la révision',
    actionKey: 'review',
    objectiveId: 'obj-1',
    status: 'review-needed',
    href: '#review',
  }, {documentRef, labelsById: {'obj-1': 'Résoudre une équation'}});
  assert.match(link.outerHTML, /<a[^>]+href="#review"/);
  assert.match(link.outerHTML, /Objectif : Résoudre une équation/);

  let received = null;
  const recommendation = {
    title: 'Continuer l’entraînement',
    description: 'Une activité d’entraînement est disponible.',
    actionLabel: 'Continuer',
    actionKey: 'training',
  };
  const buttonSection = renderRecommendedAction(recommendation, {
    documentRef,
    onAction: value => { received = value; },
  });
  const button = buttonSection.childNodes[1].childNodes.at(-1);
  assert.equal(button.tagName, 'button');
  assert.equal(button.getAttribute('type'), 'button');
  button.click();
  assert.equal(received, recommendation);
});

await test('06 panel reading order is objectives then next action', () => {
  const panel = renderObjectiveProgressPanel({
    objectives: [progress('obj-1', 'training')],
    recommendation: {
      title: 'Continuer l’entraînement',
      description: 'Une activité est disponible.',
      actionLabel: 'Continuer',
    },
  }, {documentRef});
  const html = panel.outerHTML;
  assert.ok(html.indexOf('Progression par objectif') < html.indexOf('Prochaine action recommandée'));
});

await test('07 input data is validated and not mutated', () => {
  const source = progress('obj-1', 'training');
  const before = JSON.stringify(source);
  renderObjectiveProgressItem(source, {documentRef});
  assert.equal(JSON.stringify(source), before);
  assert.throws(() => renderObjectiveProgressItem({...source, trainingAttempts: -1}, {documentRef}), TypeError);
  assert.throws(() => renderObjectiveProgressList({}, {documentRef}), TypeError);
  assert.throws(() => renderRecommendedAction({title: '', description: 'x'}, {documentRef}), TypeError);
});

const failed = results.filter(result => result.status !== 'PASS');
console.log(JSON.stringify({tests: results.length, passed: results.length - failed.length, failed}, null, 2));
if (failed.length) process.exit(1);
"""


class LearningLoopV2UiTests(unittest.TestCase):
    maxDiff = None

    def run_node_suite(self) -> dict[str, object]:
        self.assertTrue(MODULE.is_file(), MODULE)
        if shutil.which("node") is None:
            self.skipTest("node is required")
        with tempfile.TemporaryDirectory(prefix="learnit-llv2-ui-") as temp_dir:
            temp = Path(temp_dir)
            shutil.copyfile(MODULE, temp / "objective_progress.mjs")
            harness = NODE_TESTS.replace("__DOM_HARNESS__", DOM_HARNESS)
            (temp / "ui_test.mjs").write_text(harness, encoding="utf-8")
            result = subprocess.run(
                ["node", "ui_test.mjs"],
                cwd=temp,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            return json.loads(result.stdout)

    def test_dom_helpers(self) -> None:
        report = self.run_node_suite()
        self.assertEqual(report["tests"], 7)
        self.assertEqual(report["passed"], 7)
        self.assertEqual(report["failed"], [])

    def test_css_accessibility_and_mobile_contract(self) -> None:
        css = STYLES.read_text(encoding="utf-8")
        required = (
            ".objective-progress-panel",
            ".objective-progress__item--training",
            ".objective-progress__item--review-needed",
            ".objective-progress__item--ready-for-validation",
            ".objective-progress__item--validated-recently",
            ".objective-recommendation__action:focus-visible",
            "min-height: 44px",
            "@media (max-width: 520px)",
            "overflow-wrap: anywhere",
        )
        for fragment in required:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, css)
        self.assertNotIn("outline: none", css)
        self.assertNotIn("outline: 0", css)

    def test_visible_copy_stays_within_product_state_boundary(self) -> None:
        visible_sources = MODULE.read_text(encoding="utf-8").casefold()
        disallowed = (
            "ma" + "îtrise",
            "certi" + "fication",
            "rét" + "ention",
            "apprentissage " + "durable",
        )
        for phrase in disallowed:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, visible_sources)


if __name__ == "__main__":
    unittest.main(verbosity=2)
