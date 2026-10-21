#!/usr/bin/env python3
"""R4 safety regression: OneDrive displayed links must match canonical Graph IDs."""
import unittest
from tools.refresh_onedrive_catalogue import item_locator_matches
ID = "B9B0D852F6CCE2CD!s54e6af3c56804b60aa5548e307c84875"
GRAPH = "https://graph.microsoft.com/v1.0/drives/B9B0D852F6CCE2CD/items/B9B0D852F6CCE2CD%21s54e6af3c56804b60aa5548e307c84875"
class ExactItemBinding(unittest.TestCase):
    def test_graph_locator(self):
        self.assertTrue(item_locator_matches({"item_id": ID, "graph_locator": GRAPH}))
    def test_legacy_graph_url(self):
        self.assertTrue(item_locator_matches({"item_id": ID, "graph_url": GRAPH}))
    def test_wrong_id(self):
        self.assertFalse(item_locator_matches({"item_id": ID[:-1] + "0", "graph_locator": GRAPH}))
    def test_wrong_graph_host(self):
        self.assertFalse(item_locator_matches({"item_id": ID, "graph_url": GRAPH.replace("graph.microsoft.com", "not-microsoft.example")}))
    def test_malformed_id(self):
        self.assertFalse(item_locator_matches({"item_id": "attacker", "graph_locator": GRAPH}))
    def test_extra_url_suffix(self):
        self.assertFalse(item_locator_matches({"item_id": ID, "graph_locator": GRAPH + "/unexpected"}))
if __name__ == "__main__": unittest.main()
