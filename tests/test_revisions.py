import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import copy
import json
import tempfile
import unittest
from unittest.mock import patch
import pipeline as p
import library as lib
import revisions
from setup import initialize

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.patches=[patch.object(p,'ROOT',self.root),patch.object(p,'INTEL',self.root/'.project-intelligence'),patch.object(lib,'ROOT',self.root),patch.object(lib,'BASE',self.root/'.project-intelligence/library')]
        for item in self.patches:item.start()
        initialize(self.root);(self.root/'GEMINI.md').write_text('fixture');(self.root/'src/proof.txt').write_text('fixture proof\n')
        cid='fixture-case';self.folder=lib.case_path(cid);self.folder.mkdir()
        lib.save(self.folder/'case.json',{'id':cid,'title':'Fixture','question':'Fixture question','links':'','materials':[],'tags':[],'status':'completed','created_at':'2026-01-01','claim_ids':['target','other']})
        self.rows=[{'id':ident,'claim':'Statement '+ident,'category':'architecture','requires_external':False,'status':'UNSUPPORTED','evidence':[],'investigation_id':cid,'risk_policy':p.RISK_POLICY,'hypothesis_source':'DO_NOT_SEND_TO_SKEPTIC'} for ident in ('target','other')]
        p.persist(self.rows);lib.write(self.folder/'resultados.md','PREVIOUS PUBLISHED REPORT');lib.refresh(self.rows)
        self.seen=[];self.fail_stage=None
        test=self
        class Runner:
            run_id='fixture-run'
            def call(self,stage,instructions,data):
                test.seen.append((stage,copy.deepcopy(data)))
                if stage==test.fail_stage:raise ValueError('fixture failure '+stage)
                if stage=='pass2':return [{**c,'status':'UNVERIFIED','evidence':[{'type':'file','path':'src/proof.txt','lines':'1-1','excerpt':'fixture proof'}]} for c in data['claims']]
                if stage=='pass3':return [{**c,'status':'VERIFIED','domain':'general','sensible':False,'favorable':False,'skeptic_note':'fixture','contradiction_search':'fixture searched','primary_sources':[{'evidence_index':0,'independence_group':'fixture','reason':'fixture'}]} for c in data]
                if stage=='pass4':return [{'id':c['id'],'text':'Published '+c['claim']} for c in data]
                raise AssertionError(stage)
        self.runner=Runner
    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        self.temp.cleanup()
    def run_review(self,ident):
        with patch.object(sys,'argv',['pipeline.py','document','--case','fixture-case','--claim','target','--revision',ident]),patch.object(p,'Runner',self.runner),patch.object(p,'working_diff_context',return_value={'diff':'fixture'}),patch.object(p,'sync_docs'):
            p.main()
    def test_selective_review_and_materials(self):
        request=revisions.submit('fixture-case','target','https://example.org/original','New material')
        self.run_review(request['id']);rows={c['id']:c for c in p.all_claims()}
        self.assertEqual(rows['target']['status'],'VERIFIED');self.assertEqual(rows['other'],self.rows[1])
        self.assertEqual(rows['target']['provenance'][-1]['revision_id'],request['id'])
        collector=self.seen[0][1];self.assertEqual(len(collector['claims']),1)
        self.assertEqual(collector['git_context']['new_materials_unverified']['supplied_context_unverified'],'New material')
        skeptic=next(data for stage,data in self.seen if stage=='pass3')
        self.assertNotIn('DO_NOT_SEND_TO_SKEPTIC',json.dumps(skeptic));self.assertNotIn('New material',json.dumps(skeptic))
        history=revisions.history('fixture-case');self.assertEqual(history[0]['status'],'completed')
        self.assertEqual((revisions.folder('fixture-case',request['id'])/'previous_resultados.md').read_text(),'PREVIOUS PUBLISHED REPORT')
        self.assertEqual(lib.read(self.root/'.project-intelligence/state.json')['claims']['VERIFIED'],1)
        with self.assertRaises(ValueError):self.run_review(request['id'])
        self.assertEqual(revisions.history('fixture-case')[0]['status'],'completed')
        second=revisions.submit('fixture-case','target');self.run_review(second['id'])
        self.assertEqual(len(revisions.history('fixture-case')),2)
        self.assertEqual(len(p.all_claims()),2)
        self.assertEqual(lib.read(self.root/'.project-intelligence/state.json')['claims']['VERIFIED'],1)
    def test_collector_failure_preserves_verdict_and_report(self):
        request=revisions.submit('fixture-case','target');self.fail_stage='pass2'
        with self.assertRaises(ValueError):self.run_review(request['id'])
        self.assertEqual(p.all_claims(),self.rows);self.assertEqual((self.folder/'resultados.md').read_text(),'PREVIOUS PUBLISHED REPORT')
        self.assertEqual(revisions.history('fixture-case')[0]['status'],'error')
        self.assertFalse((self.root/'.project-intelligence/pipeline.lock').exists())
    def test_writer_failure_preserves_review(self):
        request=revisions.submit('fixture-case','target');self.fail_stage='pass4'
        with self.assertRaises(ValueError):self.run_review(request['id'])
        self.assertEqual(p.all_claims()[0]['status'],'VERIFIED');self.assertEqual((self.folder/'resultados.md').read_text(),'PREVIOUS PUBLISHED REPORT')
        record=revisions.history('fixture-case')[0];self.assertTrue(record['review_completed']);self.assertFalse(record.get('publication_completed',False))
    def test_invalid_scope_and_limits(self):
        with self.assertRaises(ValueError):revisions.submit('fixture-case','missing')
        with self.assertRaises(ValueError):revisions.submit('fixture-case','target','x'*100001)
        with self.assertRaises(ValueError):revisions.folder('fixture-case','../outside')
        request=revisions.submit('fixture-case','target')
        with self.assertRaises(ValueError):revisions.load('fixture-case',request['id'],'other')

    def test_frontend_request_and_busy_guard(self):
        import frontend,threading,urllib.request,urllib.error
        seen=[];event=threading.Event()
        def worker(mode,brief,case_id,review):seen.append((mode,case_id,review));event.set()
        intel=self.root/'.project-intelligence'
        with patch.object(frontend,'INTEL',intel),patch.object(frontend,'worker',worker),patch.object(frontend,'JOB',{'status':'idle','log':'','stage':''}):
            server=frontend.ThreadingHTTPServer(('127.0.0.1',0),frontend.Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            url='http://127.0.0.1:'+str(server.server_port)+'/api/run'
            def send(payload):return json.load(urllib.request.urlopen(urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'X-Local-Token':frontend.TOKEN,'Content-Type':'application/json'})))
            payload={'mode':'reevaluate','case_id':'fixture-case','claim_id':'target','new_links':'https://example.org/original','new_context':'Supplemental material'}
            try:
                with self.assertRaises(urllib.error.HTTPError) as error:send({**payload,'claim_id':'missing'})
                self.assertEqual(error.exception.code,400)
                response=send(payload);self.assertTrue(event.wait(2));self.assertEqual(seen[0][0],'reevaluate')
                request=revisions.load('fixture-case',response['revision_id'],'target');self.assertEqual(request['supplied_context_unverified'],'Supplemental material')
                with self.assertRaises(urllib.error.HTTPError) as error:send(payload)
                self.assertEqual(error.exception.code,409);self.assertEqual(len(revisions.history('fixture-case')),1)
            finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
