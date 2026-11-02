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
if __name__=='__main__':unittest.main()
