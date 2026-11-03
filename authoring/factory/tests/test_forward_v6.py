"""Forward assembler unit regressions. Real V6 validator/Node/Edge/T2 are separate gates."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from authoring.factory import forward_v6 as f


class FakeReport:
    ok = True
    errors = []


def valid_digest(document):
    for course in document["courses"]:
        for activity in course["activities"]:
            expected = "sha256:" + hashlib.sha256(json.dumps({k:v for k,v in activity.items() if k != "activityRevisionDigest"},sort_keys=True,separators=(",", ":"),ensure_ascii=False).encode()).hexdigest()
            if activity["activityRevisionDigest"] != expected:
                return ["activity digest drift"]
        expected = "sha256:" + hashlib.sha256(json.dumps({k:v for k,v in course.items() if k != "courseRevisionDigest"},sort_keys=True,separators=(",", ":"),ensure_ascii=False).encode()).hexdigest()
        if course["courseRevisionDigest"] != expected:
            return ["course digest drift"]
    document["packageRevisionDigest"] = "sha256:" + hashlib.sha256(json.dumps({k:v for k,v in document.items() if k != "packageRevisionDigest"},sort_keys=True,separators=(",", ":"),ensure_ascii=False).encode()).hexdigest()
    return []


class ForwardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.kit = self.d/"kit.json"; self.brief = self.d/"brief.json"; self.sources = self.d/"sources.json"; self.manifest = self.d/"manifest.json"
        act = {"activityLineageId":"a1", "activityRevisionId":"a2", "activityRevisionDigest":"", "assessmentRole":"validation"}
        course = {"courseLineageId":"c1", "courseRevisionId":"c2", "courseRevisionDigest":"", "objectives":[{"objectiveId":"o1"}], "activities":[act]}
        kit = {"contract":"learnit.kit.v6", "packageLineageId":"old-lineage", "packageRevisionId":"old-revision", "packageRevisionDigest":"old-digest", "assets":[], "courses":[course]}
        act["activityRevisionDigest"] = "sha256:" + hashlib.sha256(json.dumps({k:v for k,v in act.items() if k != "activityRevisionDigest"},sort_keys=True,separators=(",", ":"),ensure_ascii=False).encode()).hexdigest()
        course["courseRevisionDigest"] = "sha256:" + hashlib.sha256(json.dumps({k:v for k,v in course.items() if k != "courseRevisionDigest"},sort_keys=True,separators=(",", ":"),ensure_ascii=False).encode()).hexdigest()
        self.kit.write_bytes(f.canonical(kit))
        self.brief.write_bytes(f.canonical({"schema":"learnit.atlas.learner_brief.v1"}))
        self.sources.write_bytes(f.canonical({"schema":"learnit.atlas.v6_source_manifest.v1"}))
        self.frozen = f.freeze(self.kit,self.brief,self.sources)
        self.manifest.write_bytes(f.canonical(self.frozen))
        self.check = f.sha(self.manifest.read_bytes())

    def execute(self, digest=None):
        with patch("authoring.v6.validator_runtime.fill_new_digests", valid_digest), patch("authoring.v6.validator_runtime.validate_document", return_value=FakeReport()):
            return f.assemble(self.kit,self.brief,self.sources,self.manifest,digest or self.check)

    def test_replay_and_nested_content_identity(self):
        a,kit = self.execute(); b,_ = self.execute()
        self.assertEqual(a,b)
        self.assertEqual(kit["courses"],json.loads(self.kit.read_text())["courses"])
        f.require_uuid4(kit["packageLineageId"]); f.require_uuid4(kit["packageRevisionId"])
        self.assertNotEqual(kit["packageRevisionDigest"],"old-digest")

    def test_source_and_brief_exact_byte_drift_fail(self):
        self.brief.write_bytes(self.brief.read_bytes()+b"\n")
        with self.assertRaisesRegex(f.ForwardV6Error,"drift"):
            self.execute()

    def test_manifest_sha_and_uuid_fail(self):
        with self.assertRaisesRegex(f.ForwardV6Error,"SHA-256 mismatch"):
            self.execute("0"*64)
        for field,value in (("packageLineageId","aa215370-06ed-5693-965c-3622bb62e35a"),("packageRevisionId",self.frozen["packageLineageId"])):
            invalid=copy.deepcopy(self.frozen);invalid[field]=value
            self.manifest.write_bytes(f.canonical(invalid))
            with self.assertRaises(f.ForwardV6Error):
                self.execute(f.sha(self.manifest.read_bytes()))

    def test_mismatched_nested_digest_fails(self):
        kit=json.loads(self.kit.read_text());kit["courses"][0]["activities"][0]["activityRevisionDigest"]="sha256:"+"a"*64
        self.kit.write_bytes(f.canonical(kit))
        new=f.freeze(self.kit,self.brief,self.sources);self.manifest.write_bytes(f.canonical(new))
        with self.assertRaisesRegex(f.ForwardV6Error,"digest failure"):
            self.execute(f.sha(self.manifest.read_bytes()))

    def test_duplicate_json_keys_fail(self):
        self.brief.write_bytes(b'{"schema":"learnit.atlas.learner_brief.v1","schema":"other"}')
        with self.assertRaisesRegex(f.ForwardV6Error,"duplicate JSON key"):
            self.execute()


if __name__ == "__main__":
    unittest.main()
