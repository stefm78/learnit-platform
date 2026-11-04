import hashlib,unittest
from post_pass_factory_step import Hold,validate_event

A=b'test zip bytes';S='sha256:'+hashlib.sha256(A).hexdigest();RUN='sha256:'+'a'*64;GIT='b'*40
VERIFIED=dict(schema='learnit.atlas.qualified_release_set_result.v2',
              verdict='PASS_QUALIFIED_RELEASE_SET_V6_VERIFICATION_R1',
              releaseSha256=S,releaseBytes=len(A),
              manifest={'entries':[{'factoryRun':{'runId':RUN}}]})
EVENT=dict(type='FACTORY_V6_QUALIFIED_RELEASE_DURABLE',
           distribution_authorized=False,release_sha256=S,canonical_verifier_commit=GIT,
           factory_run_ids=[RUN])
class Tests(unittest.TestCase):
    def test_valid_binding(self):self.assertEqual(validate_event(EVENT,A,GIT,VERIFIED),(RUN,))
    def test_event_forgery_does_not_bind(self):
        with self.assertRaisesRegex(Hold,'UNTRUSTED'):
            validate_event({**EVENT,'type':'PASS'},A,GIT,VERIFIED)
    def test_claimed_public_fails(self):
        with self.assertRaisesRegex(Hold,'UNTRUSTED'):
            validate_event({**EVENT,'distribution_authorized':True},A,GIT,VERIFIED)
    def test_wrong_checkout_sha_fails(self):
        with self.assertRaisesRegex(Hold,'COMMIT'):
            validate_event(EVENT,A,'0'*40,VERIFIED)
    def test_stale_zip_fails(self):
        with self.assertRaisesRegex(Hold,'NOT_EXACT_PASS'):
            validate_event(EVENT,A+b'!',GIT,VERIFIED)
    def test_fake_verdict_fails(self):
        with self.assertRaisesRegex(Hold,'NOT_EXACT_PASS'):
            validate_event(EVENT,A,GIT,{**VERIFIED,'verdict':'PASS_AI_KIT_FACTORY_V6_R3'})
    def test_missing_run_fails(self):
        with self.assertRaisesRegex(Hold,'EVENT_MISMATCH'):
            validate_event({**EVENT,'factory_run_ids':[]},A,GIT,VERIFIED)
    def test_unexpected_run_fails(self):
        with self.assertRaisesRegex(Hold,'EVENT_MISMATCH'):
            validate_event({**EVENT,'factory_run_ids':['sha256:'+'c'*64]},A,GIT,VERIFIED)
    def test_duplicate_run_ids_fail(self):
        v={**VERIFIED,'manifest':{'entries':[{'factoryRun':{'runId':RUN}},
                                            {'factoryRun':{'runId':RUN}}]}}
        with self.assertRaisesRegex(Hold,'EVENT_MISMATCH'):
            validate_event({**EVENT,'factory_run_ids':[RUN,RUN]},A,GIT,v)
    def test_missing_commit_fails(self):
        with self.assertRaisesRegex(Hold,'COMMIT'):
            validate_event({**EVENT,'canonical_verifier_commit':None},A,GIT,VERIFIED)


# Security and human-command tests (previous V1 manually reviewed)
import copy, hashlib, pathlib, tempfile, unittest
from post_pass_factory_step import Hold, build_command

L='11111111-1111-1111-1111-111111111111'
R='22222222-2222-2222-2222-222222222222'
RAW=b'V6_RELEASE_FAKE_FOR_TEST_ONLY'
D=hashlib.sha256(RAW).hexdigest()

