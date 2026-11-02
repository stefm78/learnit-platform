"""Minimal independent checks for read-only, canonical module reuse."""
from pathlib import Path
import unittest
BASE=Path(__file__).resolve().parents[1]

class Structure(unittest.TestCase):
 def test_reuse_canonical_sources(self):
  source=(BASE/'explorer.js').read_text()
  for expected in ('projectActivityPresentation(active,{assets:kit.assets??[],contract:kit.contract,readOnlyHintPreview:true})',
                   'renderActivityPresentation(presentation)',
                   'readActivityResponse(ui.preview,presentation)',
                   'evaluateActivityResponse(active,answer)'):
   self.assertIn(expected,source)
  self.assertNotIn('JSON.stringify(active',source)
  self.assertNotIn('localStorage',source)
  self.assertNotIn('fetch(',source)
 def test_original_learner_modules_exist(self):
  root=BASE.parents[1]
  if not (root/"apps/learnit-next/src").exists(): self.skipTest("Canonical Git checkout not present locally; GitHub CI will verify")
  for name in ('apps/learnit-next/src/ui/activity_presenters.js',
               'apps/learnit-next/src/ui/media.js',
               'apps/learnit-next/src/integration/atlas/activity_projection.js',
               'apps/learnit-next/src/core/activity_semantics.js',
               'apps/learnit-next/src/styles.css'):
   self.assertTrue((root/name).is_file(),name)
 def test_no_kit_distribution(self):
  self.assertEqual(list(BASE.glob('*.json')),[])
  html=(BASE/'index.html').read_text()
  self.assertIn('connect-src \'none\'',html)
  self.assertNotIn('https://',html)

if __name__=='__main__':unittest.main()
