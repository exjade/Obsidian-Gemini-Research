import copy
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import source_identity as identity
import pipeline as p

class SourceIdentityTests(unittest.TestCase):
    def test_catalogue_roles_are_stable_and_unknown_values_are_unreviewed(self):
        self.assertEqual(identity.CATALOG_POLICY,'source-catalog-v1')
        for role in ('support','contradiction','context','unreviewed'):
            self.assertEqual(identity.normalize_relation(role),role)
        for role in ('insufficient','mismatch',None,'SUPPORT'):
            self.assertEqual(identity.normalize_relation(role),'unreviewed')
    def test_catalogue_identity_requires_explicit_policy_and_sha256_ids(self):
        row={'source_identity_policy':identity.POLICY,'source_id':'a'*64,'evidence_id':'b'*64}
        self.assertTrue(identity.has_catalog_identity(row))
        for invalid in ({k:v for k,v in row.items() if k!='source_identity_policy'},
                        {**row,'source_identity_policy':'foreign'}, {**row,'source_id':'bad'},
                        {**row,'evidence_id':'B'*64}):
            self.assertFalse(identity.has_catalog_identity(invalid))
    def external(self,url):return {'type':'external','url':url,'excerpt':'Exact passage'}
    def test_tracking_and_fragments_do_not_create_new_documents(self):
        a=identity.identify(self.external('https://EXAMPLE.org/paper/?utm_source=x#part'))
        b=identity.identify(self.external('http://example.org/paper'))
        self.assertEqual(a['source_id'],b['source_id'])
        self.assertFalse(a['authenticity_confirmed']);self.assertFalse(a['semantic_support_confirmed'])
    def test_semantic_query_and_path_case_are_preserved(self):
        a=identity.identify(self.external('https://example.org/Paper?id=1'))
        for url in ['https://example.org/Paper?id=2','https://example.org/paper?id=1']:
            self.assertNotEqual(a['source_id'],identity.identify(self.external(url))['source_id'])
    def test_doi_article_pdf_and_resolver_share_identity(self):
        urls=['https://doi.org/10.1234/abc','https://link.springer.com/article/10.1234/abc',
              'https://link.springer.com/content/pdf/10.1234/abc.pdf']
        self.assertEqual(len({identity.identify(self.external(url))['source_id'] for url in urls}),1)
    def test_source_same_passages_different_and_independence_transitive(self):
        a=identity.identify(self.external('https://example.org/a'))
        b=identity.identify(self.external('https://example.org/b'),{'final_url':'https://example.org/a'})
        c=identity.identify(self.external('https://example.org/c'))
        self.assertEqual(identity.independent_count([(a,'one'),(b,'two'),(c,'two')]),1)
        other=identity.identify({**self.external('https://example.org/a'),'excerpt':'Different passage'})
        self.assertEqual(a['source_id'],other['source_id']);self.assertNotEqual(a['evidence_id'],other['evidence_id'])
    def test_pubmed_and_pmc_aliases_and_local_reviewed_doi(self):
        self.assertEqual(identity.url_identifier('https://pubmed.ncbi.nlm.nih.gov/39633235/'),'pmid:39633235')
        self.assertEqual(identity.url_identifier('https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123/'),'pmcid:PMC123')
        doc=identity.identify({'type':'document','document_sha256':'a'*64},reviewed_key=('doi','10.1234/abc'))
        web=identity.identify(self.external('https://doi.org/10.1234/abc'))
        self.assertEqual(doc['source_id'],web['source_id'])
    def test_identical_retrieved_bytes_not_independent(self):
        receipt={'eligible':True,'body_sha256':'a'*64}
        a=identity.identify(self.external('https://example.org/a'),receipt)
        b=identity.identify(self.external('https://another.org/b'),receipt)
        self.assertEqual(identity.independent_count([(a,'one'),(b,'two')]),1)
        component=identity.independence_components([(a,'one'),(b,'two')])[0]
        self.assertEqual(component['scientific_independence'],'not_established')
        self.assertEqual(component['members'],[0,1])

    def test_assessment_keeps_primary_independence_and_semantics_separate(self):
        evidence={**self.external('https://example.org/original'),'primary':True,'official':True}
        assessment=identity.assess(evidence,{'availability':'AVAILABLE','eligible':True,'body_sha256':'a'*64})
        self.assertEqual(assessment['primary']['status'],'provider_declared_primary')
        self.assertEqual(assessment['independence']['status'],'not_established')
        self.assertEqual(assessment['semantic_support']['status'],'unreviewed')
        self.assertEqual(assessment['authenticity']['status'],'not_confirmed')

    def test_reviewed_document_identity_does_not_confirm_semantic_support(self):
        evidence={'type':'document','document_sha256':'a'*64,'primary':True}
        assessment=identity.assess(evidence,reviewed_key=('doi','10.1234/abc'))
        self.assertEqual(assessment['identity']['basis'],'reviewed_document_identity')
        self.assertEqual(assessment['primary']['status'],'provider_declared_primary')
        self.assertTrue(assessment['primary']['document_identity_reviewed'])
        self.assertEqual(assessment['primary']['basis'],'provider_annotation_only')
        self.assertEqual(assessment['semantic_support']['status'],'unreviewed')
    def test_wrapper_duplicate_sources_downgraded_and_contradiction_not_support(self):
        evidence=[{**self.external(url),'primary':True,'official':True} for url in
                  ['https://doi.org/10.1234/abc','https://link.springer.com/article/10.1234/abc']]
        c={'evidence':evidence,'status':'VERIFIED','domain':'medical','sensible':True,'favorable':False,
           'requires_external':True,'skeptic_note':'Review','primary_sources':[
               {'evidence_index':i,'independence_group':str(i),'reason':'declared original'} for i in range(2)]}
        with patch.object(p.source_check,'trusted',return_value={'eligible':True}):p.enforce_risk_policy(c)
        self.assertEqual(c['primary_source_count'],1);self.assertEqual(c['status'],'PARTIAL')
        c['status']='VERIFIED'
        for e in c['evidence']:e['relation']='contradiction'
        with patch.object(p.source_check,'trusted',return_value={'eligible':True}):p.enforce_risk_policy(c)
        self.assertEqual(c['status'],'UNSUPPORTED');self.assertEqual(c['primary_source_count'],0)
    def test_absence_of_refutation_not_contradicted(self):
        c={'evidence':[self.external('https://example.org/a')],'status':'CONTRADICTED','domain':'general',
           'sensible':False,'favorable':False,'skeptic_note':'Review','primary_sources':[]}
        with patch.object(p.source_check,'trusted',return_value={'eligible':True}):p.enforce_risk_policy(c)
        self.assertEqual(c['status'],'UNSUPPORTED')
        c['status']='CONTRADICTED';c['evidence'][0]['relation']='contradiction'
        with patch.object(p.source_check,'trusted',return_value={'eligible':True}):p.enforce_risk_policy(c)
        self.assertEqual(c['status'],'CONTRADICTED')

    def test_new_verified_gate_requires_semantic_claim_passage_support(self):
        evidence={**self.external('https://example.org/a'),'primary':True,'official':True}
        claim={'id':'claim','evidence':[evidence],'status':'VERIFIED','domain':'general','sensible':False,
               'favorable':False,'requires_external':True,'skeptic_note':'Review','primary_sources':[
                   {'evidence_index':0,'independence_group':'one','reason':'original'}]}
        with patch.object(p.source_check,'trusted',return_value={'eligible':True,'availability':'AVAILABLE'}):
            p.enforce_risk_policy(claim,require_semantic=True)
        self.assertEqual(claim['status'],'UNSUPPORTED')
        self.assertEqual(claim['primary_source_gate'][0]['reason'],'semantic_support_not_confirmed')
        supported=copy.deepcopy(claim);supported['status']='VERIFIED'
        supported['evidence'][0]['semantic_review']={'target_claim_id':'claim','decision':'support',
            'basis':'The exact passage supports the complete claim.','limits':'','reviewer':'pass3'}
        with patch.object(p.source_check,'trusted',return_value={'eligible':True,'availability':'AVAILABLE'}):
            p.enforce_risk_policy(supported,require_semantic=True)
        self.assertEqual(supported['status'],'VERIFIED')

if __name__=='__main__':unittest.main()
