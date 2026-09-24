import copy
import json
import unittest
from unittest.mock import patch
import test_revisions as fixtures
import human_review as h
import pipeline as p
import library

class HumanReviewTests(unittest.TestCase):
    setUp=fixtures.ReviewTests.setUp
    tearDown=fixtures.ReviewTests.tearDown
    def reviewed_claim(self):
        rows=copy.deepcopy(self.rows)
        rows[0]['evidence']=[{'type':'file','path':'src/proof.txt','lines':'1-1','excerpt':'fixture proof'}]
        p.persist(rows);library.refresh(rows)
        return rows[0]
    def submit(self,c,**changes):
        args={'case_id':'fixture-case','claim_id':c['id'],'actor':'Human reviewer','decision':'supports',
              'indices':[0],'notes':'Read the source and compared the passage','limits':'Does not establish causality',
              'expected_fingerprint':h.fingerprint(c)}
        args.update(changes)
        return h.record(**args)
    def test_observation_never_changes_verdict_and_keeps_snapshot(self):
        c=self.reviewed_claim();c['claim_version']=4;p.persist([c,self.rows[1]]);library.refresh(p.all_claims());before=p.all_claims()
        receipt=self.submit(c)
        self.assertEqual(p.all_claims(),before)
        self.assertEqual(receipt['automatic_status_at_review'],'UNSUPPORTED')
        self.assertFalse(receipt['automatic_verdict_changed'])
        self.assertEqual(receipt['claim_version'],4)
        self.assertEqual(receipt['examined_evidence'][0]['evidence'],c['evidence'][0])
        self.assertTrue((self.folder/'revisiones-humanas.md').exists())

    def test_legacy_review_does_not_invent_claim_version(self):
        c=self.reviewed_claim()
        c.pop('claim_version',None)
        p.persist([c,self.rows[1]]);library.refresh(p.all_claims())
        receipt=self.submit(c)
        self.assertNotIn('claim_version',receipt)
    def test_history_is_append_only_and_scoped(self):
        c=self.reviewed_claim();a=self.submit(c);b=self.submit(c,decision='uncertain')
        self.assertNotEqual(a['id'],b['id']);self.assertEqual(len(h.history('fixture-case')),2)
        with self.assertRaises(ValueError):self.submit(c,case_id='other-case')
        self.assertEqual(len(h.history('fixture-case')),2)
    def test_stale_form_and_bad_fields_rejected(self):
        c=self.reviewed_claim()
        for change in [{'actor':''},{'notes':''},{'limits':''},{'decision':'VERIFIED'},{'indices':[]},{'indices':[False]},{'indices':[2]},{'indices':[0,0]},{'expected_fingerprint':'stale'}]:
            with self.subTest(change=change),self.assertRaises(ValueError):self.submit(c,**change)
        self.assertEqual(h.history('fixture-case'),[])
    def test_snapshot_survives_future_evidence_change(self):
        c=self.reviewed_claim();receipt=self.submit(c)
        changed=copy.deepcopy(c);changed['evidence'][0]['excerpt']='new passage';p.persist([changed,self.rows[1]]);library.refresh(p.all_claims())
        self.assertEqual(h.history('fixture-case')[0]['examined_evidence'][0]['evidence']['excerpt'],'fixture proof')
        self.assertNotEqual(h.fingerprint(changed),receipt['claim_fingerprint'])

    def test_api_authentication_busy_guard_and_no_verdict_promotion(self):
        import frontend,threading,urllib.request,urllib.error
        c=self.reviewed_claim();before=p.all_claims();job={'status':'idle','stage':'','log':''}
        with patch.object(frontend,'INTEL',p.INTEL),patch.object(frontend,'JOB',job):
            server=frontend.ThreadingHTTPServer(('127.0.0.1',0),frontend.Handler)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            url='http://127.0.0.1:'+str(server.server_port)+'/api/human-review'
            payload={'case_id':'fixture-case','claim_id':c['id'],'actor':'Reviewer','decision':'supports',
                     'indices':[0],'notes':'Examined this passage','limits':'Not a causal proof','claim_fingerprint':h.fingerprint(c)}
            def send(token):return json.load(urllib.request.urlopen(urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'X-Local-Token':token,'Content-Type':'application/json'})))
            try:
                with self.assertRaises(urllib.error.HTTPError) as error:send('wrong-token')
                self.assertEqual(error.exception.code,403)
                job['status']='running'
                with self.assertRaises(urllib.error.HTTPError) as error:send(frontend.TOKEN)
                self.assertEqual(error.exception.code,409);self.assertEqual(h.history('fixture-case'),[])
                job['status']='idle';response=send(frontend.TOKEN)
                self.assertTrue(response['claims_unchanged']);self.assertEqual(p.all_claims(),before)
            finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
