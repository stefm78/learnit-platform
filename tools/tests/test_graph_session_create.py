import json, unittest
from urllib.parse import urlsplit
from graph_session_create import SessionCreateFile, Hold

D='B9B0D852F6CCE2CD'
class Fake:
    def __init__(self,authorized=True, code=201, post=200, session_url='https://session.up.1drv.com/opaque?secret=x'):
        self.auth=authorized;self.code=code;self.post=post;self.session_url=session_url;self.actions=[]
    def assert_real_provider_and_scoped_authorization(self):
        if not self.auth:raise Hold('NO_LIVE_PROVIDER_PROOF')
    def post_graph_json(self,url,body):
        self.actions.append(('POST',url,body))
        return self.post,json.dumps({'uploadUrl':self.session_url}).encode()
    def approve_upload_url(self,url):
        self.actions.append(('APPROVE',url))
        return urlsplit(url).hostname == 'session.up.1drv.com'
    def upload_without_bearer(self,url,content):
        self.actions.append(('UPLOAD',url,content))
        return self.code,json.dumps({'id':'file_new','name':'kit.json','size':len(content),'file':{}}).encode()

class TestSession(unittest.TestCase):
    def test_requires_provider_proof_before_request(self):
        t=Fake(False)
        with self.assertRaisesRegex(Hold,'NO_LIVE_PROVIDER_PROOF'):
            SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'{}')
        self.assertEqual(t.actions,[])
    def test_uses_documented_upload_session_contract(self):
        t=Fake();item=SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'{}')
        self.assertEqual(item['id'],'file_new')
        self.assertEqual([a[0] for a in t.actions],['POST','APPROVE','UPLOAD'])
        self.assertIn(b'"@microsoft.graph.conflictBehavior":"fail"',t.actions[0][2])
        self.assertTrue(t.actions[0][1].endswith(':/createUploadSession'))
    def test_no_simple_put_content(self):
        t=Fake();SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'{}')
        self.assertNotIn(':/content',t.actions[0][1])
    def test_200_response_fails_closed(self):
        t=Fake(code=200)
        with self.assertRaisesRegex(Hold,'NOT_EXCLUSIVELY_CREATED_200'):
            SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'{}')
    def test_409_no_retries(self):
        t=Fake(code=409)
        with self.assertRaisesRegex(Hold,'NOT_EXCLUSIVELY_CREATED_409'):
            SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'{}')
        self.assertEqual(len(t.actions),3)
    def test_http_403_session_no_upload(self):
        t=Fake(post=403)
        with self.assertRaisesRegex(Hold,'SESSION_FAILED_403'):
            SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'{}')
        self.assertEqual(len(t.actions),1)
    def test_invalid_upload_url_hold(self):
        t=Fake(session_url='http://example.com/secret')
        with self.assertRaisesRegex(Hold,'URL_UNTRUSTED'):
            SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'{}')
        self.assertEqual(len(t.actions),1)
    def test_url_never_in_error(self):
        t=Fake(session_url='http://evil.invalid/supersecret')
        try:SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'{}')
        except Hold as e:self.assertNotIn('supersecret',str(e))
    def test_invalid_file_name_no_create(self):
        t=Fake()
        with self.assertRaisesRegex(Hold,'INVALID_PARENT'):
            SessionCreateFile(D,t).create_file_fail('parent','../path.json',b'{}')
        self.assertEqual(t.actions,[])
    def test_timeout_no_retry(self):
        t=Fake(code=504)
        with self.assertRaisesRegex(Hold,'NOT_EXCLUSIVELY_CREATED_504'):
            SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'{}')
        self.assertEqual(len(t.actions),3)

    def test_unauthorized_https_origin_never_gets_content(self):
        t=Fake(session_url='https://evil.example/collect?token=signed-secret')
        with self.assertRaisesRegex(Hold,'URL_NOT_APPROVED'):
            SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'KIT_BYTES')
        self.assertEqual([a[0] for a in t.actions],['POST','APPROVE'])
    def test_https_unexpected_port_never_gets_content(self):
        t=Fake(session_url='https://session.up.1drv.com:8443/collect')
        with self.assertRaisesRegex(Hold,'URL_UNTRUSTED'):
            SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'KIT_BYTES')
        self.assertEqual(len(t.actions),1)
    def test_missing_url_approver_must_hold(self):
        t=Fake(); t.approve_upload_url=None
        with self.assertRaisesRegex(Hold,'APPROVAL_UNAVAILABLE'):
            SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'KIT_BYTES')
        self.assertEqual(len(t.actions),1)
    def test_failing_approver_redacts_signed_url(self):
        t=Fake(session_url='https://session.up.1drv.com/a?token=supersecret')
        def broken(url): raise RuntimeError('leaked '+url)
        t.approve_upload_url=broken
        with self.assertRaises(Hold) as ctx:
            SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'KIT_BYTES')
        self.assertNotIn('supersecret',str(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)
    def test_transport_failure_redacts_signed_url(self):
        t=Fake(session_url='https://session.up.1drv.com/a?token=supersecret')
        def broken(url,raw): raise RuntimeError('leaked '+url)
        t.upload_without_bearer=broken
        with self.assertRaisesRegex(Hold,'OUTCOME_UNCERTAIN') as ctx:
            SessionCreateFile(D,t).create_file_fail('parent','kit.json',b'KIT_BYTES')
        self.assertNotIn('supersecret',str(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)

if __name__=='__main__':unittest.main()
