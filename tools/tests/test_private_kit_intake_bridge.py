"""Portable offline unit tests; NO credentials/network/remote mutation."""
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'private_kit_intake_bridge.py'
spec = importlib.util.spec_from_file_location('private_kit_intake_bridge', MODULE)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
LINEAGE = 'aa215370-06ed-5693-965c-3622bb62e35a'
REV = '9bb3927d-3535-5ddb-8080-8fa2ec443627'


def fixture(directory):
    kit = {'contract':'learnit.kit.v6','packageLineageId':LINEAGE,'packageRevisionId':REV,
           'packageRevisionDigest':'sha256:'+'2'*64,'title':'Fixture pédagogique',
           'courses':[{'activities':[{'title':'a'}]}]}
    raw = (json.dumps(kit,ensure_ascii=False)+'\n').encode()
    entry = {'packageLineageId':LINEAGE,'packageRevisionId':REV,
             'packageRevisionDigest':kit['packageRevisionDigest'],
             'kit':{'bytes':len(raw),'sha256':m.digest(raw)},
             'factoryRun':{'runId':'fixture-run'}}
    man = {'schema':m.VERIFIED_SCHEMA,'entries':[entry],'releaseSetId':'sha256:'+'3'*64,
           'factoryAuthority':'0'*40}
    path=directory/'release.zip'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr(f'kits/{LINEAGE}/{REV}.json',raw)
    evidence={'schema':'learnit.atlas.qualified_release_set_result.v2',
              'verdict':m.RELEASE_PASS,'releaseSha256':m.digest(path.read_bytes()),
              'releaseBytes':path.stat().st_size,'manifest':man}
    return path,evidence,raw


def index_template(sha):
    return {'schema':'learnit.private-kit-index.verification-snapshot.v1',
            'authority':False,'distribution_authorized':False,'entries':[
            {'lineage_id':LINEAGE,'revision_id':REV,'kit_sha256':sha[7:],
            'private_storage_status':'STORED_PRIVATE_VERIFIED'}]}


