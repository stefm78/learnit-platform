import copy
import json
import pathlib
import unittest
from private_kit_views import (
    Hold, Snapshot, canonical, unique_object, validate_index, update_index,
    render_navigation, reconcile_views,
)

DRIVE = 'B9B0D852F6CCE2CD'
FROZEN = pathlib.Path('/mnt/data/PRIVATE_INDEX.json')


def initial_index():
    # Deliberately use real snapshot shape, but not hard-wire user's bytes into patch.
    if FROZEN.exists():
        return json.loads(FROZEN.read_text())
    k = '11111111-1111-4111-8111-111111111111'
    r = '22222222-2222-4222-8222-222222222222'
    return dict(schema='learnit.private-kit-index.verification-snapshot.v1', authority=False,
                distribution_authorized=False, public_access_authorized=False, kit_count=1,
                entries=[new_entry(k, r, 'example')])


def new_entry(k='33333333-3333-4333-8333-333333333333',
              r='44444444-4444-4444-8444-444444444444', item='new_kit'):
    h='a'*64
    return dict(lineage_id=k,revision_id=r,relative_path=f'{k}/{r}/kit.json',
                private_copy_id=item,kit_sha256=h,private_copy_sha256_verified=h,
                private_copy_access='OWNER_ONLY_AT_VERIFICATION',
                private_copy_verified_utc='2026-11-02T19:00:00+00:00',
                distribution_status='NOT_AUTHORIZED', title='Nouveau <kit>', activities=3,
                private_storage_status='STORED_PRIVATE_VERIFIED')

class FakeAtomicViews:
    """For local unit tests only. Its CAS does not prove Graph CAS exists."""
    def __init__(self,index,nav=b'OLD_NAV',qualified=True):
        self.rows={'PRIVATE_INDEX.json':[canonical(index),'etag_i'],
                   'NAVIGUER_KITS.html':[nav,'etag_n']}
        self.calls=[]
        self.qualified=qualified
        self.fail_next=None
        self.drift=None
    def read(self,name):
        if self.drift == name:
            self.drift = None
            self.rows[name][0] += b' DRIFT'
        v=self.rows[name]
        return Snapshot(v[0],v[1])
    def assert_live_conditional_write_qualified(self):
        if not self.qualified:raise Hold('NO_PROVIDER_CAS_PROOF')
    def commit_conditional(self,name,prior_etag,raw):
        self.calls.append(name)
        if self.fail_next==name:
            self.fail_next=None
            raise Hold('SIMULATED_PARTIAL_REMOTE_FAILURE')
        if self.rows[name][1]!=prior_etag:
            raise Hold('STALE_EXPECTED_ETAG')
        self.rows[name]=[raw,self.rows[name][1]+'+']

