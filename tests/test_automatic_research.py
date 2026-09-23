import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import research_agents
import research_operations
import frontend
import library


class FakeProvider:
    def __init__(self,decision='continue'):
        self.decision=decision;self.round=0;self.calls=[]
    def __call__(self,call):
        self.calls.append(call);r=call.role
        if r=='planner':return {'matrix':{k:('long-term' if k=='horizon' else k) for k in research_agents.DIMENSIONS},'gaps':['delayed measure']}
        if r=='formulation_reviewer':return {'compound':True,'subquestions':[{'id':'sub-1','claim':'Delayed retention','within_scope':True}]}
        if r=='locator':
            self.round+=1;return {'candidates':[{'query':f'delayed retention {self.round}','doi':f'10.1/{self.round}'}],
                                  'usage_events':[{'type':'query','query':f'delayed retention {self.round}'}]}
        if r=='retriever':return {'sources':[{'source_id':f's{self.round}','url':f'https://example.org/{self.round}','passages':[{'evidence_id':f'e{self.round}','excerpt':'Immediate test only.','page':1}]}],
                                  'usage_events':[{'type':'page','url':f'https://example.org/{self.round}'}]}
        if r=='source_evaluator':return {'assessments':[{'source_id':f's{self.round}','identity_status':'confirmed','credibility_status':'credible','credibility_basis':'peer reviewed source','primary_status':'confirmed_primary','primary_basis':'original study','independence_status':'not_established','independence_basis':'no duplicate signal is not proof','access':'available'}]}
        if r=='relevance_evaluator':
            relation='supports' if self.decision=='sufficient_support' else 'mismatch'
            return {'matrix':[{'source_id':f's{self.round}','evidence_id':f'e{self.round}','dimensions':{k:('supports' if self.decision=='sufficient_support' else ('mismatch' if k=='horizon' else 'supports')) for k in research_agents.DIMENSIONS},'overall_relation':relation,'basis':'Exact claim-passage audit'}]}
        if r=='skeptic':return {'verdict':'UNSUPPORTED','rationale':'Immediate measurement does not establish long-term retention.','contradiction_search':'No direct contradiction found.','support_source_ids':[]}
        if r=='final_auditor':return {'decision':'exhausted' if self.round==3 else self.decision,'explanation':'Temporal horizon remains unreported.','errors':[]}
        if r=='writer':return {'summary':'No se pudo confirmar la afirmación completa.','what_found':'Estudios inmediatos.','limits':'Falta medición diferida.','unanswered':'Retención a largo plazo.'}
        raise AssertionError(r)


