#!/usr/bin/env python3
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class AtlasM2StaticContractTests(unittest.TestCase):
    def test_no_new_storage_or_network_surface(self):
        adapter = (ROOT / 'src/adapters/atlas_indexeddb.js').read_text(encoding='utf-8')
        memory = (ROOT / 'src/core/atlas_memory.js').read_text(encoding='utf-8')
        authority = (ROOT / 'src/core/atlas_claim_authority.js').read_text(encoding='utf-8')
        self.assertIn("const DATABASE = 'learnit_atlas_m1_v2'", adapter)
        self.assertIn("const VERSION = 1", adapter)
        self.assertIn("'learningEvents'", adapter)
        self.assertIn("'scoredExecutions'", adapter)
        self.assertIn("'resumeStates'", adapter)
        self.assertIn("'atlasMeta'", adapter)
        joined = '\n'.join([memory, authority])
        for forbidden in ('fetch(', 'XMLHttpRequest', 'WebSocket', 'EventSource', 'localStorage.setItem'):
            self.assertNotIn(forbidden, joined)

    def test_product_does_not_author_qa_or_transfer_semantics(self):
        recommendation = (ROOT / 'src/core/atlas_recommendation.js').read_text(encoding='utf-8')
        surface = (ROOT / 'src/integration/atlas/surface.js').read_text(encoding='utf-8')
        self.assertNotIn('transfer-completed', recommendation)
        self.assertNotIn('transfer-completed', surface)
        self.assertNotIn('qa_atlas_m2', surface)
        self.assertNotIn('qa_atlas_m2', recommendation)


if __name__ == '__main__':
    unittest.main(verbosity=2)
