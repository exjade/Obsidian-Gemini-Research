import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import evidence_reuse as reuse

class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.target=[{'id':'new','claim':'Recuperación espaciada mejora retención conceptual','investigation_id':'target'}]
    def case(self,name,rows):
        folder=self.root/'.project-intelligence/library'/name;folder.mkdir(parents=True)
        (folder/'claims.json').write_text(json.dumps(rows),encoding='utf-8')
    def row(self,url='https://example.invalid/paper',kind='external'):
        return {'id':'old','claim':'Recuperación espaciada y retención conceptual',
                'status':'VERIFIED','evidence':[{'type':kind,'url':url,'excerpt':'La recuperación espaciada afecta la retención conceptual.','primary':True,'relation':'contradiction'}]}
    def test_candidates_keep_counterevidence_without_transferring_verdict_or_primary(self):
        self.case('other',[self.row()]);rows=reuse.candidates(self.root,self.target)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['declared_relation'],'contradiction')
        self.assertEqual(rows[0]['relevance_review'],'pending')
        self.assertNotIn('status',rows[0]);self.assertNotIn('primary',rows[0])
        self.assertEqual(rows[0]['origin_case_id'],'other')
        self.assertEqual(rows[0]['relation_provenance'],'legacy_url_excerpt_noncanonical')
    def test_canonical_ids_and_origin_role_travel_as_provenance_only(self):
        row=self.row();row['evidence'][0].update(source_id='a'*64,evidence_id='b'*64,source_identity_policy='source-identity-v1')
        self.case('other',[row]);proposal=reuse.candidates(self.root,self.target)[0]
        self.assertEqual((proposal['source_id'],proposal['evidence_id']),('a'*64,'b'*64))
        self.assertEqual(proposal['relation_provenance'],'origin_claim_passage')
        selected=reuse.selected_origins({'source_id':'a'*64,'evidence_id':'b'*64},'new',[proposal])
        self.assertEqual(selected[0]['declared_relation'],'contradiction')
        self.assertEqual(reuse.selected_origins({'source_id':'c'*64,'evidence_id':'b'*64},'new',[proposal]),[])
    def test_excludes_current_case_private_notes_documents_and_unrelated_material(self):
        self.case('target',[self.row()]);self.case('pdf',[self.row(kind='document')])
        self.case('unrelated',[{'id':'x','claim':'Precios agrícolas','evidence':[{'type':'external','url':'https://example.invalid','excerpt':'Los precios agrícolas aumentan.'}]}])
        self.assertEqual(reuse.candidates(self.root,self.target),[])
    def test_bounded_deduplicated_and_origin_matches_exact_passage(self):
        self.case('other',[self.row(),self.row(),self.row('https://example.invalid/two')])
        rows=reuse.candidates(self.root,self.target,limit=1);self.assertEqual(len(rows),1)
        e={'url':rows[0]['url'],'excerpt':rows[0]['excerpt']}
        self.assertEqual(len(reuse.selected_origins(e,'new',rows)),1)
        self.assertEqual(reuse.selected_origins({**e,'excerpt':'Changed'},'new',rows),[])
        self.assertEqual(reuse.selected_origins(e,'wrong',rows),[])
    def test_corrupt_case_does_not_abort_other_retrieval(self):
        self.case('bad',[]);(self.root/'.project-intelligence/library/bad/claims.json').write_text('{')
        self.case('good',[self.row()]);self.assertEqual(len(reuse.candidates(self.root,self.target)),1)
    def test_relevance_review_cannot_target_other_claim_or_omit_limits(self):
        for review in (None,{'target_claim_id':'other','decision':'support','reason':'Reason','limits':'Limit'},
                       {'target_claim_id':'new','decision':'support','reason':'Reason'}):
            with self.assertRaisesRegex(ValueError,'pertinencia'):reuse.apply_review({'reuse_relevance':review},'new')
        evidence={'reuse_relevance':{'target_claim_id':'new','decision':'not_relevant','reason':'Different population','limits':'No direct support'},'relation':'support'}
        reuse.apply_review(evidence,'new');self.assertEqual(evidence['relation'],'context')