def fixture():
    return {'status':'LOCAL_PLAN_ONLY_NOT_ADMITTED','authority':False,
        'remote_mutation':False,'automatic_hook_installed':False,
        'release_sha256':'sha256:'+D,'factory_run_ids':['sha256:'+'a'*64],
        'members_sha256':{f'20_KITS/{L}/{R}/kit.json':'c'*64},
        'plan':{'schema':'learnit.private-kit-intake-plan.v1',
                'status':'LOCAL_PREPARED_READ_ONLY_NOT_ADMITTED',
                'authority':False,'write_permissions_conferred':False,
                'release_sha256':D,'release_id':'sha256:'+'e'*64,
                'implementation_authority':'1'*40,'baseline_index_sha256':'b'*64,
                'entries':[{'lineage_id':L,'revision_id':R,
                'destination':f'20_KITS/{L}/{R}/kit.json',
                'content_sha256':'sha256:'+'c'*64,'content_bytes':42,
                'factory_run_id':'sha256:'+'a'*64,
                'action':'PREFLIGHT_REMOTE_AND_CREATE_ONLY_IF_AUTHORIZED'}]}}

class TestManual(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.arc=pathlib.Path(self.tmp.name)/'release.zip';self.arc.write_bytes(RAW)
        self.valid=fixture()
    def test_correct_receipt_proposes_no_automatic_publication(self):
        s=build_command(self.valid,self.arc)
        for term in ['GO CONDITIONNEL','sha256:'+D,'PRIVATE_INDEX.json','NAVIGUER_KITS.html',
                     'refresh_onedrive_catalogue.py','HOLD','Aucune publication élèves',
                     f'20_KITS/{L}/{R}/kit.json','sha256:'+'a'*64]:
            self.assertIn(term,s)
    def test_archive_mutation_blocks(self):
        self.arc.write_bytes(RAW+b'changed')
        with self.assertRaisesRegex(Hold,'RELEASE_ARCHIVE_BYTES_CHANGED'):build_command(self.valid,self.arc)
    def test_no_fake_pass(self):
        self.valid['status']='PASS_PRIVATELY_PUBLISHED'
        with self.assertRaisesRegex(Hold,'NOT_A_READ_ONLY'):build_command(self.valid,self.arc)
    def test_no_authority_granted(self):
        self.valid['plan']['write_permissions_conferred']=True
        with self.assertRaisesRegex(Hold,'PLAN_NOT_READ_ONLY'):build_command(self.valid,self.arc)
    def test_no_stale_index_unbound(self):
        self.valid['plan']['baseline_index_sha256']=None
        with self.assertRaisesRegex(Hold,'FRESH_RAW_PRIVATE_INDEX'):build_command(self.valid,self.arc)
    def test_release_identity_must_match(self):
        self.valid['plan']['release_sha256']='d'*64
        with self.assertRaisesRegex(Hold,'RELEASE_IDENTITY_MISMATCH'):build_command(self.valid,self.arc)
    def test_no_bad_path(self):
        self.valid['plan']['entries'][0]['destination']='20_KITS/../../evil.json'
        with self.assertRaisesRegex(Hold,'UNSAFE_OR_DUPLICATE'):build_command(self.valid,self.arc)
    def test_no_wrong_target_revision(self):
        self.valid['plan']['entries'][0]['destination']=f'20_KITS/{L}/{L}/kit.json'
        with self.assertRaisesRegex(Hold,'UNSAFE_OR_DUPLICATE'):build_command(self.valid,self.arc)
    def test_no_unknown_action(self):
        self.valid['plan']['entries'][0]['action']='REPLACE_AND_PUBLISH'
        with self.assertRaisesRegex(Hold,'UNKNOWN_ACTION'):build_command(self.valid,self.arc)
    def test_no_duplicate_entries(self):
        self.valid['plan']['entries']*=2
        with self.assertRaisesRegex(Hold,'DUPLICATE_KIT_IDENTITY'):build_command(self.valid,self.arc)
    def test_name_is_not_interpolated_as_html_or_shell(self):
        self.valid['plan']['entries'][0]['title']='<script>alert(1)</script>'
        self.assertNotIn('<script>',build_command(self.valid,self.arc))
    def test_reuse_existing_is_read_only(self):
        self.valid['plan']['entries'][0]['action']='VERIFY_EXISTING_REMOTE_BYTES_AND_ACL_NO_WRITE'
        self.valid['members_sha256']={}
        s=build_command(self.valid,self.arc)
        self.assertIn('aucun nouveau kit',s)
    def test_factory_run_binding(self):
        self.valid['plan']['entries'][0]['factory_run_id']='sha256:'+'b'*64
        with self.assertRaisesRegex(Hold,'UNBOUND_FACTORY_RUN'):build_command(self.valid,self.arc)
    def test_kit_bytes_binding(self):
        path=f'20_KITS/{L}/{R}/kit.json'
        self.valid['members_sha256'][path]='d'*64
        with self.assertRaisesRegex(Hold,'NEW_KIT_SOURCE_DIGEST_MISMATCH'):build_command(self.valid,self.arc)
    def test_no_release_set_identity(self):
        self.valid['plan']['release_id']=None
        with self.assertRaisesRegex(Hold,'CANONICAL_RELEASE_SET_ID_MISSING'):build_command(self.valid,self.arc)
    def test_no_implementation_authority(self):
        self.valid['plan']['implementation_authority']='not-a-commit'
        with self.assertRaisesRegex(Hold,'IMPLEMENTATION_AUTHORITY_MISSING'):build_command(self.valid,self.arc)
    def test_no_extra_run(self):
        self.valid['factory_run_ids'].append('sha256:'+'d'*64)
        with self.assertRaisesRegex(Hold,'FACTORY_RUN_SET_INCOMPLETE_OR_EXTRA'):build_command(self.valid,self.arc)
    def test_extra_source_in_receipt(self):
        self.valid['members_sha256']['20_KITS/surprise.json']='e'*64
        with self.assertRaisesRegex(Hold,'UNBOUND_OR_EXTRA_MEMBER'):build_command(self.valid,self.arc)
    def test_existing_with_new_bytes_is_hold(self):
        self.valid['plan']['entries'][0]['action']='VERIFY_EXISTING_REMOTE_BYTES_AND_ACL_NO_WRITE'
        with self.assertRaisesRegex(Hold,'EXISTING_KIT_MUST_BE_VERIFY_ONLY'):build_command(self.valid,self.arc)
    def test_missing_member_map_is_hold(self):
        del self.valid['members_sha256']
        with self.assertRaisesRegex(Hold,'MEMBER_DIGESTS_ABSENT'):build_command(self.valid,self.arc)
    def test_no_new_kits_proposes_no_go(self):
        self.valid['plan']['entries'][0]['action']='VERIFY_EXISTING_REMOTE_BYTES_AND_ACL_NO_WRITE'
        self.valid['members_sha256']={}
        s=build_command(self.valid,self.arc)
        self.assertIn('aucun nouveau kit',s)
        self.assertNotIn('GO CONDITIONNEL',s)
    def test_no_network_invocation_in_command_renderer(self):
        import unittest.mock
        with unittest.mock.patch('subprocess.run',side_effect=AssertionError('no process expected')):
            s=build_command(self.valid,self.arc)
            self.assertIn('GO CONDITIONNEL',s)

    def test_wrong_hash_format(self):
        self.valid['plan']['entries'][0]['content_sha256']='c'*64
        with self.assertRaisesRegex(Hold,'KIT_HASH_INVALID'):build_command(self.valid,self.arc)



class TestManualPostPassIntegration(unittest.TestCase):
    def test_verified_receipt_generates_command_only_after_validation(self):
        import json, pathlib, tempfile, types
        from unittest.mock import patch
        from post_pass_factory_step import prepare_read_only
        # Controlled local simulator, never a claim of real Graph connectivity.
        with tempfile.TemporaryDirectory() as work:
            release=pathlib.Path(work)/'frozen-release.zip'
            release.write_bytes(RAW)
            index=b'{"entries":[],"schema":"learnit.private-kit-index.verification-snapshot.v1"}'
            receipt=fixture()
            evidence={'verified':{
                'schema':'learnit.atlas.qualified_release_set_result.v2',
                'verdict':'PASS_QUALIFIED_RELEASE_SET_V6_VERIFICATION_R1',
                'releaseSha256':'sha256:'+D,'releaseBytes':len(RAW),
                'manifest':{'entries':[{'factoryRun':{'runId':'sha256:'+'a'*64}}]}
            },'plan':receipt['plan'],'members_sha':receipt['members_sha256']}
            event={'type':'FACTORY_V6_QUALIFIED_RELEASE_DURABLE',
                   'distribution_authorized':False,'release_sha256':'sha256:'+D,
                   'canonical_verifier_commit':'1'*40,
                   'factory_run_ids':['sha256:'+'a'*64]}
            done=types.SimpleNamespace(stdout=json.dumps(evidence))
            with patch('post_pass_factory_step.require_exact_checkout') as guard, \
                 patch('post_pass_factory_step.subprocess.run',return_value=done) as call:
                result=prepare_read_only(release,pathlib.Path(work),'1'*40,index,event)
            self.assertIn('GO CONDITIONNEL',result['manual_handoff'])
            self.assertFalse(result['remote_mutation'])
            self.assertFalse(result['automatic_hook_installed'])
            guard.assert_called_once()
            call.assert_called_once()
    def test_rendered_prompt_excludes_secrets_and_path_injection(self):
        receipt=fixture()
        receipt['plan']['entries'][0]['title']='<script>Bearer victim-token</script>'
        with tempfile.TemporaryDirectory() as work:
            import pathlib
            release=pathlib.Path(work)/'frozen-release.zip';release.write_bytes(RAW)
            rendered=build_command(receipt,release)
        self.assertNotIn('victim-token',rendered)
        self.assertNotIn('<script>',rendered)

class TestThirdAdversarialReview(unittest.TestCase):
    def test_false_factory_hold_cannot_produce_command(self):
        import pathlib, tempfile, types, json
        from unittest.mock import patch
        from post_pass_factory_step import prepare_read_only
        with tempfile.TemporaryDirectory() as work:
            a=pathlib.Path(work)/'frozen-release.zip';a.write_bytes(RAW)
            v=fixture(); rec={'verified':{
                'schema':'learnit.atlas.qualified_release_set_result.v2',
                'verdict':'HOLD_QUALIFIED_RELEASE_SET_V6_INPUT_R1',
                'releaseSha256':'sha256:'+D,'releaseBytes':len(RAW),
                'manifest':{'entries':[{'factoryRun':{'runId':'sha256:'+'a'*64}}]}},
                'plan':v['plan'],'members_sha':v['members_sha256']}
            event={'type':'FACTORY_V6_QUALIFIED_RELEASE_DURABLE',
                'distribution_authorized':False,'release_sha256':'sha256:'+D,
                'canonical_verifier_commit':'1'*40,
                'factory_run_ids':['sha256:'+'a'*64]}
            with patch('post_pass_factory_step.require_exact_checkout'), \
                 patch('post_pass_factory_step.subprocess.run',return_value=types.SimpleNamespace(stdout=json.dumps(rec))):
                with self.assertRaisesRegex(Hold,'CANONICAL_RELEASE_NOT_EXACT_PASS'):
                    prepare_read_only(a,pathlib.Path(work),'1'*40,b'{}',event)
    def test_malicious_pretend_index_or_publish_action_rejected(self):
        import pathlib, tempfile
        with tempfile.TemporaryDirectory() as wd:
            arc=pathlib.Path(wd)/'release.zip';arc.write_bytes(RAW)
            for bad in ('REPLACE_EXISTING','PUBLISH_PUBLIC','UPDATE_NAVIGATOR'):
                v=fixture();v['plan']['entries'][0]['action']=bad
                with self.subTest(action=bad), self.assertRaisesRegex(Hold,'UNKNOWN_ACTION'):
                    build_command(v,arc)
    def test_command_mentions_canonical_catalogue_only(self):
        import pathlib,tempfile
        with tempfile.TemporaryDirectory() as wd:
            arc=pathlib.Path(wd)/'release.zip';arc.write_bytes(RAW)
            s=build_command(fixture(),arc)
            self.assertIn('tools/refresh_onedrive_catalogue.py',s)
            self.assertIn('PAS la copie historique V1',s)
            self.assertIn('Aucune publication élèves',s)
            self.assertIn('le `PRIVATE_INDEX.json` courant',s)
            self.assertNotIn('execute now without checks',s.lower())


class TestScheduledChatGPTPostPassCLI(unittest.TestCase):
    """CLI contract for a future scheduler; does not run scheduled tasks."""
    def call(self, event_text, human=False, handoff='GO CONDITIONNEL — kit privé'):
        import contextlib,io,pathlib,tempfile
        from unittest.mock import patch
        from post_pass_factory_step import main
        with tempfile.TemporaryDirectory() as root:
            p=pathlib.Path(root)
            for name,data in [('archive.zip',RAW),('index.json',b'{}'),('event.json',event_text.encode())]:
                (p/name).write_bytes(data)
            args=['--release',str(p/'archive.zip'),'--checkout',str(p),
                  '--commit','1'*40,'--index-raw',str(p/'index.json'),
                  '--event',str(p/'event.json')]
            if human: args.append('--human-command')
            output,errors=io.StringIO(),io.StringIO()
            with patch('post_pass_factory_step.prepare_read_only',return_value={
                'manual_handoff':handoff,'remote_mutation':False,
                'automatic_hook_installed':False}) as fn, \
                 contextlib.redirect_stdout(output),contextlib.redirect_stderr(errors):
                status=main(args)
            return status,output.getvalue(),errors.getvalue(),fn.call_count

    def test_text_mode_prints_human_command_not_json(self):
        code,out,err,count=self.call('{"type":"example"}',human=True)
        self.assertEqual((code,out.strip(),err,count),(0,'GO CONDITIONNEL — kit privé','',1))

    def test_default_json_receipt_preserved(self):
        import json
        code,out,err,count=self.call('{"type":"example"}')
        self.assertEqual((code,err,count),(0,'',1))
        self.assertFalse(json.loads(out)['remote_mutation'])
        self.assertFalse(json.loads(out)['automatic_hook_installed'])

    def test_human_mode_existing_kit_no_write_command(self):
        code,out,err,count=self.call('{"type":"example"}',human=True,
                                    handoff='Aucun nouveau kit. AUCUNE commande de modification.')
        self.assertEqual(code,0)
        self.assertNotIn('GO CONDITIONNEL',out)
        self.assertEqual(count,1)

    def test_duplicate_event_json_key_holds_before_verification(self):
        code,out,err,count=self.call('{"type":"EXACT","type":"FORGED"}',human=True)
        self.assertEqual(code,8)
        self.assertIn('DUPLICATE_EVENT_JSON_KEY',err)
        self.assertEqual(count,0)
        self.assertEqual(out,'')

    def test_nested_duplicate_event_json_key_holds(self):
        code,out,err,count=self.call('{"type":"x","factory_run_ids":[{"x":1,"x":2}]}')
        self.assertEqual(code,8)
        self.assertIn('DUPLICATE_EVENT_JSON_KEY',err)
        self.assertEqual(count,0)

    def test_malformed_event_holds_without_handoff(self):
        code,out,err,count=self.call('{bad',human=True)
        self.assertEqual(code,8)
        self.assertEqual(out,'')
        self.assertEqual(count,0)
        self.assertIn('HOLD:',err)
