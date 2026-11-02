"""Isolated transport simulations. No Graph access or real authorization."""
import importlib.util,sys,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]
for name in ('private_kit_intake_bridge','private_kit_intake_executor'):
    spec=importlib.util.spec_from_file_location(name,p/(name+'.py'))
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod)
b=sys.modules['private_kit_intake_bridge']; e=sys.modules['private_kit_intake_executor']
LINEAGE='aa215370-06ed-5693-965c-3622bb62e35a'
REV='9bb3927d-3535-5ddb-8080-8fa2ec443627'
RAW=b'{"contract":"learnit.kit.v6"}'
PATH=f'20_KITS/{LINEAGE}/{REV}/{REV}.json'

class FakePort:
    def __init__(self):
        self.nodes={'courses':{'id':'courses','name':'Cours_source','folder':{}},
                    'root':{'id':'root','name':'20_KITS','folder':{}}}
        self.parents={('courses','20_KITS'):'root'}
        self.contents={};self.acls={k:[{'roles':['owner']}] for k in self.nodes}
        self.writes=[];self.counter=0;self.unsafe_permission=False;self.tamper_read=False
    def child(self,parent,name):
        v=self.parents.get((parent,name));return self.nodes[v] if v else None
    def new(self,parent,name,folder=False,raw=None):
        if self.child(parent,name):raise e.Hold('CONFLICT_FAIL')
        self.counter+=1;key=f'n{self.counter}'
        node={'id':key,'name':name,'folder':{}} if folder else {'id':key,'name':name,'file':{},'size':len(raw)}
        self.nodes[key]=node;self.parents[parent,name]=key;self.acls[key]=[{'roles':['owner']}]
        if self.unsafe_permission:self.acls[key]=[{'roles':['write'],'link':{'scope':'anonymous'}}]
        if raw is not None:self.contents[key]=raw
        self.writes.append((parent,name));return node
    def create_folder_fail(self,parent,name):return self.new(parent,name,folder=True)
    def create_file_fail(self,parent,name,raw):return self.new(parent,name,raw=raw)
    def content(self,item_id):
        data=self.contents[item_id]
        return data+b'!' if self.tamper_read else data
    def permissions(self,item_id):return self.acls[item_id]


def plan(exist=False):
    return {'schema':b.SCHEMA,'status':'LOCAL_PREPARED_READ_ONLY_NOT_ADMITTED',
            'authority':False,'write_permissions_conferred':False,'entries':[
            {'lineage_id':LINEAGE,'revision_id':REV,'destination':PATH,
             'action':'VERIFY_EXISTING_REMOTE_BYTES_AND_ACL_NO_WRITE' if exist else 'PREFLIGHT_REMOTE_AND_CREATE_ONLY_IF_AUTHORIZED',
             'content_sha256':b.digest(RAW)}]}

class ExecutorTest(unittest.TestCase):
    def test_new_one_verified_pending_index(self):
        port=FakePort();seen=[]
        result=e.execute_verified_plan(plan(),{PATH:RAW},port,'courses',authorization=True,observe=seen.append)
        self.assertEqual(result['status'],'PASS_PRIVATE_COPIES_VERIFIED_INDEX_NOT_COMMITTED')
        self.assertEqual(len(port.writes),3)
        self.assertEqual(len(seen),1)
        self.assertFalse(result['public_distribution'])
    def test_denied_by_default(self):
        port=FakePort()
        with self.assertRaisesRegex(e.Hold,'AUTHORIZATION'):
            e.execute_verified_plan(plan(),{PATH:RAW},port,'courses')
        self.assertFalse(port.writes)
    def test_wrong_digest_prevents_any_write(self):
        port=FakePort()
        with self.assertRaisesRegex(e.Hold,'SHA256'):
            e.execute_verified_plan(plan(),{PATH:b'bad'},port,'courses',True)
        self.assertFalse(port.writes)
    def test_extra_member_rejected(self):
        port=FakePort()
        with self.assertRaisesRegex(e.Hold,'MEMBERS_NOT_EXACT'):
            e.execute_verified_plan(plan(),{PATH:RAW,'other':RAW},port,'courses',True)
    def test_remote_conflict(self):
        port=FakePort();parent=port.create_folder_fail('root',LINEAGE);ver=port.create_folder_fail(parent['id'],REV)
        port.create_file_fail(ver['id'],REV+'.json',RAW)
        orig=len(port.writes)
        with self.assertRaisesRegex(e.Hold,'CONFLICT'):
            e.execute_verified_plan(plan(),{PATH:RAW},port,'courses',True)
        self.assertEqual(len(port.writes),orig)
    def test_unsafe_permissions_hold(self):
        port=FakePort();port.unsafe_permission=True
        with self.assertRaisesRegex(e.Hold,'ACL_NOT_OWNER_ONLY'):
            e.execute_verified_plan(plan(),{PATH:RAW},port,'courses',True)
    def test_tampered_readback_hold(self):
        port=FakePort();port.tamper_read=True
        with self.assertRaisesRegex(e.Hold,'REMOTE_READBACK_SHA256'):
            e.execute_verified_plan(plan(),{PATH:RAW},port,'courses',True)
    def test_existing_no_write(self):
        port=FakePort();first=e.execute_verified_plan(plan(),{PATH:RAW},port,'courses',True)
        count=len(port.writes)
        r=e.execute_verified_plan(plan(True),{},port,'courses',True)
        self.assertEqual(len(port.writes),count)
        self.assertEqual(r['entries'][0]['mode'],'VERIFIED_EXISTING_NO_WRITE')
    def test_missing_existing_holds_without_writes(self):
        port=FakePort()
        with self.assertRaisesRegex(e.Hold,'EXPECTED_FOLDER_ABSENT'):
            e.execute_verified_plan(plan(True),{},port,'courses',True)
        self.assertFalse(port.writes)
    def test_root_public_holds(self):
        port=FakePort();port.acls['root']=[{'roles':['owner'],'link':{'scope':'anonymous'}}]
        with self.assertRaisesRegex(e.Hold,'ACL_NOT_OWNER_ONLY'):
            e.execute_verified_plan(plan(),{PATH:RAW},port,'courses',True)
    def test_path_traversal_holds(self):
        port=FakePort();bad=plan();bad['entries'][0]['destination']=f'20_KITS/{LINEAGE}/../file.json'
        with self.assertRaisesRegex(e.Hold,'PATH_OR_IDENTITY'):
            e.execute_verified_plan(bad,{bad['entries'][0]['destination']:RAW},port,'courses',True)
        self.assertFalse(port.writes)
    def test_duplicate_destination_preflight_holds(self):
        port=FakePort();bad=plan();bad['entries'].append(dict(bad['entries'][0]))
        with self.assertRaisesRegex(e.Hold,'DUPLICATE_DESTINATION'):
            e.execute_verified_plan(bad,{PATH:RAW},port,'courses',True)
        self.assertFalse(port.writes)
    def test_acl_validation(self):
        self.assertTrue(e.is_owner_only([{'roles':['owner']}]))
        self.assertFalse(e.is_owner_only([]))
        self.assertFalse(e.is_owner_only([{'roles':['owner'],'grantedToIdentitiesV2':[{}]}]))
        self.assertFalse(e.is_owner_only([{'roles':['write']}]))
if __name__=='__main__':unittest.main()