class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path,self.evidence,self.raw=fixture(Path(self.tmp.name))

    def plan(self,**kw):return m.prepare(self.path,self.evidence,**kw)

    def test_builds_private_plan(self):
        plan, files=self.plan()
        self.assertEqual(len(plan['entries']),1)
        self.assertEqual(files[plan['entries'][0]['destination']],self.raw)
        self.assertFalse(plan['authority'])
        self.assertFalse(plan['write_permissions_conferred'])
        self.assertEqual(plan['entries'][0]['activities'],1)
        self.assertEqual(plan['entries'][0]['distribution_status'],'NOT_AUTHORIZED')

    def test_no_side_effects(self):
        before=set(Path(self.tmp.name).iterdir())
        self.plan()
        self.assertEqual(set(Path(self.tmp.name).iterdir()),before)

    def test_reject_unverified_verdict(self):
        with self.assertRaisesRegex(m.Hold,'CANONICAL_RELEASE'):
            m.prepare(self.path,{**self.evidence,'verdict':'PASS'})

    def test_reject_incorrect_schema(self):
        with self.assertRaises(m.Hold):
            m.prepare(self.path,{**self.evidence,'schema':'unknown'})

    def test_reject_tampered_release_digest(self):
        with self.assertRaisesRegex(m.Hold,'ARCHIVE_CHANGED'):
            m.prepare(self.path,{**self.evidence,'releaseSha256':'sha256:'+'0'*64})

    def test_reject_tampered_release_size(self):
        with self.assertRaisesRegex(m.Hold,'ARCHIVE_CHANGED'):
            m.prepare(self.path,{**self.evidence,'releaseBytes':1})

    def test_reject_bad_file_names(self):
        for filename in ('../abc.json','a/b.json','a.html','PRIVATE_INDEX.json','NAVIGUER_KITS.html'):
            with self.subTest(filename=filename),self.assertRaisesRegex(m.Hold,'UNSAFE_FILENAME'):
                self.plan(filenames={LINEAGE:filename})

    def test_reject_mismatched_manifest_revision(self):
        e={**self.evidence,'manifest':{**self.evidence['manifest']}}
        e['manifest']['entries']=[{**e['manifest']['entries'][0],'packageRevisionId':'0'*8+'-'+REV[9:]}]
        with self.assertRaisesRegex(m.Hold,'MISMATCH|BYTES'):
            m.prepare(self.path,e)

    def test_reject_duplicate_release_identity(self):
        e={**self.evidence,'manifest':{**self.evidence['manifest']}}
        e['manifest']['entries']=2*e['manifest']['entries']
        with self.assertRaisesRegex(m.Hold,'DUPLICATE'):
            m.prepare(self.path,e)

    def test_remote_exists_does_not_imply_proof(self):
        idx=index_template(m.digest(self.raw))
        p,files=self.plan(existing_index=idx)
        self.assertEqual(files,{})
        self.assertEqual(p['entries'][0]['action'],'VERIFY_EXISTING_REMOTE_BYTES_AND_ACL_NO_WRITE')

    def test_reject_existing_conflict(self):
        idx=index_template('sha256:'+'f'*64)
        with self.assertRaisesRegex(m.Hold,'IDENTITY_CONFLICT'):
            self.plan(existing_index=idx)

    def test_reject_trusted_claim_in_untrusted_index(self):
        idx=index_template(m.digest(self.raw));idx['authority']=True
        with self.assertRaisesRegex(m.Hold,'INDEX_INVALID'):
            self.plan(existing_index=idx)

    def test_reject_duplicate_index_entry(self):
        idx=index_template(m.digest(self.raw));idx['entries']*=2
        with self.assertRaisesRegex(m.Hold,'DUPLICATE_IDENTITY'):
            self.plan(existing_index=idx)

    def test_index_preimage_exact_bytes(self):
        idx=index_template(m.digest(self.raw))
        raw=(json.dumps(idx,ensure_ascii=False,indent=1)+'\n').encode()
        plan,_=self.plan(existing_index=idx,existing_index_raw=raw)
        self.assertEqual(plan['baseline_index_sha256'],m.digest(raw))
        with self.assertRaisesRegex(m.Hold,'RAW_MISMATCH'):
            self.plan(existing_index=idx,existing_index_raw=b'{}')

    def test_reject_duplicate_json_keys(self):
        with self.assertRaisesRegex(m.Hold,'DUPLICATE_KEY'):
            m.read_object(b'{"a":1,"a":2}','bad')

    def test_invalid_git_commit_rejected(self):
        with self.assertRaisesRegex(m.Hold,'EXPECTED_COMMIT_INVALID'):
            m.require_frozen_checkout(Path(self.tmp.name),'main')

    def test_checkout_is_required(self):
        with self.assertRaisesRegex(m.Hold,'CANONICAL_CHECKOUT'):
            m.require_frozen_checkout(Path(self.tmp.name),'0'*40)

    def test_verifier_is_required(self):
        with self.assertRaisesRegex(m.Hold,'VERIFIER_NOT_AVAILABLE'):
            m.verified_release(self.path,Path(self.tmp.name))

    def test_unsafe_archive_member(self):
        with zipfile.ZipFile(self.path,'w') as z:z.writestr('../bad','evil')
        with self.assertRaisesRegex(m.Hold,'UNSAFE_ARCHIVE'):
            m.load_checked_archive(self.path)

    def test_duplicate_archive_member(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(self.path,'w') as z:
                z.writestr('kit.json','a');z.writestr('kit.json','b')
        with self.assertRaisesRegex(m.Hold,'UNSAFE_ARCHIVE'):
            m.load_checked_archive(self.path)

    def test_cli_without_repo_fails_without_writes(self):
        out=Path(self.tmp.name)/'result.json'
        status=m.cli(['--release',str(self.path),'--verified-repository-checkout',self.tmp.name,
                      '--expected-repository-commit','0'*40,'--output',str(out)])
        self.assertEqual(status,8)
        self.assertFalse(out.exists())

    def test_no_distribution_authority(self):
        plan,_=self.plan()
        self.assertTrue(all(x['distribution_status']=='NOT_AUTHORIZED' for x in plan['entries']))

    def test_reject_wrong_kit_bytes(self):
        with zipfile.ZipFile(self.path,'w') as z:
            z.writestr(f'kits/{LINEAGE}/{REV}.json',self.raw+b' ')
        e={**self.evidence,'releaseSha256':m.digest(self.path.read_bytes()),'releaseBytes':self.path.stat().st_size}
        with self.assertRaisesRegex(m.Hold,'BYTES_MISMATCH'):
            m.prepare(self.path,e)


if __name__=='__main__':unittest.main()
