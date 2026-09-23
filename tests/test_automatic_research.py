import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import research_agents
import research_operations
import source_identity
import frontend
import library


class FakeProvider:
    def __init__(self,decision='continue'):
        self.decision=decision;self.round=0;self.calls=[]
    def __call__(self,call):
        self.calls.append(call);r=call.role
        if r=='planner':
            targets=[{'dimension_ids':[k],'query':f'{k} claim study','purpose':purpose}
                     for k in research_agents.DIMENSIONS for purpose in ('support','contradiction')]
            return {'matrix':{k:('long-term' if k=='horizon' else k) for k in research_agents.DIMENSIONS},
                    'gaps':['delayed measure'],'competing_hypotheses':['H1','H0'],
                    'falsification_criteria':['direct null result at delayed follow-up'],'retrieval_targets':targets}
        if r=='formulation_reviewer':return {'compound':True,'subquestions':[{'id':'sub-1','claim':'Delayed retention','dimension_ids':['horizon'],'within_scope':True}]}
        if r=='locator':
            self.round+=1;targets=call.payload.get('retrieval_targets') or [{'dimension_ids':['horizon'],'purpose':'support','query':'delayed'}]
            return {'candidates':[{**target,'doi':f'10.1/{self.round}-{i}'} for i,target in enumerate(targets)],
                    'usage_events':[{'type':'query','query':target['query']} for target in targets]}
        if r=='retriever':
            candidates=call.payload['candidates']['candidates'];sources=[{'source_id':f's{self.round}-{i}','url':f'https://example.org/{self.round}-{i}','passages':[{'evidence_id':f'e{self.round}-{i}','excerpt':'Immediate test only.','page':1}]} for i,_ in enumerate(candidates)]
            return {'sources':sources,'usage_events':[{'type':'page','url':row['url']} for row in sources]}
        if r=='source_evaluator':return {'assessments':[{'source_id':f's{self.round}-{i}','identity_status':'confirmed','credibility_status':'credible','credibility_basis':'peer reviewed source','primary_status':'confirmed_primary','primary_basis':'original study','independence_status':'not_established','independence_basis':'no duplicate signal is not proof','access':'available'} for i in range(len(call.payload['sources']['sources']))]}
        if r=='relevance_evaluator':
            relation='supports' if self.decision=='sufficient_support' else 'mismatch'
            return {'matrix':[{'source_id':f's{self.round}-{i}','evidence_id':f'e{self.round}-{i}','dimensions':{k:('supports' if self.decision=='sufficient_support' else ('mismatch' if k=='horizon' else 'supports')) for k in research_agents.DIMENSIONS},'overall_relation':relation,'basis':'Exact claim-passage audit'} for i in range(len(call.payload['sources']['sources']))]}
        if r=='skeptic':return {'verdict':'VERIFIED' if self.decision=='sufficient_support' else 'UNSUPPORTED','rationale':'Immediate measurement does not establish long-term retention.','contradiction_search':'Explicit target queries were examined; none yielded a directly audited contradiction.','support_source_ids':[row['source_id'] for row in call.payload['support_matrix']['matrix'] if row['overall_relation']=='supports']}
        if r=='final_auditor':return {'decision':'exhausted' if self.round==3 else self.decision,'explanation':'Temporal horizon remains unreported.','errors':[],
             'unresolved_dimensions':([] if self.decision=='sufficient_support' else ['horizon']),
             'indeterminacy_criteria':['bounded_search_complete','unresolved_dimensions_targeted','all_supplied_inputs_considered']}
        if r=='writer':return {'summary':'No se pudo confirmar la afirmación completa.','what_found':'Estudios inmediatos.','limits':'Falta medición diferida.','unanswered':'Retención a largo plazo.'}
        raise AssertionError(r)