class ViewTests(unittest.TestCase):
    def test_current_snapshot_contract(self):
        self.assertGreaterEqual(len(validate_index(initial_index())),1)
    def test_single_new_registration(self):
        out, new=update_index(initial_index(),new_entry())
        self.assertTrue(new)
        self.assertEqual(out['kit_count'], initial_index()['kit_count']+1)
        self.assertFalse(out['distribution_authorized'])
        self.assertFalse(out['authority'])
        self.assertIn('PER_ENTRY',out['current_remote_status'])
    def test_existing_nine_remain_byte_identical(self):
        before=initial_index();out,_=update_index(before,new_entry())
        for entry in before['entries']:
            got=next(x for x in out['entries'] if x['lineage_id']==entry['lineage_id'])
            self.assertEqual(got,entry)
    def test_replay_does_not_change_index(self):
        x,_=update_index(initial_index(),new_entry())
        y,created=update_index(x,new_entry())
        self.assertFalse(created)
        self.assertEqual(x,y)
    def test_replay_with_changed_bytes_holds(self):
        x,_=update_index(initial_index(),new_entry());entry=new_entry();entry['kit_sha256']='b'*64
        entry['private_copy_sha256_verified']='b'*64
        with self.assertRaisesRegex(Hold,'EXISTING_IDENTITY_CONFLICT'):update_index(x,entry)
    def test_replay_with_changed_remote_id_holds(self):
        x,_=update_index(initial_index(),new_entry());entry=new_entry(item='different')
        with self.assertRaisesRegex(Hold,'EXISTING_IDENTITY_CONFLICT'):update_index(x,entry)
    def test_existing_destination_alias_fails(self):
        i=initial_index();e=new_entry(item=i['entries'][0]['private_copy_id'])
        with self.assertRaisesRegex(Hold,'DESTINATION_REUSED'):update_index(i,e)
    def test_index_entry_path_traversal_fails(self):
        e=new_entry();e['relative_path']='../../../escape.json'
        with self.assertRaisesRegex(Hold,'INDEX_PATH'):update_index(initial_index(),e)
    def test_index_entry_invalid_sha_fails(self):
        e=new_entry();e['kit_sha256']='garbage'
        with self.assertRaisesRegex(Hold,'INDEX_REMOTE_ID_OR_SHA'):update_index(initial_index(),e)
    def test_index_entry_public_status_fails(self):
        e=new_entry();e['distribution_status']='PUBLIC'
        with self.assertRaisesRegex(Hold,'INDEX_ACCESS_OR_DISTRIBUTION'):update_index(initial_index(),e)
    def test_duplicate_lineage_revision_fails(self):
        i=initial_index();i['entries'].append(copy.deepcopy(i['entries'][0]));i['kit_count']+=1
        with self.assertRaisesRegex(Hold,'COLLISION'):validate_index(i)
    def test_invalid_count_fails(self):
        i=initial_index();i['kit_count']=0
        with self.assertRaisesRegex(Hold,'COUNT'):validate_index(i)
    def test_duplicate_json_keys_fail(self):
        with self.assertRaisesRegex(Hold,'DUPLICATE_JSON_KEY'):
            unique_object(b'{"authority":false,"authority":true}')
    def test_navigator_escapes_injection(self):
        i,_=update_index(initial_index(),new_entry())
        out=render_navigation(i,DRIVE)
        self.assertNotIn(b'<kit>',out)
        self.assertIn(b'&lt;kit&gt;',out)
        self.assertIn('diffusion aux élèves non autoris'.encode('utf-8'),out)
    def test_preserves_private_search_and_grouping(self):
        i,_=update_index(initial_index(),new_entry())
        out=render_navigation(i,DRIVE)
        self.assertIn(b'id="search"',out)
        self.assertIn(b'document.querySelectorAll',out)
        self.assertIn(b'<section>',out)

    def test_invalid_title_fails_closed(self):
        i=initial_index();i['entries'][0]['title']={'unexpected':'object'}
        with self.assertRaisesRegex(Hold,'DISPLAY_METADATA_INVALID'):render_navigation(i,DRIVE)

    def test_navigator_is_deterministic(self):
        i,_=update_index(initial_index(),new_entry())
        a=render_navigation(i,DRIVE)
        i['entries'].reverse()
        self.assertEqual(a,render_navigation(i,DRIVE))
    def test_navigation_does_not_open_anonymous_link(self):
        i,_=update_index(initial_index(),new_entry())
        out=render_navigation(i,DRIVE)
        self.assertNotIn(b'createLink',out)
        self.assertNotIn(b'anonymous',out)
    def test_absent_live_cas_rejects_before_writing(self):
        p=FakeAtomicViews(initial_index(),qualified=False)
        with self.assertRaisesRegex(Hold,'NO_PROVIDER_CAS_PROOF'):
            reconcile_views(p,new_entry(),DRIVE,qualification_verified=True,kit_remote_verified=True)
        self.assertEqual(p.calls,[])
    def test_no_canonical_pass_cannot_write(self):
        p=FakeAtomicViews(initial_index())
        with self.assertRaisesRegex(Hold,'EVIDENCE_NOT_VERIFIED'):
            reconcile_views(p,new_entry(),DRIVE,qualification_verified=False,kit_remote_verified=True)
        self.assertEqual(p.calls,[])
    def test_missing_kit_remote_proof_cannot_write(self):
        p=FakeAtomicViews(initial_index())
        with self.assertRaisesRegex(Hold,'EVIDENCE_NOT_VERIFIED'):
            reconcile_views(p,new_entry(),DRIVE,qualification_verified=True,kit_remote_verified=False)
        self.assertEqual(p.calls,[])
    def test_both_views_rebuilt_only_after_mock_cas(self):
        p=FakeAtomicViews(initial_index())
        result=reconcile_views(p,new_entry(),DRIVE,qualification_verified=True,kit_remote_verified=True)
        self.assertEqual(p.calls,['PRIVATE_INDEX.json','NAVIGUER_KITS.html'])
        self.assertTrue(result['new_registration'])
        self.assertEqual(json.loads(p.rows['PRIVATE_INDEX.json'][0])['kit_count'],initial_index()['kit_count']+1)
    def test_two_view_failure_is_a_hold_and_recoverable(self):
        p=FakeAtomicViews(initial_index());p.fail_next='NAVIGUER_KITS.html'
        with self.assertRaisesRegex(Hold,'PARTIAL_REMOTE_FAILURE'):
            reconcile_views(p,new_entry(),DRIVE,qualification_verified=True,kit_remote_verified=True)
        # durable first view is updated; next attempt is replay, repairs nav only
        self.assertEqual(json.loads(p.rows['PRIVATE_INDEX.json'][0])['kit_count'],initial_index()['kit_count']+1)
        p.calls.clear()
        result=reconcile_views(p,new_entry(),DRIVE,qualification_verified=True,kit_remote_verified=True)
        self.assertEqual(p.calls,['NAVIGUER_KITS.html'])
        self.assertFalse(result['new_registration'])
    def test_idempotent_replay_both_views_unchanged(self):
        p=FakeAtomicViews(initial_index())
        reconcile_views(p,new_entry(),DRIVE,qualification_verified=True,kit_remote_verified=True)
        p.calls.clear()
        result=reconcile_views(p,new_entry(),DRIVE,qualification_verified=True,kit_remote_verified=True)
        self.assertEqual(p.calls,[])
        self.assertFalse(result['new_registration'])
    def test_unsafe_user_content_cannot_be_html(self):
        entry=new_entry();entry['title']='A <script>void 0</script>'
        i,_=update_index(initial_index(),entry)
        out=render_navigation(i,DRIVE)
        self.assertNotIn(b'<h3>A <script>',out)
        self.assertIn(b'<h3>A &lt;script&gt;',out)
    def test_wrong_index_schema_does_not_write(self):
        i=initial_index();i['schema']='other'
        p=FakeAtomicViews(i)
        with self.assertRaisesRegex(Hold,'INDEX_CONTRACT'):
            reconcile_views(p,new_entry(),DRIVE,qualification_verified=True,kit_remote_verified=True)
        self.assertEqual(p.calls,[])
    def test_invalid_drive_not_written(self):
        p=FakeAtomicViews(initial_index())
        with self.assertRaisesRegex(Hold,'DRIVE_ID_INVALID'):
            reconcile_views(p,new_entry(),'x/?y',qualification_verified=True,kit_remote_verified=True)
        self.assertEqual(p.calls,[])

if __name__=='__main__': unittest.main()
