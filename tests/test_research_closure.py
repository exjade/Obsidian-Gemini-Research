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


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'id':i,'claim':'Claim '+i,'status':'VERIFIED'} for i in ('a','b')]
        self.meta={'question':'Question','scope':{'status':'approved','selected_ids':['a','b'],
                   'candidates':[{'id':c['id'],'claim':c['claim']} for c in self.rows]}}
        self.meta['scope']['question_sha256']=research_scope.question_hash(self.meta)

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

    def test_bounded_unresolved_claim_allows_completion_with_limits(self):
        self.rows[1]['status']='UNSUPPORTED'
        self.rows[1]['bounded_resolution']={'status':'excluded_with_limit','reason':'Falta una medición diferida.'}
        state=closure.assess(self.meta,self.rows,lambda c:None)
        self.assertTrue(state['ready']);self.assertEqual(state['limited'],1)
        report=closure.scope_summary(state)
        self.assertIn('Parte de la pregunta que no pudimos responder',report)
        self.assertIn('Falta una medición diferida',report)

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