class AutomaticResearchTests(unittest.TestCase):
    def test_documents_only_uses_local_retrieval_without_locator_or_web_retriever(self):
        provider=FakeProvider()
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'.project-intelligence/claim-research')
            op=store.create('case','claim','A synthetic claim',evidence_mode='documents_only',document_ids=['doc-id'])
            local={'sources':[{'source_id':'s0-0','document_id':'doc-id','title':'Local PDF','passages':[
                {'evidence_id':'e0-0','excerpt':'A synthetic passage with a physical page reference.','page':1}]}]}
            with patch.object(research_operations.ResearchOrchestrator,'_local_sources',return_value=local):
                result=research_operations.ResearchOrchestrator(store,provider).run(op['operation_id'])
            self.assertEqual(result['status'],'completed_with_limits')
            self.assertNotIn('locator',[call.role for call in provider.calls])
            self.assertNotIn('retriever',[call.role for call in provider.calls])
            self.assertEqual(result['result']['scientific_resolution']['evidence_mode'],'documents_only')

    def test_operation_modes_are_validated_and_fingerprinted(self):
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            with self.assertRaises(ValueError):store.create('case','claim','claim',evidence_mode='unknown')
            with self.assertRaises(ValueError):store.create('case','claim','claim',evidence_mode='documents_only')
            first=store.create('case','claim','claim',evidence_mode='documents_only',document_ids=['doc-a'])
            second=store.create('case','claim','claim',evidence_mode='documents_plus_search',document_ids=['doc-a'])
            self.assertNotEqual(first['input_fingerprint'],second['input_fingerprint'])

    def test_shared_source_flags_other_conclusions_without_revising_them(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'case';folder.mkdir()
            other={'id':'other','claim':'Another claim','status':'VERIFIED',
                   'evidence':[{'type':'external','url':'https://example.org/study','doi':'10.1234/study'}]}
            library.save(folder/'claims.json',[{'id':'current','claim':'Current','status':'UNSUPPORTED'},other])
            with patch.object(library,'case_path',return_value=folder):
                affected=research_operations._affected_conclusions(temp,'case','current',[{'matrix':[{
                    'source_id':'new-source','source_url':'https://example.org/study',
                    'source_doi':'10.1234/study','dimensions':{}}]}])
            self.assertEqual([row['claim_id'] for row in affected],['other'])
            self.assertEqual(library.read(folder/'claims.json')[1]['status'],'VERIFIED')

    def test_scientific_resolution_distinguishes_support_refutation_and_indeterminacy(self):
        plan={'matrix':{key:key for key in research_agents.DIMENSIONS},'retrieval_targets':[]}
        formulation={'claim':'A composed claim','claim_id':'claim','plan':plan}
        rows=[{'source_id':'primary','evidence_id':key,'source_status':'confirmed_primary',
               'dimensions':{dim:('mismatch' if dim=='horizon' else 'supports') for dim in research_agents.DIMENSIONS},
               'overall_relation':'mismatch','basis':'Dimension-level audit'} for key in ('p1','p2')]
        audit={'decision':'exhausted','explanation':'Delayed horizon remains unreported.',
               'unresolved_dimensions':['horizon'],'indeterminacy_criteria':['bounded_search_complete',
               'unresolved_dimensions_targeted','all_supplied_inputs_considered']}
        skeptic={'verdict':'UNSUPPORTED'}
        receipts=[{'round':n,'target_dimensions':['horizon'],'target_purposes':['support','contradiction']}
                  for n in (1,2,3)]
        result=__import__('research_closure').scientific_resolution(formulation,[{'matrix':rows}],audit,skeptic,
            receipts,documents_considered=True)
        self.assertEqual(result['resolution'],'indeterminate')
        self.assertNotEqual(result['dimensions']['horizon']['state'],'contradicted')
        unsupported=__import__('research_closure').scientific_resolution(formulation,[{'matrix':rows}],audit,skeptic,
            receipts[:1],documents_considered=True)
        self.assertEqual(unsupported['resolution'],'unresolved')
        contradiction={**audit,'decision':'direct_contradiction'}
        direct=__import__('research_closure').scientific_resolution(formulation,[{'matrix':[{
            **rows[0],'dimensions':{**rows[0]['dimensions'],'horizon':'contradicts'},'overall_relation':'contradicts'}]}],
            contradiction,{'verdict':'CONTRADICTED'},receipts[:1],documents_considered=True)
        self.assertEqual(direct['resolution'],'refuted')

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
            if call.role=='skeptic':value={**value,'verdict':'VERIFIED','support_source_ids':[row['source_id'] for row in call.payload['support_matrix']['matrix'] if row['overall_relation']=='supports']}
            return value
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops');op=store.create('c','x','claim')
            result=research_operations.ResearchOrchestrator(store,supported).run(op['operation_id'])
            self.assertEqual(result['status'],'resolved')
            self.assertGreaterEqual(len(result['result']['budget_receipts']),2)

    def test_retriever_without_passage_is_rejected(self):
        with self.assertRaises(research_agents.AgentOutputError):
            research_agents.validate_agent_output('retriever',{'sources':[{'source_id':'s','passages':[]}]})

    def test_retriever_canonical_passage_list_is_preserved(self):
        source={'source_id':'stable-source','dimension_ids':['outcome'],'purpose':'support',
                'passages':[{'evidence_id':'ev-1','excerpt':'Literal text','page':3}]}
        original={'sources':[source]}
        normalized=research_operations._normalize_retriever_passages(original)
        self.assertIs(normalized['sources'][0],source)
        self.assertEqual(normalized['sources'][0],source)
        checked=research_agents.validate_agent_output('retriever',normalized)
        self.assertEqual(checked['sources'][0]['passages'],source['passages'])
        self.assertNotIn('passage_structure_origin',checked['sources'][0])

    def test_retriever_normalizes_observed_flat_single_passage_without_changing_evidence(self):
        source={'source_id':'stable-source','evidence_id':'ev-1','passage':'Literal source text',
                'location':'Abstract','url':'https://example.org/paper','dimension_ids':['outcome'],
                'purpose':'support','candidate_ref':'candidate-1'}
        normalized=research_operations._normalize_retriever_passages({'sources':[source]})
        item=normalized['sources'][0]
        self.assertEqual(item['passages'],[{'evidence_id':'ev-1','excerpt':'Literal source text',
                                            'location':'Abstract'}])
        self.assertEqual(item['dimension_ids'],['outcome'])
        self.assertEqual(item['purpose'],'support')
        self.assertEqual(item['candidate_ref'],'candidate-1')
        self.assertEqual(item['passage_structure_origin'],'wrapper_flat_single_passage')
        self.assertEqual(item['passage_structure_policy'],'retriever-passage-normalization-v1')
        checked=research_agents.validate_agent_output('retriever',normalized)
        self.assertEqual(checked['sources'][0]['passages'][0]['evidence_id'],'ev-1')

    def test_retriever_rejects_every_explicit_non_list_passages_shape(self):
        valid={'evidence_id':'ev-1','excerpt':'Literal text','location':'Abstract'}
        invalid_values=(None,'Literal text',valid,{},0,False)
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(research_agents.AgentOutputError,
                        r'no devolvió una lista estructurada.*sources\[0\]\.passages debe ser una lista'):
                    research_operations._normalize_retriever_passages(
                        {'sources':[{'source_id':'s','passages':value,
                                     'evidence_id':'ev-1','passage':'Literal text','location':'Abstract'}]})

    def test_retriever_rejects_empty_passages_list(self):
        result={'sources':[{'source_id':'s','passages':[]}]}
        self.assertEqual(research_operations._normalize_retriever_passages(result),result)
        with self.assertRaisesRegex(research_agents.AgentOutputError,'necesita al menos un pasaje'):
            research_agents.validate_agent_output('retriever',result)

    def test_retriever_rejects_ambiguous_flattened_passage_text(self):
        with self.assertRaisesRegex(research_agents.AgentOutputError,'passage y excerpt diferentes'):
            research_operations._normalize_retriever_passages({'sources':[{
                'source_id':'s','evidence_id':'ev-1','passage':'One literal','excerpt':'Different literal',
                'location':'Abstract'}]})

    def test_retriever_rejects_flattened_passage_missing_required_evidence_fields(self):
        incomplete=(
            {'source_id':'s','passage':'Literal text','location':'Abstract'},
            {'source_id':'s','evidence_id':'ev-1','location':'Abstract'},
            {'source_id':'s','evidence_id':'ev-1','passage':'Literal text'},
        )
        for source in incomplete:
            with self.subTest(source=source):
                with self.assertRaisesRegex(research_agents.AgentOutputError,
                        'no conserva un pasaje con estructura inequívoca'):
                    research_operations._normalize_retriever_passages({'sources':[source]})

    def test_retriever_flattened_shape_stays_raw_and_downstream_gets_canonical_list(self):
        observed={'source_id':'source-1','url':'https://example.org/paper','evidence_id':'ev-1',
                  'passage':'Literal text from the provider','location':'Abstract',
                  'dimension_ids':['outcome'],'purpose':'support'}
        downstream={}
        def provider(call):
            if call.role=='retriever':
                return {'sources':[dict(observed)],'usage_events':[{'type':'page','url':observed['url']}]}
            downstream[call.role]=call.payload['sources']['sources']
            if call.role=='source_evaluator':
                return {'assessments':[{'source_id':'source-1','identity_status':'confirmed',
                    'credibility_status':'credible','credibility_basis':'fixture',
                    'primary_status':'declared_primary','primary_basis':'fixture',
                    'independence_status':'not_established','independence_basis':'fixture','access':'available'}]}
            if call.role=='relevance_evaluator':
                return {'matrix':[{'source_id':'source-1','evidence_id':'ev-1',
                    'dimensions':{key:'unreported' for key in research_agents.DIMENSIONS},
                    'overall_relation':'unreported','basis':'fixture'}]}
            raise AssertionError(call.role)
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            operation=store.create('case','claim','A synthetic claim')
            engine=research_operations.ResearchOrchestrator(store,provider)
            profile=research_operations.ROUNDS[0]
            budget=research_operations.BudgetLedger(0,clock=lambda:0);budget.begin_round(profile)
            retrieved=engine._call(operation,'retriever',{'candidates':{'candidates':[]}},budget,profile)
            self.assertEqual(retrieved['sources'][0]['passages'][0]['excerpt'],observed['passage'])
            raw_file=next((store.folder(operation['operation_id'])/'artifacts'/'raw-agent-output').glob('*.json'))
            raw=json.loads(raw_file.read_text(encoding='utf-8'))
            raw_source=raw['value']['result']['sources'][0]
            self.assertEqual(raw_source,observed)
            self.assertNotIn('passages',raw_source)
            self.assertEqual(raw['value']['result']['usage_events'],
                             [{'type':'page','url':observed['url']}])
            self.assertFalse(raw['canonical'])
            engine._call(operation,'source_evaluator',{'sources':retrieved},budget,profile)
            engine._call(operation,'relevance_evaluator',{'sources':retrieved},budget,profile)
            for rows in downstream.values():
                self.assertIsInstance(rows[0]['passages'],list)
                self.assertEqual(rows[0]['passages'][0]['evidence_id'],'ev-1')

    def test_retriever_structural_failure_retry_preserves_raw_and_budget(self):
        attempts={'count':0};url='https://example.org/flat-paper'
        def provider(_call):
            attempts['count']+=1
            result={'sources':[{'source_id':'source-1','url':url,'evidence_id':'ev-1',
                               'passage':'Literal text','location':'Abstract'}],
                    'usage_events':[{'type':'page','url':url}]}
            if attempts['count']==1:
                result['sources'][0]['passages']=None
            return result
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            operation=store.create('case','claim','A synthetic claim')
            engine=research_operations.ResearchOrchestrator(store,provider)
            profile=research_operations.ROUNDS[0]
            first_budget=research_operations.BudgetLedger(0,clock=lambda:0);first_budget.begin_round(profile)
            with self.assertRaisesRegex(research_agents.AgentOutputError,r'sources\[0\]\.passages debe ser una lista'):
                engine._call(operation,'retriever',{'candidates':{'candidates':[]}},first_budget,profile)
            artifacts=store.folder(operation['operation_id'])/'artifacts'
            failed_raw=json.loads(next((artifacts/'raw-agent-output').glob('*.json')).read_text(encoding='utf-8'))
            self.assertFalse(failed_raw['canonical'])
            self.assertIsNone(failed_raw['value']['result']['sources'][0]['passages'])
            self.assertEqual(list((artifacts/'agent-results').glob('*.json')),[])
            retry_budget=research_operations.BudgetLedger(0,clock=lambda:0);retry_budget.begin_round(profile)
            retried=engine._call(operation,'retriever',{'candidates':{'candidates':[]}},retry_budget,profile)
            self.assertEqual(attempts['count'],2)
            self.assertEqual(retried['sources'][0]['passages'][0]['excerpt'],'Literal text')
            self.assertEqual(retry_budget.page_count,1)
            canonical=list((artifacts/'agent-results').glob('*.json'))
            self.assertEqual(len(canonical),1)
            saved=json.loads(canonical[0].read_text(encoding='utf-8'))
            self.assertTrue(saved['canonical'])
            self.assertEqual(saved['value']['result']['sources'][0]['passages'][0]['evidence_id'],'ev-1')

    def test_retriever_keeps_supplied_nonempty_source_id(self):
        normalized=research_operations._normalize_retriever_identity(
            {'sources':[{'source_id':'catalog-id','title':'Only a label','passages':[]}]},[])
        checked=research_agents.validate_agent_output('retriever',{
            'sources':[{'source_id':normalized['sources'][0]['source_id'],
                        'passages':[{'evidence_id':'e','excerpt':'Exact passage','page':1}],
                        'source_identity_origin':normalized['sources'][0]['source_identity_origin']}]})
        self.assertEqual(checked['sources'][0]['source_id'],'catalog-id')
        self.assertEqual(normalized['sources'][0]['source_identity_origin'],'supplied')

    def test_retriever_normalizes_stable_web_identities_and_preserves_provenance(self):
        cases=(
            ('https://doi.org/10.5555/sample',{'doi':'10.5555/sample'}),
            ('https://pubmed.ncbi.nlm.nih.gov/12345/',{'pmid':'12345'}),
            ('https://example.org/paper?utm_source=one',{}),
        )
        for url,metadata in cases:
            with self.subTest(url=url):
                candidate={'url':url,**metadata}
                source={'source_id':'', 'url':url,**metadata,'passages':[
                    {'evidence_id':'passage','excerpt':'Exact passage','page':2}]}
                first=research_operations._normalize_retriever_identity(
                    {'sources':[source]},[candidate])['sources'][0]
                second=research_operations._normalize_retriever_identity(
                    {'sources':[{'source_id':'', 'url':url.replace('one','two'),**metadata,
                                 'passages':[{'evidence_id':'passage-2','excerpt':'Other exact passage','page':3}]}]},
                    [{'url':url.replace('one','two'),**metadata}])['sources'][0]
                self.assertEqual(first['source_id'],second['source_id'])
                self.assertEqual(first['source_identity_origin'],'wrapper_existing_policy')
                self.assertEqual(first['source_identity_policy'],source_identity.POLICY)
                self.assertEqual(first['source_identity_key'],first['source_id'] and
                                 source_identity.identify({'type':'external','url':url})['identity_key'])
                self.assertTrue(first['source_identity_signals'])
                checked=research_agents.validate_agent_output('retriever',{'sources':[first]})
                self.assertEqual(checked['sources'][0]['source_id'],first['source_id'])

    def test_retriever_normalizes_only_authorized_local_document_identity(self):
        source={'document_id':'doc-authorized','document_sha256':'doc-authorized','source_id':'',
                'passages':[{'evidence_id':'p1','excerpt':'Local exact passage','page':4}]}
        normalized=research_operations._normalize_retriever_identity(
            {'sources':[source]},[],['doc-authorized'])['sources'][0]
        self.assertEqual(normalized['source_id'],'doc-authorized')
        self.assertEqual(normalized['source_identity_basis'],'authorized_document_id')
        checked=research_agents.validate_agent_output('retriever',{'sources':[normalized]})
        self.assertEqual(checked['sources'][0]['source_id'],'doc-authorized')
        with self.assertRaisesRegex(research_agents.AgentOutputError,'identidad utilizable'):
            research_operations._normalize_retriever_identity({'sources':[source]},[],[])

    def test_retriever_rejects_source_without_any_recoverable_identity(self):
        source={'source_id':'','title':'Untrusted title','passages':[
            {'evidence_id':'e','excerpt':'A passage is not an identity','page':1}]}
        with self.assertRaisesRegex(research_agents.AgentOutputError,
                'no tenía identidad utilizable; la ejecución se detuvo para no perder trazabilidad'):
            research_operations._normalize_retriever_identity({'sources':[source]},[])
        with self.assertRaisesRegex(research_agents.AgentOutputError,'source_id debe contener texto'):
            research_agents.validate_agent_output('retriever',{'sources':[source]})

    def test_duplicate_references_share_one_stable_id_and_downstream_receives_it(self):
        stable_url='https://doi.org/10.5555/same-work'
        candidate={'url':stable_url,'doi':'10.5555/same-work'}
        seen={}
        def provider(call):
            if call.role=='retriever':
                return {'sources':[{'source_id':'','url':stable_url,'doi':'10.5555/same-work',
                    'passages':[{'evidence_id':'p1','excerpt':'Passage one','page':1}]},
                    {'source_id':'','url':'https://doi.org/10.5555/same-work?utm_source=mirror',
                     'doi':'10.5555/same-work','passages':[{'evidence_id':'p2','excerpt':'Passage two','page':2}]}],
                    'usage_events':[{'type':'page','url':stable_url}]}
            sources=call.payload.get('sources',{}).get('sources',[])
            ids=[row['source_id'] for row in sources]
            seen[call.role]=ids
            if call.role=='source_evaluator':
                return {'assessments':[{'source_id':row['source_id'],'identity_status':'uncertain',
                    'credibility_status':'uncertain','credibility_basis':'synthetic fixture',
                    'primary_status':'uncertain','primary_basis':'synthetic fixture',
                    'independence_status':'not_established','independence_basis':'synthetic fixture',
                    'access':'available'} for row in sources]}
            if call.role=='relevance_evaluator':
                return {'matrix':[{'source_id':row['source_id'],'evidence_id':passage['evidence_id'],
                    'dimensions':{key:'unreported' for key in research_agents.DIMENSIONS},
                    'overall_relation':'unreported','basis':'synthetic fixture'}
                    for row in sources for passage in row['passages']]}
            raise AssertionError(call.role)
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            operation=store.create('case','claim','A synthetic claim')
            engine=research_operations.ResearchOrchestrator(store,provider)
            budget=research_operations.BudgetLedger(0,clock=lambda:0)
            budget.begin_round(research_operations.ROUNDS[0])
            retriever=engine._call(operation,'retriever',{'candidates':{'candidates':[candidate]}},
                                   budget,research_operations.ROUNDS[0])
            stable_ids=[row['source_id'] for row in retriever['sources']]
            self.assertEqual(stable_ids[0],stable_ids[1])
            self.assertIn('source:'+stable_ids[0],budget.pages)
            self.assertEqual(budget.page_count,1)
            assessment=engine._call(operation,'source_evaluator',{'sources':retriever},budget,
                                    research_operations.ROUNDS[0])
            relevance=engine._call(operation,'relevance_evaluator',
                {'sources':retriever,'assessments':assessment},budget,research_operations.ROUNDS[0])
            self.assertEqual(seen['source_evaluator'],stable_ids)
            self.assertEqual(seen['relevance_evaluator'],stable_ids)
            self.assertEqual({row['source_id'] for row in assessment['assessments']},set(stable_ids))
            self.assertEqual({row['source_id'] for row in relevance['matrix']},set(stable_ids))

    def test_failed_identity_attempt_is_noncanonical_and_retry_reuses_page_budget(self):
        attempt={'number':0}
        url='https://example.org/retrieved-paper'
        def provider(call):
            attempt['number']+=1
            if attempt['number']==1:
                source={'source_id':'','title':'Paper','passages':[
                    {'evidence_id':'e1','excerpt':'Text','page':1}]}
                candidates=[]
            else:
                source={'source_id':'','url':url,'passages':[
                    {'evidence_id':'e1','excerpt':'Text','page':1}]}
                candidates=[{'url':url}]
            return {'sources':[source],'usage_events':[{'type':'page','url':url}]}
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            operation=store.create('case','claim','A synthetic claim')
            engine=research_operations.ResearchOrchestrator(store,provider)
            budget=research_operations.BudgetLedger(0,clock=lambda:0)
            budget.begin_round(research_operations.ROUNDS[0])
            with self.assertRaisesRegex(research_agents.AgentOutputError,'identidad utilizable'):
                engine._call(operation,'retriever',{'candidates':{'candidates':[]}},budget,
                             research_operations.ROUNDS[0])
            artifacts=store.folder(operation['operation_id'])/'artifacts'
            self.assertEqual(len(list((artifacts/'agent-results').glob('*.json'))),0)
            invalid_raw=json.loads(next((artifacts/'raw-agent-output').glob('*.json')).read_text(encoding='utf-8'))
            self.assertFalse(invalid_raw['canonical'])
            self.assertEqual(invalid_raw['value']['result']['sources'][0]['source_id'],'')
            retry_budget=research_operations.BudgetLedger(0,clock=lambda:0)
            retry_budget.begin_round(research_operations.ROUNDS[0])
            retried=engine._call(operation,'retriever',{'candidates':{'candidates':[{'url':url}]}},retry_budget,
                                 research_operations.ROUNDS[0])
            self.assertTrue(retried['sources'][0]['source_id'])
            self.assertEqual(retry_budget.page_count,1)
            self.assertEqual(len(list((artifacts/'retry-usage-replay').glob('*.json'))),1)
            canonical=list((artifacts/'agent-results').glob('*.json'))
            self.assertEqual(len(canonical),1)
            envelope=json.loads(canonical[0].read_text(encoding='utf-8'))
            self.assertTrue(envelope['canonical'])
            self.assertEqual(envelope['value']['usage_events'][0]['source_id'],retried['sources'][0]['source_id'])

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