class AutomaticResearchTests(unittest.TestCase):
    def test_frontend_reuses_failed_claim_research_operation(self):
        with tempfile.TemporaryDirectory() as temp:
            old=frontend.INTEL
            try:
                frontend.INTEL=Path(temp)
                first,created=frontend.operation_start('claim_research','case','claim')
                self.assertTrue(created)
                frontend.operation_update(first['id'],status='error',error='bad json')
                retried,restarted=frontend.operation_start('claim_research','case','claim')
                self.assertTrue(restarted)
                self.assertEqual(retried['id'],first['id'])
                self.assertEqual(retried['status'],'queued')
                self.assertIsNone(retried['error'])
            finally:frontend.INTEL=old

    def test_frontend_does_not_repeat_completed_claim_research(self):
        with tempfile.TemporaryDirectory() as temp:
            old=frontend.INTEL
            try:
                frontend.INTEL=Path(temp)
                first,created=frontend.operation_start('claim_research','case','claim')
                self.assertTrue(created)
                frontend.operation_update(first['id'],status='done',result={'outcome':'completed_with_limits'})
                same,created_again=frontend.operation_start('claim_research','case','claim')
                self.assertFalse(created_again)
                self.assertEqual(same['id'],first['id'])
            finally:frontend.INTEL=old

    def test_retry_reuses_validated_checkpoints_and_usage(self):
        provider=FakeProvider()
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            op=store.create('case','claim','Elaborative learning improves long-term retention')
            engine=research_operations.ResearchOrchestrator(store,provider)
            budget=research_operations.BudgetLedger(0,clock=lambda:0)
            budget.begin_round(research_operations.ROUNDS[0])
            operation=store.load(op['operation_id'])
            first=engine._call(operation,'locator',{'claim':'x'},budget,research_operations.ROUNDS[0])
            calls=len(provider.calls)
            retry_budget=research_operations.BudgetLedger(0,clock=lambda:0)
            retry_budget.begin_round(research_operations.ROUNDS[0])
            second=engine._call(operation,'locator',{'claim':'x'},retry_budget,research_operations.ROUNDS[0])
            self.assertEqual(first,second)
            self.assertEqual(len(provider.calls),calls)
            self.assertEqual(len(retry_budget.queries),1)

    def test_one_agent_budget_violation_does_not_fail_whole_operation(self):
        base=FakeProvider()
        def limited(call):
            if call.role=='retriever' and base.round>1:
                raise research_operations.BudgetExceeded('retriever intentó exceder el saldo')
            return base(call)
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            op=store.create('case','claim','Elaborative learning improves long-term retention')
            result=research_operations.ResearchOrchestrator(store,limited).run(op['operation_id'])
            self.assertEqual(result['status'],'completed_with_limits')
            self.assertEqual(len(result['result']['budget_receipts']),3)
            self.assertIn('budget_rejected',result['result']['budget_receipts'][1]['stopped_reason'])

    def test_interrupted_frontend_worker_reclaims_engine_checkpoints(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'case';folder.mkdir()
            library.save(folder/'claims.json',[{'id':'claim','claim':'A synthetic claim','status':'UNSUPPORTED'}])
            store=research_operations.store(root)
            op=store.create('case','claim','A synthetic claim')
            store.update(op['operation_id'],status='running',stage='locator')
            frontend_dir=root/'.project-intelligence'/'operations';frontend_dir.mkdir(parents=True)
            (frontend_dir/(op['operation_id']+'.json')).write_text(json.dumps({
                'status':'running','stage':'Preparando investigación automática'}),encoding='utf-8')
            with patch.object(library,'case_path',return_value=folder):
                finished=research_operations.run_claim_research(root,'case','claim',
                    operation_id=op['operation_id'],provider=FakeProvider())
            self.assertEqual(finished['status'],'completed_with_limits')
            self.assertEqual(finished['operation_id'],op['operation_id'])

    def test_failed_agent_does_not_replace_existing_claim_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'case';folder.mkdir()
            original={'id':'claim','claim':'A synthetic claim','status':'UNSUPPORTED',
                      'research_summary':{'summary':'Conserved result'},
                      'automatic_research_history':[{'outcome':'completed_with_limits'}]}
            library.save(folder/'claims.json',[original])
            def broken(_call):
                raise ValueError('provider failed')
            with patch.object(library,'case_path',return_value=folder):
                finished=research_operations.run_claim_research(root,'case','claim',provider=broken)
            saved=library.read(folder/'claims.json',[])[0]
            self.assertEqual(finished['status'],'failed')
            self.assertEqual(saved['research_summary'],original['research_summary'])
            self.assertEqual(saved['automatic_research_history'],original['automatic_research_history'])

    def test_page_identity_aliases_do_not_spend_budget_twice(self):
        ledger=research_operations.BudgetLedger(0,clock=lambda:0);ledger.begin_round(research_operations.ROUNDS[0])
        first=ledger.observe({'type':'page','url':'https://example.org/paper','doi':'10.1/test'})
        second=ledger.observe({'type':'page','final_url':'https://publisher.example/test','doi':'https://doi.org/10.1/test'})
        self.assertFalse(first['reused']);self.assertTrue(second['reused']);self.assertEqual(ledger.page_count,1)

    def test_frontend_coalesces_double_click_operations(self):
        with tempfile.TemporaryDirectory() as temp:
            old=frontend.INTEL
            try:
                frontend.INTEL=Path(temp)
                first,created=frontend.operation_start('technical_check','case','claim')
                second,created_again=frontend.operation_start('technical_check','case','claim')
                self.assertTrue(created);self.assertFalse(created_again)
                self.assertEqual(first['id'],second['id'])
            finally:frontend.INTEL=old

    def test_three_rounds_finish_with_explicit_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            op=store.create('case','claim','Elaborative learning improves long-term retention')
            result=research_operations.ResearchOrchestrator(store,FakeProvider()).run(op['operation_id'])
            self.assertEqual(result['status'],'completed_with_limits')
            self.assertEqual(result['result']['bounded_resolution']['status'],'excluded_with_limit')
            self.assertEqual(len(result['result']['budget_receipts']),3)
            self.assertEqual(result['result']['historical_verdict_changed'],False)

    def test_direct_support_stops_early(self):
        provider=FakeProvider('sufficient_support')
        def supported(call):
            value=provider(call)
            if call.role=='skeptic':value={**value,'verdict':'VERIFIED','support_source_ids':['s1']}
            return value
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops');op=store.create('c','x','claim')
            result=research_operations.ResearchOrchestrator(store,supported).run(op['operation_id'])
            self.assertEqual(result['status'],'resolved')
            self.assertEqual(len(result['result']['budget_receipts']),1)

    def test_retriever_without_passage_is_rejected(self):
        with self.assertRaises(research_agents.AgentOutputError):
            research_agents.validate_agent_output('retriever',{'sources':[{'source_id':'s','passages':[]}]})

    def test_temporal_mismatch_cannot_be_direct_contradiction_fixture(self):
        matrix={'source_id':'pmc6449625','evidence_id':'passage','dimensions':
                {k:('mismatch' if k=='horizon' else 'supports') for k in research_agents.DIMENSIONS},
                'overall_relation':'mismatch','basis':'The horizon is not reported.'}
        checked=research_agents.validate_agent_output('relevance_evaluator',{'matrix':[matrix]})
        self.assertEqual(checked['matrix'][0]['dimensions']['horizon'],'mismatch')
        text='Immediate measurement; four minutes were allowed to answer the retention question.'
        self.assertNotIn('four minutes after',text.casefold())
        sources={'sources':[{'passages':[{'excerpt':text}]}]}
        with self.assertRaisesRegex(research_agents.AgentOutputError,'tiempo para responder'):
            research_operations.ResearchOrchestrator._guard_temporal_wording(
                sources,{'explanation':'Measured four minutes after studying.'})

    def test_source_evaluator_requires_separate_statuses_and_bases(self):
        with self.assertRaisesRegex(research_agents.AgentOutputError,'independence_status'):
            research_agents.validate_agent_output('source_evaluator',{'assessments':[{
                'source_id':'s','identity_status':'confirmed','credibility_status':'credible',
                'credibility_basis':'supplied metadata','primary_status':'declared_primary',
                'primary_basis':'provider annotation','independence_status':'confirmed_independent',
                'independence_basis':'model inference only','access':'available'}]})

    def test_support_and_contradiction_require_audited_passage_relation(self):
        dimensions={key:'supports' for key in research_agents.DIMENSIONS}
        relevance={'matrix':[{'source_id':'s','evidence_id':'e','dimensions':dimensions,
                              'overall_relation':'mismatch','basis':'Wrong horizon'}]}
        with self.assertRaisesRegex(research_agents.AgentOutputError,'pasaje auditado'):
            research_operations.ResearchOrchestrator._enforce_audit(
                {'decision':'sufficient_support'},{'verdict':'VERIFIED','support_source_ids':['s']},relevance)
        relevance['matrix'][0]['dimensions']['horizon']='mismatch'
        with self.assertRaisesRegex(research_agents.AgentOutputError,'contradicción exige'):
            research_operations.ResearchOrchestrator._enforce_audit(
                {'decision':'direct_contradiction'},{'verdict':'CONTRADICTED','support_source_ids':[]},relevance)


if __name__=='__main__':unittest.main()
