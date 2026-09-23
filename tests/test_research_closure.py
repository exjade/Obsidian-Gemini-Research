import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import research_scope
import research_closure as closure
import pipeline
from research_agents import DIMENSIONS, stable_digest


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'id':i,'claim':'Claim '+i,'status':'VERIFIED'} for i in ('a','b')]
        self.meta={'question':'Question','scope':{'status':'approved','selected_ids':['a','b'],
                   'candidates':[{'id':c['id'],'claim':c['claim']} for c in self.rows]}}
        self.meta['scope']['question_sha256']=research_scope.question_hash(self.meta)

    def scientific_record(self, claim, resolution):
        required='intervention'
        relation='supports' if resolution=='supported' else 'contradicts' if resolution=='refuted' else 'unreported'
        state='supported' if resolution=='supported' else 'contradicted' if resolution=='refuted' else 'unresolved'
        passage={'source_id':'source-1','evidence_id':'passage-1','relation':relation,
                 'source_status':'confirmed_primary','basis':'synthetic fixture'}
        dimensions={key:{'formulation':'active retrieval' if key==required else '',
            'state':state if key==required else 'unresolved',
            'evidence_strength':'direct' if resolution=='supported' else
                'contradictory' if resolution=='refuted' else 'unreported',
            'evidence':[passage] if key==required else [], 'retrieval_targets':[]} for key in DIMENSIONS}
        receipts=[]
        for round_no in (1,2,3):
            receipts.extend([
                {'round':round_no,'target_dimensions':[required],'target_purposes':['support'],
                 'remaining':{'global_queries':4,'global_pages':8,'seconds':1200}},
                {'round':round_no,'target_dimensions':[required],'target_purposes':['contradiction'],
                 'remaining':{'global_queries':4,'global_pages':8,'seconds':1200}},
            ])
        unresolved=[required] if resolution=='indeterminate' else []
        return {'policy':'scientific-resolution-v1','version':1,'resolution_id':'resolution-1',
            'resolution':resolution,'claim_id':claim['id'],'claim_sha256':stable_digest(claim['claim']),
            'input_fingerprint':'inputs-1','evidence_mode':'question_search','dimensions':dimensions,
            'unresolved_dimensions':unresolved,'budget_receipts':receipts,
            'audit_decision':{'supported':'sufficient_support','refuted':'direct_contradiction',
                              'indeterminate':'exhausted'}[resolution],
            'skeptic_verdict':{'supported':'VERIFIED','refuted':'CONTRADICTED',
                               'indeterminate':'UNSUPPORTED'}[resolution],
            'documents_considered':resolution=='indeterminate',
            'indeterminacy_criteria':['all_supplied_inputs_considered','bounded_search_complete',
                                      'unresolved_dimensions_targeted'] if resolution=='indeterminate' else [],
            'audit_unresolved_dimensions':unresolved,
            'limitations':'El protocolo acotado no resolvió estas dimensiones; esto no demuestra que no existan estudios.'
                if resolution=='indeterminate' else ''}

    def test_one_unresolved_blocks_whole_approved_scope(self):
        self.rows[1]['status']='UNSUPPORTED'
        state=closure.assess(self.meta,self.rows,lambda c:None)
        self.assertFalse(state['ready']);self.assertEqual(state['resolved'],1)
        self.assertIn('no refuta',state['blockers'][0]['reason'])
        report=closure.provisional('Case',state)
        self.assertIn('Informe provisional',report);self.assertIn('Siguiente acción',report)

    def test_excluded_candidate_does_not_block_approved_scope(self):
        self.rows.append({'id':'outside','claim':'Outside','status':'UNSUPPORTED'})
        self.assertTrue(closure.assess(self.meta,self.rows,lambda c:None)['ready'])

    def test_budget_exhaustion_alone_does_not_count_as_scientific_resolution(self):
        self.rows[1]['status']='UNSUPPORTED'
        self.rows[1]['bounded_resolution']={'status':'excluded_with_limit','reason':'Falta una medición diferida.'}
        state=closure.assess(self.meta,self.rows,lambda c:None)
        self.assertFalse(state['ready']);self.assertEqual(state['limited'],0)
        report=closure.scope_summary(state)
        self.assertIn('Pendiente: el protocolo todavía no permite resolverla',report)
        self.assertIn('Falta una medición diferida',report)

    def test_indeterminate_requires_complete_explicit_criteria_and_attempted_gaps(self):
        self.rows[1]['status']='UNSUPPORTED'
        self.rows[1]['scientific_resolution']=self.scientific_record(self.rows[1],'indeterminate')
        self.rows[1]['scientific_resolution_history']=[self.rows[1]['scientific_resolution']]
        self.assertTrue(closure.assess(self.meta,self.rows,lambda c:None)['ready'])

    def test_minimal_indeterminate_record_and_invalid_latest_record_do_not_close(self):
        claim=self.rows[0]
        claim['scientific_resolution']={'resolution':'indeterminate','limitations':'bounded',
            'dimensions':{'horizon':{'state':'unresolved'}},'resolution_id':'r1'}
        state=closure.assess(self.meta,self.rows,lambda c:None)
        self.assertFalse(state['ready']);self.assertEqual(state['resolved'],1)
        self.assertIn('desactualizada o incompleta',state['blockers'][0]['reason'])

    def test_scientific_supported_and_refuted_close_without_rewriting_legacy_verdict(self):
        for resolution, legacy in (('supported','UNSUPPORTED'),('refuted','VERIFIED')):
            with self.subTest(resolution=resolution):
                self.rows[0]['status']=legacy
                record=self.scientific_record(self.rows[0],resolution)
                self.rows[0]['scientific_resolution']=record
                self.rows[0]['scientific_resolution_history']=[record]
                state=closure.assess(self.meta,self.rows,lambda c:None)
                self.assertTrue(state['ready'])
                self.assertEqual(state['items'][0]['resolution'],resolution)
                self.assertEqual(self.rows[0]['status'],legacy)

    def test_invalid_policy_hash_dimension_or_unresolved_projection_blocks_without_legacy_fallback(self):
        for mutate in (
            lambda r:r.update(policy='foreign-policy'),
            lambda r:r.update(claim_sha256='stale'),
            lambda r:r['dimensions'].pop('horizon'),
            lambda r:r.update(resolution='unresolved'),
        ):
            claim=self.rows[0];claim['status']='VERIFIED'
            record=self.scientific_record(claim,'indeterminate');mutate(record)
            claim['scientific_resolution']=record;claim['scientific_resolution_history']=[record]
            state=closure.assess(self.meta,self.rows,lambda c:None)
            self.assertFalse(state['ready'])
            self.assertEqual(state['items'][0]['resolution'],'unresolved')
            claim.pop('scientific_resolution',None);claim.pop('scientific_resolution_history',None)

    def test_indeterminate_projection_with_directly_contradicted_dimension_is_rejected(self):
        claim=self.rows[0];claim['status']='UNSUPPORTED'
        record=self.scientific_record(claim,'indeterminate')
        record['dimensions']['population']={'formulation':'adults','state':'contradicted',
            'evidence_strength':'contradictory','evidence':[{'source_id':'source-2','evidence_id':'passage-2',
            'relation':'contradicts','source_status':'confirmed_primary'}],'retrieval_targets':[]}
        claim['scientific_resolution']=record;claim['scientific_resolution_history']=[record]
        self.assertFalse(closure.assess(self.meta,self.rows,lambda c:None)['ready'])

    def test_source_failure_cannot_become_refutation_or_indeterminacy(self):
        def blocked(c):raise ValueError('Acceso restringido')
        before=copy.deepcopy(self.rows)
        state=closure.assess(self.meta,self.rows,blocked)
        self.assertFalse(state['ready']);self.assertEqual(self.rows,before)
        self.assertEqual(state['resolved'],0)

    def test_changed_scope_blocks_and_writing_log_does_not_invalidate_signature(self):
        state=closure.assess(self.meta,self.rows,lambda c:None)
        self.rows[0]['writing_history']=[{'written_at':'now'}]
        self.assertEqual(state['input_sha256'],closure.assess(self.meta,self.rows,lambda c:None)['input_sha256'])
        self.rows[0]['claim']='Changed'
        self.assertFalse(closure.assess(self.meta,self.rows,lambda c:None)['ready'])

    def test_contradicted_requires_explicit_checked_refutation(self):
        with tempfile.TemporaryDirectory() as td,patch.object(pipeline,'ROOT',Path(td)),patch.object(pipeline,'INTEL',Path(td)/'.project-intelligence'):
            (Path(td)/'proof.txt').write_text('Evidence')
            claim={'id':'a','claim':'Claim','status':'CONTRADICTED','domain':'general','sensible':False,
                   'favorable':False,'risk_policy':pipeline.RISK_POLICY,'skeptic_note':'Review',
                   'contradiction_search':'Search','primary_sources':[],
                   'evidence':[{'type':'file','path':'proof.txt','lines':'1-1','excerpt':'Evidence'}]}
            with self.assertRaisesRegex(ValueError,'refutación directa'):pipeline.closure_evidence(claim)
            claim['evidence'][0]['relation']='contradiction'
            pipeline.closure_evidence(claim)
            (Path(td)/'proof.txt').write_text('Different')
            with self.assertRaises(ValueError):pipeline.closure_evidence(claim)

    def test_legacy_verdicts_do_not_automatically_close(self):
        with self.assertRaisesRegex(ValueError,'política actual'):pipeline.closure_evidence({'status':'VERIFIED'})

    def test_proposed_expansion_requires_decision_but_does_not_erase_resolutions(self):
        self.meta['scope_proposal']={'id':'proposal'}
        result=closure.assess(self.meta,self.rows,lambda c:None)
        self.assertFalse(result['ready']);self.assertEqual(result['resolved'],2)
        self.assertIn('ampliación propuesta',result['blockers'][0]['reason'])


if __name__=='__main__':unittest.main()
