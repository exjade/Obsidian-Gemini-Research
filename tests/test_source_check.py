import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
import source_check as sc
import pipeline

EXCERPT='A documented original sentence with sufficient length to compare against the retrieved page.'
def page(status=200,body=None,kind='text/html',**kwargs):
    return {'final_url':'https://example.org/article','http_status':status,'content_type':kind,
            'content_encoding':'identity','redirects':[],'body':body or ('<html><title>Article</title><p>'+EXCERPT+'</p></html>').encode(),'truncated':False,**kwargs}

class SourceTests(unittest.TestCase):
    def test_content_and_limits(self):
        check,_=sc.inspect('https://example.org/article',EXCERPT,lambda _:page())
        self.assertTrue(check['eligible'])
        for status,label in [(404,'NOT_FOUND'),(410,'NOT_FOUND'),(403,'RESTRICTED'),(429,'RESTRICTED'),(503,'HTTP_ERROR')]:
            check,_=sc.inspect('https://example.org/article',EXCERPT,lambda _:page(status))
            self.assertEqual(check['availability'],label);self.assertFalse(check['eligible'])
        check,_=sc.inspect('https://example.org/article',EXCERPT,lambda _:page(body=b'<title>404 Page Not Found</title>'))
        self.assertEqual(check['availability'],'SOFT_NOT_FOUND')
        check,_=sc.inspect('https://example.org/article',EXCERPT,lambda _:page(body=b'<title>Changed content</title>Something different'))
        self.assertFalse(check['excerpt_match'])
        check,_=sc.inspect('https://example.org/article','short',lambda _:page())
        self.assertFalse(check['eligible'])
        check,_=sc.inspect('https://example.org/article',EXCERPT,lambda _:page(kind='application/pdf'))
        self.assertEqual(check['availability'],'UNSUPPORTED_FORMAT')
        def timeout(_):raise TimeoutError('fixture timeout')
        check,_=sc.inspect('https://example.org/article',EXCERPT,timeout)
        self.assertEqual(check['availability'],'ERROR')
    def test_block_private_destinations(self):
        for ip in ('127.0.0.1','10.1.2.3','169.254.169.254','::1','192.168.1.1','224.0.0.1','ff0e::1'):
            with patch.object(sc.socket,'getaddrinfo',return_value=[(2,1,6,'',(ip,443))]):
                with self.assertRaises(ValueError):sc.public_target('https://example.org/')
        for url in ('file:///etc/passwd','https://user:secret@example.org','https://example.org:8443'):
            with self.assertRaises(ValueError):sc.public_target(url)
    def test_redirect_revalidates_target(self):
        class Response:
            status=302
            def getheader(self,name):return 'http://127.0.0.1/private'
        class Connection:
            def __init__(self,*args,**kwargs):pass
            def request(self,*args,**kwargs):pass
            def getresponse(self):return Response()
            def close(self):pass
        with patch.object(sc,'public_target',side_effect=[(sc.urlsplit('https://example.org'),443,['93.184.216.34']),ValueError('private redirect blocked')]),patch.object(sc.http.client,'HTTPSConnection',Connection):
            record,_=sc.inspect('https://example.org',EXCERPT)
            self.assertFalse(record['eligible']);self.assertIn('blocked',record['error'])
    def test_receipts_and_publication_gate(self):
        evidence={'type':'external','url':'https://example.org/article','excerpt':EXCERPT,'primary':True,'official':True,'primary_kind':'official_documentation'}
        with tempfile.TemporaryDirectory() as td:
            directory=Path(td)/'source-checks'
            with patch.object(sc,'fetch',lambda _:page()):
                # inspect's default binds fetch, so explicitly provide a deterministic transport.
                real_inspect=sc.inspect
                with patch.object(sc,'inspect',lambda u,e:real_inspect(u,e,lambda _:page())):
                    receipt=sc.record_check(evidence,directory)
            evidence['source_check_id']=receipt['id']
            trusted=sc.trusted(evidence,directory)
            self.assertTrue(trusted['eligible'])
            self.assertEqual(trusted['snapshot_metadata_policy'],'source-snapshot-metadata-v1')
            self.assertEqual(trusted['normalized_final_url'],'example.org/article')
            self.assertEqual(trusted['persistent_identifiers'],[])
            self.assertNotIn('semantic_support',trusted)
            assertions=sc.trusted_metadata(evidence,directory)
            self.assertIn(('title','Article','source_check.page_title'),
                          {(a['field'],a['value'],a['provenance']) for a in assertions})
            self.assertIn(('final_url','https://example.org/article','source_check.final_url'),
                          {(a['field'],a['value'],a['provenance']) for a in assertions})
            self.assertIn(('normalized_final_url','example.org/article','source_check.normalized_final_url'),
                          {(a['field'],a['value'],a['provenance']) for a in assertions})
            self.assertEqual(sc.trusted_metadata({**evidence,'excerpt':'changed'},directory),[])
            self.assertTrue(sc.latest(evidence,directory)['eligible'])
            self.assertIsNone(sc.trusted({**evidence,'excerpt':'invented'},directory))
            claim={'evidence':[dict(evidence)],'status':'VERIFIED','domain':'general','sensible':False,'favorable':False,'skeptic_note':'fixture','primary_sources':[{'evidence_index':0,'independence_group':'original','reason':'fixture'}]}
            with patch.object(pipeline,'INTEL',Path(td)):
                pipeline.enforce_risk_policy(claim);self.assertEqual(claim['status'],'VERIFIED')
                forged=dict(claim);forged['evidence']=[{**evidence,'source_check_id':'0'*32}]
                pipeline.enforce_risk_policy(forged);self.assertEqual(forged['status'],'UNSUPPORTED')
                claim['evidence'][0].pop('source_check_id');pipeline.enforce_risk_policy(claim)
                self.assertEqual(claim['status'],'UNSUPPORTED')
            (directory/(receipt['id']+'.bin')).write_bytes(b'tampered')
            self.assertIsNone(sc.trusted(evidence,directory))

    def test_merged_persistent_identifier_provenance_is_neutral(self):
        evidence={'type':'external','url':'https://pubmed.ncbi.nlm.nih.gov/12345','excerpt':EXCERPT}
        with tempfile.TemporaryDirectory() as td:
            directory=Path(td)/'source-checks';real_inspect=sc.inspect
            final='https://example.org/article/10.9876/final-doi'
            result={'final_url':final,'http_status':200,'content_type':'text/html','content_encoding':'identity',
                    'redirects':[],'body':('<html><title>Article</title><p>'+EXCERPT+'</p></html>').encode(),'truncated':False}
            with patch.object(sc,'inspect',lambda u,e:real_inspect(u,e,lambda _:result)):
                receipt=sc.record_check(evidence,directory)
            evidence['source_check_id']=receipt['id']
            assertions=sc.trusted_metadata(evidence,directory)
            identifiers=[a for a in assertions if a['field'] in ('doi','pmid','pmcid')]
            self.assertEqual({(a['field'],a['value']) for a in identifiers},
                             {('pmid','12345'),('doi','10.9876/final-doi')})
            self.assertEqual({a['provenance'] for a in identifiers},{'source_check.persistent_identifier'})

    def test_four_pass_external_gate(self):
        import copy
        evidence={'type':'external','url':'https://example.org/article','excerpt':EXCERPT,'primary':True,'official':True,'primary_kind':'official_documentation','searched':True,'fetched':True,'retrieved_at':'2026-09-18T00:00:00Z'}
        candidate={'id':'fixture-id','claim':'fixture externally supported statement','requires_external':True,'status':'UNVERIFIED'}
        class Runner:
            run_id='fixture-run'
            def call(self,stage,instructions,data):
                if stage=='pass2':return [{'id':candidate['id'],'claim':candidate['claim'],'status':'UNVERIFIED','evidence':[copy.deepcopy(evidence)]}]
                if stage=='pass3':
                    reviewed=copy.deepcopy(data[0])
                    reviewed['evidence'][0]['semantic_review']={'target_claim_id':candidate['id'],'decision':'support','basis':'fixture exact passage support','limits':'','reviewer':'pass3'}
                    return [{**reviewed,'status':'VERIFIED','domain':'general','sensible':False,'favorable':False,'skeptic_note':'fixture review','contradiction_search':'fixture search','primary_sources':[{'evidence_index':0,'independence_group':'original','reason':'fixture'}]}]
                if stage=='pass4':return [{'id':candidate['id'],'text':'fixture published paragraph'}]
                raise AssertionError(stage)
        with tempfile.TemporaryDirectory() as td,patch.object(pipeline,'INTEL',Path(td)),patch.object(pipeline,'ROOT',Path(td)):
            (Path(td)/'GEMINI.md').write_text('fixture contract',encoding='utf-8')
            real_inspect=sc.inspect
            for status,expected in [(200,'VERIFIED'),(404,'UNSUPPORTED')]:
                with patch.object(sc,'inspect',lambda u,e:real_inspect(u,e,lambda _:page(status))):
                    result=pipeline.evaluate(Runner(),[copy.deepcopy(candidate)])
                self.assertEqual(result[0]['status'],expected)
                if expected=='VERIFIED':self.assertIn(candidate['id'],pipeline.writer(Runner(),result))

    def test_snapshot_api_scoped_and_authenticated(self):
        import frontend,library,threading,urllib.request,urllib.error
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);intel=root/'.project-intelligence';base=intel/'library';folder=base/'fixture-case';folder.mkdir(parents=True)
            e={'type':'external','url':'https://example.org/article','excerpt':EXCERPT}
            (folder/'claims.json').write_text(json.dumps([{'id':'fixture','evidence':[e]}]),encoding='utf-8')
            real_inspect=sc.inspect
            with patch.object(sc,'inspect',lambda u,e:real_inspect(u,e,lambda _:page())):receipt=sc.record_check(e,intel/'source-checks')
            with patch.object(frontend,'INTEL',intel),patch.object(library,'BASE',base):
                server=frontend.ThreadingHTTPServer(('127.0.0.1',0),frontend.Handler)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                url='http://127.0.0.1:'+str(server.server_port)+'/api/source-snapshot?case=fixture-case&id='+receipt['id']
                try:
                    def get(target,auth=True):return urllib.request.urlopen(urllib.request.Request(target,headers={'X-Local-Token':frontend.TOKEN} if auth else {}))
                    self.assertIn(EXCERPT,get(url).read().decode())
                    with self.assertRaises(urllib.error.HTTPError) as error:get(url,False)
                    self.assertEqual(error.exception.code,403)
                    with self.assertRaises(urllib.error.HTTPError) as error:get(url.replace('fixture-case','other-case'))
                    self.assertEqual(error.exception.code,404)
                finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
