import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import documents as d
import library as lib
import pipeline as p
from setup import initialize


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.patches=[patch.object(lib,'ROOT',self.root),patch.object(lib,'BASE',self.root/'.project-intelligence/library'),
                      patch.object(p,'ROOT',self.root),patch.object(p,'INTEL',self.root/'.project-intelligence')]
        for x in self.patches:x.start()
        initialize(self.root)
        (self.root/'GEMINI.md').write_text('fixture contract',encoding='utf-8')
        for cid in ('case-a','case-b'):
            lib.save(lib.case_path(cid)/'case.json',{'id':cid,'title':'Fixture','question':'Fixture',
                   'tags':[],'created_at':'2026-01-01','status':'completed','claim_ids':['claim-a']})
            lib.save(lib.case_path(cid)/'claims.json',[{'id':'claim-a'}])
        self.raw=b'%PDF-1.7 fixture bytes'
        self.text='This original passage supports a precisely delimited claim and includes important limitations.'
        self.ident=d.import_pdf(self.root,'case-a',self.raw,'paper.pdf','https://example.org/paper','10.1234/paper')
        def converter(args,**kwargs):
            Path(args[3]).write_text(json.dumps({'pages':[{'physical_page':1,'text':self.text}],
                  'version':'fixture','ocr':False,'seconds':0.1,'metadata_declared_in_pdf':{'/Title':'Fixture'}}),encoding='utf8')
            return subprocess.CompletedProcess(args,0,b'',b'')
        with patch.object(d.subprocess,'run',converter):self.extraction=d.extract(self.root,self.ident)
        self.chunk=d.retrieve(self.root,'case-a','precisely delimited claim')[0]
        self.evidence={'type':'document','document_id':self.ident,'document_sha256':self.ident,
            'extraction_id':self.extraction['id'],'chunk_id':self.chunk['id'],'physical_page':1,'excerpt':self.text,
            'primary':True,'official':True,'primary_kind':'other'}
    def tearDown(self):
        for x in reversed(self.patches):x.stop()
        self.temp.cleanup()
    def test_exact_passage_and_identity_without_truth_promotion(self):
        receipt=d.validate(self.root,self.evidence,'case-a')
        self.assertTrue(receipt['eligible']);self.assertFalse(receipt['semantic_support_reviewed'])
        self.assertEqual((d.folder(self.root,self.ident)/'original.pdf').read_bytes(),self.raw)
        claim={'investigation_id':'case-a','evidence':[self.evidence],'status':'VERIFIED','requires_external':True,
               'domain':'general','sensible':False,'favorable':False,'skeptic_note':'fixture',
               'primary_sources':[{'evidence_index':0,'independence_group':'paper','reason':'fixture'}]}
        p.enforce_risk_policy(claim)
        self.assertEqual(claim['status'],'UNSUPPORTED')

    def test_unrelated_query_does_not_inject_zero_match_fragments(self):
        self.assertEqual(d.retrieve(self.root,'case-a','unrelated astronomy galaxies'),[])

    def test_verified_document_support_does_not_require_an_accessible_url(self):
        d.review_identity(self.root,'case-a',self.ident,'Reviewer','original_research',
                          'https://example.org/paper','10.1234/paper','Title and identity examined')
        pending={'id':'claim-a','claim':'precisely delimited claim','category':'dependencies','status':'UNVERIFIED',
                 'requires_external':True,'investigation_id':'case-a'}
        test=self
        class Runner:
            run_id='document-verified-fixture'
            def call(self,stage,instructions,data):
                if stage=='pass2':return [{**data['claims'][0],'status':'UNVERIFIED','evidence':[copy.deepcopy(test.evidence)]}]
                reviewed=copy.deepcopy(data[0]);reviewed['evidence'][0]['semantic_review']={
                    'target_claim_id':'claim-a','decision':'support','basis':'fixture exact passage support',
                    'limits':'','reviewer':'pass3'}
                return [{**reviewed,'status':'VERIFIED','domain':'general','sensible':False,
                         'favorable':False,'skeptic_note':'fixture review','contradiction_search':'fixture search',
                         'primary_sources':[{'evidence_index':0,'independence_group':'paper','reason':'original paper'}]}]
        self.assertEqual(p.evaluate(Runner(),[pending],{})[0]['status'],'VERIFIED')
    def test_scope_and_fabricated_page_or_quote_rejected(self):
        with self.assertRaises(ValueError):d.validate(self.root,self.evidence,'case-b')
        for field,value in [('physical_page',2),('excerpt','This invented quote is deliberately longer than forty characters.'),('document_sha256','0'*64)]:
            with self.assertRaises(ValueError):d.validate(self.root,{**self.evidence,field:value},'case-a')
        with self.assertRaises(ValueError):d.folder(self.root,'../escape')
    def test_duplicate_bytes_share_document_identity_not_independent_sources(self):
        ident=d.import_pdf(self.root,'case-a',self.raw,'renamed.pdf')
        self.assertEqual(ident,self.ident);self.assertEqual(len(d.records(self.root,'case-a')),1)
    def test_modified_extraction_or_original_rejected(self):
        out=d.folder(self.root,self.ident)/'extractions'/self.extraction['id']/'chunks.json'
        out.write_text('[]')
        with self.assertRaises(ValueError):d.validate(self.root,self.evidence,'case-a')
        (d.folder(self.root,self.ident)/'original.pdf').write_bytes(b'changed')
        with self.assertRaises(ValueError):d.import_pdf(self.root,'case-a',self.raw,'paper.pdf')
    def test_collector_receives_only_case_documents_and_skeptic_gets_source_context(self):
        pending={'id':'claim-a','claim':'precisely delimited claim','category':'dependencies','status':'UNVERIFIED',
                 'requires_external':True,'investigation_id':'case-a','hypothesis_source':'PRIVATE_INVESTIGATOR'}
        seen=[];test=self
        class Runner:
            run_id='document-fixture'
            def call(self,stage,instructions,data):
                seen.append((stage,copy.deepcopy(data)))
                evidence=copy.deepcopy(test.evidence)
                if stage=='pass2':return [{'id':'claim-a','claim':pending['claim'],'status':'UNVERIFIED','evidence':[evidence]}]
                return [{**data[0],'status':'UNSUPPORTED','domain':'general','sensible':False,'favorable':False,
                         'skeptic_note':'Publication identity unconfirmed','contradiction_search':'fixture', 'primary_sources':[]}]
        result=p.evaluate(Runner(),[pending],{})
        self.assertEqual(len(seen[0][1]['local_document_fragments']),1)
        self.assertEqual(seen[1][1][0]['evidence'][0]['document_context'],self.text)
        self.assertNotIn('PRIVATE_INVESTIGATOR',json.dumps(seen[1][1]))
        self.assertEqual(result[0]['status'],'UNSUPPORTED')
    def test_failed_conversion_is_visible_and_does_not_destroy_previous_extraction(self):
        with patch.object(d.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'',b'fixture failure')):
            with self.assertRaises(ValueError):d.extract(self.root,self.ident,'docling-standard')
        record=d.records(self.root,'case-a')[0]
        self.assertEqual(record['active_extraction'],self.extraction['id'])
        self.assertEqual(record['extractions'][-1]['status'],'error')
        self.assertTrue(d.validate(self.root,self.evidence,'case-a')['eligible'])

    def test_identity_review_is_not_a_verdict_and_reviews_remain_secondary(self):
        for kind,expected in [('review','UNSUPPORTED'),('original_research','VERIFIED')]:
            review=d.review_identity(self.root,'case-a',self.ident,'Reviewer',kind,
                   'https://example.org/paper','10.1234/paper','Title, authors and DOI examined; claim not reviewed.')
            self.assertEqual(review['scope'],'publication identity only; not claim truth')
            claim={'investigation_id':'case-a','evidence':[copy.deepcopy(self.evidence)],'status':'VERIFIED',
                   'requires_external':True,'domain':'general','sensible':False,'favorable':False,
                   'skeptic_note':'fixture','primary_sources':[{'evidence_index':0,'independence_group':'paper','reason':'fixture'}]}
            p.enforce_risk_policy(claim);self.assertEqual(claim['status'],expected)
        self.assertEqual(lib.read(lib.case_path('case-a')/'claims.json'),[{'id':'claim-a'}])
        self.assertEqual(d.identity_key(self.root,'case-a',self.evidence),
                         d.identity_key(self.root,'case-a',{'type':'external','url':'https://doi.org/10.1234/paper'}))
        with self.assertRaises(ValueError):d.review_identity(self.root,'case-b',self.ident,'Reviewer','original_research',
                                      'https://example.org/paper','10.1234/paper','fixture')

    def test_pdf_api_scope_authentication_and_page_download(self):
        import frontend,threading,urllib.request,urllib.error
        with patch.object(frontend,'ROOT',self.root),patch.object(frontend,'INTEL',self.root/'.project-intelligence'):
            server=frontend.ThreadingHTTPServer(('127.0.0.1',0),frontend.Handler)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            prefix='http://127.0.0.1:'+str(server.server_port)
            def request(route,token=True):
                headers={'X-Local-Token':frontend.TOKEN} if token else {}
                return urllib.request.urlopen(urllib.request.Request(prefix+route,headers=headers))
            try:
                route='/api/pdf?case=case-a&id='+self.ident
                self.assertEqual(request(route).read(),self.raw)
                with self.assertRaises(urllib.error.HTTPError) as error:request(route,False)
                self.assertEqual(error.exception.code,403)
                with self.assertRaises(urllib.error.HTTPError) as error:request('/api/pdf?case=case-b&id='+self.ident)
                self.assertEqual(error.exception.code,404)
                page=json.load(request('/api/pdf-passages?case=case-a&id='+self.ident+'&page=1'))
                self.assertEqual(page['page_text'],self.text)
                with self.assertRaises(urllib.error.HTTPError):request('/api/pdf-passages?case=case-a&id='+self.ident+'&page=2')
            finally:server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()
