import tempfile
import unittest
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import research_agents
import research_operations
import source_identity
import pipeline
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
    @staticmethod
    def _planner_result(*, missing_contradictions=(), empty_dimensions=()):
        matrix={key:("" if key in empty_dimensions else f"declared {key}")
                for key in research_agents.DIMENSIONS}
        targets=[{"dimension_ids":[key for key in research_agents.DIMENSIONS
                                  if key not in missing_contradictions and key not in empty_dimensions],
                  "query":"Search directly for evidence against the declared dimensions.",
                  "purpose":"contradiction"}]
        targets=[row for row in targets if row["dimension_ids"]]
        targets.append({"dimension_ids":[key for key in research_agents.DIMENSIONS if key not in empty_dimensions],
                        "query":"Search for primary evidence supporting the stated dimensions.",
                        "purpose":"support"})
        return {"matrix":matrix,"gaps":[],"competing_hypotheses":["H1","H0"],
                "falsification_criteria":["Direct contradictory result"],"retrieval_targets":targets}

    def test_planner_requires_explicit_contradiction_coverage_only_for_declared_dimensions(self):
        valid=self._planner_result()
        self.assertEqual(research_agents.validate_agent_output('planner',valid),valid)

        with self.assertRaises(research_agents.PlannerContradictionCoverageError) as raised:
            research_agents.validate_agent_output(
                'planner',self._planner_result(missing_contradictions={'population'}))
        self.assertEqual(raised.exception.missing_dimensions,('population',))

        empty=self._planner_result(empty_dimensions={'population'})
        # The only contradiction target excludes the empty dimension.
        self.assertNotIn('population',empty['retrieval_targets'][0]['dimension_ids'])
        self.assertEqual(research_agents.validate_agent_output('planner',empty),empty)

    def test_planner_support_and_identity_recovery_do_not_satisfy_contradiction_coverage(self):
        result=self._planner_result(missing_contradictions={'population'})
        result['retrieval_targets'].append({"dimension_ids":["population"],
            "query":"Recover the identity of an already cited source.","purpose":"identity_recovery"})
        with self.assertRaises(research_agents.PlannerContradictionCoverageError) as raised:
            research_agents.validate_agent_output('planner',result)
        self.assertEqual(raised.exception.missing_dimensions,('population',))

        # One explicit contradiction target can cover every declared dimension.
        multi=self._planner_result()
        contradiction=[row for row in multi['retrieval_targets'] if row['purpose']=='contradiction']
        self.assertEqual(len(contradiction),1)
        self.assertEqual(set(contradiction[0]['dimension_ids']),set(research_agents.DIMENSIONS))
        research_agents.validate_agent_output('planner',multi)

    def test_adaptive_budget_formula_uses_nonempty_dimensions_and_bounded_hypotheses(self):
        cases=((1,0,10,16),(3,0,12,19),(5,0,14,22),(7,0,16,24),
               (1,1,11,18),(1,2,12,20),(5,3,16,24))
        for dimensions,hypotheses,queries,pages in cases:
            with self.subTest(dimensions=dimensions,hypotheses=hypotheses):
                planner=self._planner_result()
                planner['matrix']={key:(f'declared {key}' if index < dimensions else '')
                                   for index,key in enumerate(research_agents.DIMENSIONS)}
                planner['competing_hypotheses']=[f'H{index}' for index in range(hypotheses)]
                plan=research_operations._adaptive_budget_plan(planner,'question_search')
                self.assertEqual(plan['operation_query_cap'],queries)
                self.assertEqual(plan['target_cap'],queries)
                self.assertEqual(plan['operation_page_cap'],pages)
                self.assertLessEqual(plan['operation_query_cap'],research_operations.GLOBAL_QUERY_LIMIT)
                self.assertLessEqual(plan['operation_page_cap'],research_operations.GLOBAL_PAGE_LIMIT)
        sparse=self._planner_result()
        sparse['matrix']={'intervention':'', 'spacing':'   '}
        sparse['competing_hypotheses']=['',None,'  ']
        plan=research_operations._adaptive_budget_plan(sparse,'question_search')
        self.assertEqual(plan['declared_dimensions'],[])
        self.assertEqual(plan['operation_query_cap'],10)
        self.assertEqual(plan['operation_page_cap'],16)
        self.assertEqual(plan['competing_hypotheses_counted'],0)

    def test_adaptive_budget_modes_keep_web_queries_separate_from_local_capacity(self):
        planner=self._planner_result()
        planner['matrix']={key:('x' if index < 3 else '') for index,key in enumerate(research_agents.DIMENSIONS)}
        planner['competing_hypotheses']=[]
        search=research_operations._adaptive_budget_plan(planner,'question_search')
        local=research_operations._adaptive_budget_plan(planner,'documents_only')
        combined=research_operations._adaptive_budget_plan(planner,'documents_plus_search')
        self.assertEqual(search['operation_query_cap'],12)
        self.assertEqual(local['operation_query_cap'],0)
        self.assertEqual(local['target_cap'],12)
        self.assertEqual(local['operation_page_cap'],19)
        self.assertEqual(combined['operation_query_cap'],12)
        self.assertEqual(combined['operation_page_cap'],19)
        self.assertEqual(combined['page_pool'],'shared_local_and_web_unique_pages')

    def test_adaptive_round_grants_redistribute_unused_shared_pool(self):
        planner=self._planner_result()
        planner['matrix']={key:'x' for key in research_agents.DIMENSIONS}
        planner['competing_hypotheses']=[]
        plan=research_operations._adaptive_budget_plan(planner,'question_search')
        ledger=research_operations.BudgetLedger(0,clock=lambda:0)
        ledger.configure(plan)
        ledger.begin_round(research_operations.ROUNDS[0])
        self.assertEqual(ledger.round_grants,{'queries':6,'pages':8,'targets':6})
        for index in range(2):
            ledger.observe({'type':'query','query':f'round one query {index}'})
        for index in range(3):
            ledger.observe({'type':'page','url':f'https://example.org/r1/{index}'})
        for index in range(2):
            ledger.observe_target({'purpose':'support','query':f'target-{index}',
                                  'dimension_ids':['intervention']})
        ledger.begin_round(research_operations.ROUNDS[1])
        self.assertEqual(ledger.round_grants,{'queries':7,'pages':11,'targets':7})
        receipt=ledger.receipt(2,'fixture')
        self.assertEqual(receipt['shared_pool_remaining'],{'queries':14,'pages':21,'targets':14})
        self.assertEqual(receipt['round_grant'],{'queries':7,'pages':11,'targets':7})

        full=research_operations.BudgetLedger(0,clock=lambda:0)
        full.configure(plan)
        observed=[]
        for profile in research_operations.ROUNDS:
            full.begin_round(profile)
            observed.append(full.round_grants['queries'])
            for index in range(full.round_grants['queries']):
                full.observe({'type':'query','query':f'{profile["name"]}-{index}'})
        self.assertEqual(observed,[6,5,5])
        self.assertEqual(len(full.queries),16)
        with self.assertRaises(research_operations.BudgetExceeded):
            full.observe({'type':'query','query':'seventeenth unique query'})

    def test_adaptive_targets_round_robin_without_rewriting_target_semantics(self):
        targets=[{'purpose':'support','query':'S1','dimension_ids':['intervention']},
                 {'purpose':'support','query':'S2','dimension_ids':['spacing']},
                 {'purpose':'contradiction','query':'C1','dimension_ids':['outcome']},
                 {'purpose':'identity_recovery','query':'I1','dimension_ids':['population']},
                 {'purpose':'contradiction','query':'C2','dimension_ids':['horizon']}]
        selected=research_operations._round_robin_targets(targets,4)
        self.assertEqual([row['query'] for row in selected],['S1','C1','I1','S2'])
        self.assertEqual(selected[1],targets[2])
        self.assertEqual(selected[2],targets[3])

    def test_adaptive_budget_manifest_and_receipt_explain_policy_and_local_page_consumption(self):
        planner=self._planner_result()
        planner['matrix']={key:('x' if index < 1 else '') for index,key in enumerate(research_agents.DIMENSIONS)}
        planner['competing_hypotheses']=[]
        plan=research_operations._adaptive_budget_plan(planner,'documents_plus_search')
        ledger=research_operations.BudgetLedger(0,clock=lambda:0)
        ledger.configure(plan)
        ledger.begin_round(research_operations.ROUNDS[0])
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            operation=store.create('case','claim','Synthetic claim',evidence_mode='documents_plus_search',
                                   document_ids=['authorized-doc'])
            engine=research_operations.ResearchOrchestrator(store,FakeProvider())
            manifest=engine._manifest(operation,'retriever',research_operations.ROUNDS[0],ledger)
            self.assertEqual(manifest['budget_policy'],research_operations.ADAPTIVE_BUDGET_POLICY)
            self.assertEqual(manifest['budget_plan']['operation_query_cap'],10)
            self.assertEqual(manifest['round_grant'],{'queries':4,'pages':6,'targets':4})
        before=ledger.remaining()['global_queries']
        first=ledger.observe({'type':'page','document_sha256':'doc-sha','page':7,'body_sha256':'passage-a'})
        self.assertFalse(first['reused'])
        self.assertEqual(ledger.remaining()['global_pages'],15)
        self.assertEqual(ledger.remaining()['global_queries'],before)
        duplicate=ledger.observe({'type':'page','document_sha256':'doc-sha','physical_page':7,
                                  'body_sha256':'passage-b'})
        self.assertTrue(duplicate['reused'])
        self.assertEqual(ledger.page_count,1)

    def test_adaptive_budget_plan_is_canonical_idempotent_and_bound_to_valid_planner(self):
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            operation=store.create('case','claim','Synthetic claim')
            engine=research_operations.ResearchOrchestrator(store,FakeProvider())
            planner=self._planner_result()
            planner['matrix']={key:('x' if index < 3 else '') for index,key in enumerate(research_agents.DIMENSIONS)}
            first=engine._persist_budget_plan(operation,planner)
            second=engine._persist_budget_plan(operation,planner)
            self.assertEqual(first,second)
            folder=store.folder(operation['operation_id'])/'artifacts'/'budget-plan'
            files=list(folder.glob('*.json'))
            self.assertEqual(len(files),1)
            saved=json.loads(files[0].read_text(encoding='utf-8'))
            self.assertTrue(saved['canonical'])
            self.assertEqual(saved['value'],first)
            changed=dict(planner)
            changed['matrix']={**planner['matrix'],'horizon':'new declared dimension'}
            with self.assertRaisesRegex(research_agents.AgentOutputError,'no coincide con la entrada validada'):
                engine._persist_budget_plan(operation,changed)
            self.assertEqual(len(list(folder.glob('*.json'))),1)

    def test_planner_coverage_retry_preserves_raw_and_writes_one_checkpoint_for_each_evidence_mode(self):
        valid=self._planner_result()
        invalid=self._planner_result(missing_contradictions={'population'})
        for mode,document_ids in (
                ('question_search',[]),('documents_only',['doc-authorized']),
                ('documents_plus_search',['doc-authorized'])):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                store=research_operations.OperationStore(Path(temp)/'ops')
                operation=store.create('case','claim','Synthetic claim',evidence_mode=mode,
                                       document_ids=document_ids)
                calls=[]
                class PlannerRetryProvider:
                    def __call__(self,call):
                        calls.append(call)
                        result=invalid if len(calls)==1 else valid
                        return {**result,"usage_events":[{"type":"query","query":"one synthetic planner receipt"}]}

                engine=research_operations.ResearchOrchestrator(store,PlannerRetryProvider())
                budget=research_operations.BudgetLedger(0,clock=lambda:0)
                budget.begin_round(research_operations.ROUNDS[0])
                result=engine._call(operation,'planner',{'claim':'Synthetic claim',
                    'evidence_mode':mode,'document_ids':document_ids},budget,None)

                self.assertEqual(len(calls),2)
                self.assertEqual(result['matrix'],valid['matrix'])
                retry=calls[1].payload['planner_retry']
                self.assertEqual(retry['missing_contradiction_dimensions'],['population'])
                self.assertEqual(retry['previous_invalid_output'],invalid)
                self.assertIn('purpose=contradiction',retry['correction'])
                self.assertIn('No conviertas ausencia de evidencia en contradicción.',retry['correction'])
                self.assertEqual(calls[1].manifest['semantic_retry']['attempt'],2)
                self.assertEqual(calls[1].manifest['semantic_retry']['missing_dimensions'],['population'])

                artifacts=store.folder(operation['operation_id'])/'artifacts'
                raw_files=sorted((artifacts/'raw-agent-output').glob('*.json'))
                self.assertEqual(len(raw_files),2)
                first=json.loads(raw_files[0].read_text(encoding='utf-8'))
                second=json.loads(raw_files[1].read_text(encoding='utf-8'))
                self.assertFalse(first['canonical'])
                self.assertEqual(first['value']['result'],{**invalid,"usage_events":[
                    {"type":"query","query":"one synthetic planner receipt"}]})
                self.assertFalse(second['canonical'])
                self.assertEqual(second['value']['result'],{**valid,"usage_events":[
                    {"type":"query","query":"one synthetic planner receipt"}]})
                self.assertEqual(len(budget.queries),1)
                self.assertEqual(budget.page_count,0)
                checkpoints=list((artifacts/'agent-results').glob('*.json'))
                self.assertEqual(len(checkpoints),1)
                checkpoint=json.loads(checkpoints[0].read_text(encoding='utf-8'))
                self.assertTrue(checkpoint['canonical'])
                self.assertEqual(checkpoint['value']['result']['matrix'],valid['matrix'])
                self.assertEqual(len(checkpoint['value']['usage_events']),1)
                self.assertEqual(list((artifacts/'retry-usage-replay').glob('*.json')),[])

                reused=engine._call(operation,'planner',{'claim':'Synthetic claim',
                    'evidence_mode':mode,'document_ids':document_ids},budget,None)
                self.assertEqual(reused['matrix'],valid['matrix'])
                self.assertEqual(len(calls),2)
                self.assertEqual(len(list((artifacts/'agent-results').glob('*.json'))),1)
                self.assertEqual(len(list((artifacts/'checkpoint-reuse').glob('*.json'))),1)
                self.assertEqual(len(budget.queries),1)

    def test_planner_retry_stops_after_second_invalid_coverage_result_without_checkpoint(self):
        invalid=self._planner_result(missing_contradictions={'population'})
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            operation=store.create('case','claim','Synthetic claim')
            calls=[]
            class AlwaysInvalidProvider:
                def __call__(self,call):
                    calls.append(call)
                    return invalid
            engine=research_operations.ResearchOrchestrator(store,AlwaysInvalidProvider())
            with self.assertRaises(research_agents.PlannerContradictionCoverageError) as raised:
                engine._call(operation,'planner',{'claim':'Synthetic claim'},
                             research_operations.BudgetLedger(0,clock=lambda:0),None)
            self.assertEqual(raised.exception.missing_dimensions,('population',))
            self.assertEqual(len(calls),2)
            artifacts=store.folder(operation['operation_id'])/'artifacts'
            self.assertEqual(len(list((artifacts/'raw-agent-output').glob('*.json'))),2)
            self.assertEqual(list((artifacts/'agent-results').glob('*.json')),[])
            self.assertEqual(list((artifacts/'budget-plan').glob('*.json')),[])

    def test_pipeline_provider_promotes_bounded_planner_correction_to_instructions(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            skill=root/'skills/research-planner/SKILL.md'
            skill.parent.mkdir(parents=True)
            skill.write_text('planner skill',encoding='utf-8')
            observed={}
            class FakeRunner:
                run_id='planner-retry-fixture'
                def call(self,stage,instructions,data,agent,budget):
                    observed.update(stage=stage,instructions=instructions,data=data,agent=agent,budget=budget)
                    return [{'matrix':{}}]
            call=research_agents.AgentCall('planner',{'planner_retry':{
                'missing_contradiction_dimensions':['population'],
                'previous_invalid_output':{'matrix':{'population':'adults'}}}},
                {'claim_ids':['claim'],'semantic_retry':{'reason':'missing_contradiction_dimension_coverage',
                 'missing_dimensions':['population']},'budget_remaining':{'seconds':30,
                 'round_queries':0,'round_pages':0}})
            with patch.object(pipeline,'Runner',FakeRunner):
                result=research_operations.PipelineProvider(root)(call)
            self.assertEqual(result['matrix'],{})
            self.assertIn('population',observed['instructions'])
            self.assertIn('purpose=contradiction',observed['instructions'])
            self.assertIn('No conviertas ausencia de evidencia en contradicción.',observed['instructions'])
            self.assertEqual(observed['budget']['allowed_tools'],[])
            self.assertEqual(observed['budget']['max_tool_actions'],0)

    def test_invalid_planner_structure_is_not_given_semantic_coverage_retry(self):
        invalid=self._planner_result(missing_contradictions={'population'})
        invalid.pop('gaps')
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            operation=store.create('case','claim','Synthetic claim')
            calls=[]
            class InvalidStructureProvider:
                def __call__(self,call):
                    calls.append(call)
                    return invalid
            engine=research_operations.ResearchOrchestrator(store,InvalidStructureProvider())
            with self.assertRaisesRegex(research_agents.AgentOutputError,'planner.gaps'):
                engine._call(operation,'planner',{'claim':'Synthetic claim'},
                             research_operations.BudgetLedger(0,clock=lambda:0),None)
            self.assertEqual(len(calls),1)
            artifacts=store.folder(operation['operation_id'])/'artifacts'
            self.assertEqual(len(list((artifacts/'raw-agent-output').glob('*.json'))),1)
            self.assertEqual(list((artifacts/'agent-results').glob('*.json')),[])

    def test_retriever_provider_keeps_tools_narrow_and_supplies_authorized_document_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            skill=root/'skills/research-retriever/SKILL.md'
            skill.parent.mkdir(parents=True)
            skill.write_text((Path(__file__).resolve().parents[1]/'skills/research-retriever/SKILL.md').read_text(encoding='utf-8'),encoding='utf-8')
            observed={}
            class FakeRunner:
                run_id='retriever-fixture'
                def call(self,stage,instructions,data,agent,budget):
                    observed.update(stage=stage,instructions=instructions,data=data,agent=agent,budget=budget)
                    return [{'sources':[{'source_id':'doc:authorized-1','document_id':'authorized-1',
                        'dimension_ids':['outcome'],'purpose':'support','passages':[
                            {'evidence_id':'doc:authorized-1:p1','excerpt':'Literal local passage.', 'page':1}]}]}]

            payload={'authorized_documents':[{'document_id':'authorized-1','page':1,
                      'text':'Literal local passage.'}]}
            call=research_agents.AgentCall('retriever',payload,{
                'claim_ids':['claim-1'],'budget_remaining':{'seconds':120,'round_queries':2,'round_pages':3}})
            with patch.object(pipeline,'Runner',FakeRunner):
                result=research_operations.PipelineProvider(root)(call)
            self.assertEqual(observed['budget']['allowed_tools'],['search_web','read_url_content'])
            self.assertNotIn('view_file',observed['budget']['allowed_tools'])
            self.assertIn('No abras rutas locales',observed['instructions'])
            self.assertIn('brain/<conversation>/.system_generated/steps/<n>/content.md',observed['instructions'])
            self.assertIn('RESTRICCIÓN EXPLÍCITA DEL WRAPPER',observed['instructions'])
            self.assertEqual(observed['data']['payload'],payload)
            self.assertEqual(result['sources'][0]['passages'][0]['excerpt'],'Literal local passage.')

    def _flat_relevance_evaluation(self):
        return {
            'source_id':'doi:10.5093/psed2020a20',
            'evidence_id':'doi:10.5093/psed2020a20:ev1',
            'intervention':'mismatch','spacing':'unreported','comparison':'unreported',
            'population':'unreported','material':'unreported','outcome':'supports',
            'horizon':'unreported','overall_relation':'mismatch',
            'basis':'Observed flat provider evaluation; no semantic values are inferred.',
        }

    def test_relevance_matrix_canonical_list_is_preserved(self):
        row={'source_id':'source-1','evidence_id':'passage-1',
             'dimensions':{key:'unreported' for key in research_agents.DIMENSIONS},
             'overall_relation':'unreported','basis':'Canonical fixture.'}
        original={'matrix':[row]}
        normalized=research_operations._normalize_relevance_matrix(original)
        self.assertEqual(normalized,original)
        self.assertNotIn('matrix_structure_origin',normalized)
        self.assertEqual(research_agents.validate_agent_output('relevance_evaluator',normalized),original)

    def test_relevance_matrix_normalizes_only_observed_flat_evaluations(self):
        evaluation=self._flat_relevance_evaluation()
        raw={'evaluations':[dict(evaluation)],'usage_events':[]}
        normalized=research_operations._normalize_relevance_matrix(raw)
        self.assertNotIn('evaluations',normalized)
        self.assertEqual(normalized['matrix'],[{
            'source_id':evaluation['source_id'],
            'evidence_id':evaluation['evidence_id'],
            'dimensions':{key:evaluation[key] for key in research_agents.DIMENSIONS},
            'overall_relation':evaluation['overall_relation'],
            'basis':evaluation['basis'],
        }])
        self.assertEqual(normalized['matrix_structure_origin'],
                         research_agents.RELEVANCE_MATRIX_STRUCTURE_ORIGIN)
        self.assertEqual(normalized['matrix_structure_policy'],
                         research_agents.RELEVANCE_MATRIX_STRUCTURE_POLICY)
        checked=research_agents.validate_agent_output('relevance_evaluator',normalized)
        self.assertEqual(checked['matrix'],normalized['matrix'])
        self.assertEqual(raw,{'evaluations':[evaluation],'usage_events':[]})

    def test_relevance_matrix_rejects_ambiguous_or_incomplete_shapes(self):
        valid=self._flat_relevance_evaluation()
        malformed_values=(None,'text',17,True,{'row-1':valid},{'source_id':'s'})
        for malformed in malformed_values:
            with self.subTest(matrix=malformed):
                with self.assertRaisesRegex(research_agents.AgentOutputError,
                        'no devolvió una matriz estructurada'):
                    research_operations._normalize_relevance_matrix(
                        {'matrix':malformed,'evaluations':[dict(valid)]})

        missing_dimension=dict(valid);missing_dimension.pop('horizon')
        invalid_dimension=dict(valid);invalid_dimension['horizon']='maybe'
        missing_id=dict(valid);missing_id['source_id']=' '
        missing_evidence=dict(valid);missing_evidence.pop('evidence_id')
        conflicting_nested={**valid,'dimensions':{key:'supports' for key in research_agents.DIMENSIONS}}
        no_rows={'evaluations':[]}
        non_list={'evaluations':valid}
        for malformed in (missing_dimension,invalid_dimension,missing_id,missing_evidence,
                          conflicting_nested):
            with self.subTest(evaluation=malformed):
                with self.assertRaisesRegex(research_agents.AgentOutputError,
                        'no devolvió una matriz estructurada'):
                    research_operations._normalize_relevance_matrix({'evaluations':[malformed]})
        for malformed in (no_rows,non_list,{'unexpected':[]},
                          {'evaluations':[dict(valid,extra_relation='supports')]}):
            with self.subTest(envelope=malformed):
                with self.assertRaises(research_agents.AgentOutputError):
                    research_operations._normalize_relevance_matrix(malformed)

    def test_relevance_validator_rejects_noncanonical_dimensions_and_relations(self):
        base={'source_id':'s','evidence_id':'e',
              'dimensions':{key:'unreported' for key in research_agents.DIMENSIONS},
              'overall_relation':'unreported','basis':'Fixture.'}
        invalid_rows=[]
        missing_dimension=dict(base);missing_dimension['dimensions']=dict(base['dimensions']);missing_dimension['dimensions'].pop('horizon')
        extra_dimension=dict(base);extra_dimension['dimensions']={**base['dimensions'],'other':'unreported'}
        invalid_dimension=dict(base);invalid_dimension['dimensions']={**base['dimensions'],'horizon':'maybe'}
        invalid_dimension_type=dict(base);invalid_dimension_type['dimensions']={**base['dimensions'],'horizon':None}
        invalid_overall=dict(base,overall_relation='maybe')
        missing_overall=dict(base);missing_overall.pop('overall_relation')
        missing_basis=dict(base);missing_basis.pop('basis')
        missing_source=dict(base);missing_source.pop('source_id')
        missing_evidence=dict(base);missing_evidence.pop('evidence_id')
        invalid_rows.extend((missing_dimension,extra_dimension,invalid_dimension,
                             invalid_dimension_type,invalid_overall,missing_overall,
                             missing_basis,missing_source,missing_evidence))
        for row in invalid_rows:
            with self.subTest(row=row):
                with self.assertRaises(research_agents.AgentOutputError):
                    research_agents.validate_agent_output('relevance_evaluator',{'matrix':[row]})
        for provenance in (
                {'matrix_structure_origin':'wrapper_flat_evaluations'},
                {'matrix_structure_origin':None,'matrix_structure_policy':None}):
            with self.subTest(provenance=provenance):
                with self.assertRaisesRegex(research_agents.AgentOutputError,'provenance'):
                    research_agents.validate_agent_output('relevance_evaluator',
                        {'matrix':[base],**provenance})
        with self.assertRaisesRegex(research_agents.AgentOutputError,'procedencia de normalización'):
            research_operations._normalize_relevance_matrix({
                'evaluations':[self._flat_relevance_evaluation()],
                'matrix_structure_policy':research_agents.RELEVANCE_MATRIX_STRUCTURE_POLICY,
                'matrix_structure_origin':research_agents.RELEVANCE_MATRIX_STRUCTURE_ORIGIN,
            })

    def test_relevance_failure_preserves_raw_and_retry_emits_one_canonical_checkpoint(self):
        attempts={'count':0}
        evaluation=self._flat_relevance_evaluation()
        malformed={'matrix':{'ambiguous':'not a row'},'evaluations':[dict(evaluation)],'usage_events':[]}
        valid={'evaluations':[dict(evaluation)],'usage_events':[]}
        downstream={}
        def provider(call):
            if call.role=='relevance_evaluator':
                attempts['count']+=1
                return malformed if attempts['count']==1 else valid
            if call.role in {'skeptic','final_auditor'}:
                downstream[call.role]=call.payload['support_matrix']['matrix']
                if call.role=='skeptic':
                    return {'verdict':'UNSUPPORTED','rationale':'Fixture only.',
                            'contradiction_search':'No provider was used.',
                            'support_source_ids':[]}
                return {'decision':'continue','explanation':'Fixture only.','errors':[],
                        'unresolved_dimensions':[],'indeterminacy_criteria':[]}
            raise AssertionError(call.role)

        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            operation=store.create('case','claim','A synthetic compound claim')
            engine=research_operations.ResearchOrchestrator(store,provider)
            profile=research_operations.ROUNDS[0]
            first_budget=research_operations.BudgetLedger(0,clock=lambda:0)
            first_budget.begin_round(profile)
            first_budget.observe({'type':'query','query':'preexisting query'})
            first_budget.observe({'type':'page','url':'https://example.org/preexisting'})
            before=(set(first_budget.queries),set(first_budget.pages))
            with self.assertRaisesRegex(research_agents.AgentOutputError,
                    'La evaluación de pertinencia no devolvió una matriz estructurada'):
                engine._call(operation,'relevance_evaluator',{'sources':{'sources':[]}},
                             first_budget,profile)
            artifacts=store.folder(operation['operation_id'])/'artifacts'
            raw_files=list((artifacts/'raw-agent-output').glob('*.json'))
            self.assertEqual(len(raw_files),1)
            raw=json.loads(raw_files[0].read_text(encoding='utf-8'))
            self.assertFalse(raw['canonical'])
            self.assertEqual(raw['value']['result'],malformed)
            self.assertEqual((set(first_budget.queries),set(first_budget.pages)),before)
            self.assertEqual(list((artifacts/'agent-results').glob('*.json')),[])

            retry_budget=research_operations.BudgetLedger(0,clock=lambda:0)
            retry_budget.begin_round(profile)
            retry_budget.observe({'type':'query','query':'preexisting query'})
            retry_budget.observe({'type':'page','url':'https://example.org/preexisting'})
            canonical=engine._call(operation,'relevance_evaluator',{'sources':{'sources':[]}},
                                   retry_budget,profile)
            self.assertEqual(attempts['count'],2)
            self.assertEqual(canonical['matrix'][0]['source_id'],evaluation['source_id'])
            self.assertEqual(canonical['matrix'][0]['evidence_id'],evaluation['evidence_id'])
            self.assertEqual((set(retry_budget.queries),set(retry_budget.pages)),before)
            canonical_files=list((artifacts/'agent-results').glob('*.json'))
            self.assertEqual(len(canonical_files),1)
            checkpoint=json.loads(canonical_files[0].read_text(encoding='utf-8'))
            self.assertTrue(checkpoint['canonical'])
            self.assertEqual(checkpoint['value']['result']['matrix'],canonical['matrix'])

            reuse_budget=research_operations.BudgetLedger(0,clock=lambda:0)
            reuse_budget.begin_round(profile)
            reuse_budget.observe({'type':'query','query':'preexisting query'})
            reuse_budget.observe({'type':'page','url':'https://example.org/preexisting'})
            reused=engine._call(operation,'relevance_evaluator',{'sources':{'sources':[]}},
                                reuse_budget,profile)
            self.assertEqual(attempts['count'],2)
            self.assertEqual(reused['matrix'],canonical['matrix'])
            self.assertEqual((set(reuse_budget.queries),set(reuse_budget.pages)),before)
            reuse_files=list((artifacts/'checkpoint-reuse').glob('*.json'))
            self.assertTrue(reuse_files)
            self.assertEqual(len(list((artifacts/'agent-results').glob('*.json'))),1)

            engine._call(operation,'skeptic',{'support_matrix':canonical},retry_budget,profile)
            engine._call(operation,'final_auditor',{'support_matrix':canonical},retry_budget,profile)
            for role in ('skeptic','final_auditor'):
                self.assertIsInstance(downstream[role],list)
                self.assertEqual(downstream[role],canonical['matrix'])

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
            artifacts=store.folder(op['operation_id'])/'artifacts'
            claim_passage=json.loads(next((artifacts/'claim-passage-matrix').glob('*.json')).read_text(encoding='utf-8'))
            rows=claim_passage['value']['matrix']
            self.assertTrue(rows)
            self.assertTrue(all('dimensions' in row for row in rows))
            self.assertTrue(all('evaluations' not in row for row in rows))
            budget_plan=json.loads(next((artifacts/'budget-plan').glob('*.json')).read_text(encoding='utf-8'))
            self.assertTrue(budget_plan['canonical'])
            self.assertEqual(budget_plan['value']['evidence_mode'],'documents_only')
            self.assertEqual(budget_plan['value']['operation_query_cap'],0)
            self.assertGreater(budget_plan['value']['target_cap'],0)
            receipts=[json.loads(path.read_text(encoding='utf-8'))['value']
                      for path in (artifacts/'budget-receipts').glob('*.json')]
            self.assertEqual(len(receipts),3)
            self.assertTrue(all(receipt['queries_total']==0 for receipt in receipts))
            self.assertTrue(all('round_grant' in receipt and 'shared_pool_remaining' in receipt
                                for receipt in receipts))

    def test_operation_modes_are_validated_and_fingerprinted(self):
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            with self.assertRaises(ValueError):store.create('case','claim','claim',evidence_mode='unknown')
            with self.assertRaises(ValueError):store.create('case','claim','claim',evidence_mode='documents_only')
            first=store.create('case','claim','claim',evidence_mode='documents_only',document_ids=['doc-a'])
            second=store.create('case','claim','claim',evidence_mode='documents_plus_search',document_ids=['doc-a'])
            self.assertNotEqual(first['input_fingerprint'],second['input_fingerprint'])

    def test_create_with_id_creates_final_folder_without_directory_rename(self):
        operation_id='12c609c2320b472484eb780e9419d21a'
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'.project-intelligence/claim-research')
            def denied_rename(_self,*_args,**_kwargs):
                raise PermissionError('directory rename is forbidden in this regression test')
            with patch.object(Path,'replace',denied_rename), patch.object(Path,'rename',denied_rename):
                record=store.create_with_id(operation_id,'case','claim','A synthetic question')
            final=store.root/operation_id
            self.assertTrue(final.is_dir())
            self.assertEqual([path.name for path in store.root.iterdir()],[operation_id])
            self.assertEqual(record['operation_id'],operation_id)
            saved_operation=json.loads((final/'operation.json').read_text(encoding='utf-8'))
            saved_input=json.loads((final/'input.json').read_text(encoding='utf-8'))
            self.assertEqual(saved_operation['operation_id'],operation_id)
            self.assertEqual(saved_input['operation_id'],operation_id)
            self.assertEqual(saved_operation['input_fingerprint'],saved_input['input_fingerprint'])

    def test_create_with_id_is_idempotent_and_preserves_artifacts_and_checkpoints(self):
        operation_id='bee3a1b837bb4186b3c3f59b740fc57b'
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            first=store.create_with_id(operation_id,'case','claim','A synthetic claim')
            failed=store.update(operation_id,status='failed',stage='failed',
                error={'type':'fixture','message':'retain'},updated_at='fixed-timestamp')
            artifact=store.artifact(operation_id,'agent-results',{'role':'planner','result':{'ok':True}})
            checkpoint=store.folder(operation_id)/artifact['path']
            before=(checkpoint.read_bytes(),(store.folder(operation_id)/'operation.json').read_bytes(),
                    (store.folder(operation_id)/'input.json').read_bytes())
            second=store.create_with_id(operation_id,'different-case','different-claim','changed input',
                evidence_mode='invalid')
            after=(checkpoint.read_bytes(),(store.folder(operation_id)/'operation.json').read_bytes(),
                   (store.folder(operation_id)/'input.json').read_bytes())
            self.assertEqual(second,failed)
            self.assertEqual(second['operation_id'],first['operation_id'])
            self.assertEqual(after,before)

    def test_create_with_id_concurrent_duplicate_converges_without_mixing(self):
        operation_id='e'*32
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda claim:store.create_with_id(operation_id,'case','claim',claim),
                                      ('claim A','claim B')))
            self.assertEqual([row['operation_id'] for row in results],[operation_id,operation_id])
            saved=json.loads((store.folder(operation_id)/'operation.json').read_text(encoding='utf-8'))
            input_record=json.loads((store.folder(operation_id)/'input.json').read_text(encoding='utf-8'))
            self.assertIn(saved['claim'],('claim A','claim B'))
            self.assertEqual(input_record['claim'],saved['claim'])
            self.assertEqual([path.name for path in store.root.iterdir()],[operation_id])

    def test_incomplete_existing_operation_folder_is_preserved_and_not_reinitialized(self):
        operation_id='f'*32
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            folder=store.folder(operation_id);folder.mkdir(parents=True)
            marker=folder/'artifacts'/'existing.bin';marker.parent.mkdir();marker.write_bytes(b'keep')
            with patch.object(research_operations.time,'monotonic',side_effect=[0,3]), \
                    patch.object(research_operations.time,'sleep'):
                with self.assertRaisesRegex(research_operations.OperationConflict,'no contiene una operación completa'):
                    store.create_with_id(operation_id,'case','claim','claim')
            self.assertEqual(marker.read_bytes(),b'keep')
            self.assertFalse((folder/'input.json').exists())
            self.assertFalse((folder/'operation.json').exists())

    def test_create_with_id_preserves_all_evidence_modes_and_authorized_document_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            store=research_operations.OperationStore(Path(temp)/'ops')
            modes=(('a'*32,'question_search',[]),
                   ('b'*32,'documents_only',['authorized-doc']),
                   ('c'*32,'documents_plus_search',['authorized-doc']))
            for operation_id,mode,document_ids in modes:
                with self.subTest(mode=mode):
                    record=store.create_with_id(operation_id,'case','claim','Question',
                        evidence_mode=mode,document_ids=document_ids,claim_version='claim-v4')
                    input_record=json.loads((store.folder(operation_id)/'input.json').read_text(encoding='utf-8'))
                    self.assertEqual(record['evidence_mode'],mode)
                    self.assertEqual(record['document_ids'],document_ids)
                    self.assertEqual(record['claim_version'],'claim-v4')
                    self.assertEqual(input_record['evidence_mode'],mode)
                    self.assertEqual(input_record['document_ids'],document_ids)
                    self.assertEqual(input_record['claim_version'],'claim-v4')

    def test_failed_claim_research_retry_keeps_final_id_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);case_folder=root/'case';case_folder.mkdir()
            library.save(case_folder/'claims.json',[{'id':'claim','claim':'A synthetic claim','status':'UNSUPPORTED'}])
            first_id='d'*32
            calls=[]
            class FailAfterPlanner(FakeProvider):
                def __call__(self,call):
                    calls.append(call.role)
                    if call.role=='formulation_reviewer':raise ValueError('synthetic failure after planner checkpoint')
                    return super().__call__(call)
            with patch.object(library,'case_path',return_value=case_folder):
                failed=research_operations.run_claim_research(root,'case','claim',operation_id=first_id,
                    evidence_mode='documents_plus_search',document_ids=['authorized-doc'],provider=FailAfterPlanner())
                self.assertEqual(failed['status'],'failed')
                store=research_operations.store(root)
                agent_results=store.folder(first_id)/'artifacts'/'agent-results'
                planner_artifacts=[path for path in agent_results.glob('*.json')
                    if json.loads(path.read_text(encoding='utf-8'))['value']['manifest']['agent']=='planner']
                self.assertEqual(len(planner_artifacts),1)
                retry_provider=FakeProvider()
                finished=research_operations.run_claim_research(root,'case','claim',operation_id=first_id,
                    evidence_mode='documents_plus_search',document_ids=['authorized-doc'],provider=retry_provider)
            self.assertEqual(finished['operation_id'],first_id)
            self.assertEqual(calls.count('planner'),1)
            self.assertNotIn('planner',[call.role for call in retry_provider.calls])
            planner_after=[path for path in (store.folder(first_id)/'artifacts'/'agent-results').glob('*.json')
                if json.loads(path.read_text(encoding='utf-8'))['value']['manifest']['agent']=='planner']
            self.assertEqual(len(planner_after),1)

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
