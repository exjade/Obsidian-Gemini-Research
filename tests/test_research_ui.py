"""Exercise the browser's pure state model with recorded-data fixtures."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which('node'), 'Optional frontend tests require Node')
class ResearchUITests(unittest.TestCase):
    def evaluate(self, expression):
        source=(Path(__file__).resolve().parents[1]/'scripts/frontend.html').read_text(encoding='utf-8')
        model=source.split('// BEGIN RESEARCH MODEL:')[1].split('// END RESEARCH MODEL')[0]
        model=model[model.index('\n'):]
        model+='\n'+next(line for line in source.splitlines() if line.startswith('const stateNames='))
        model+='\n'+next(line for line in source.splitlines() if line.startswith('function caseConclusion('))
        globals="function localDate(value){return new Date(value).toLocaleString('es-ES')}const verdictNames={VERIFIED:'Verificada',UNSUPPORTED:'Sin respaldo suficiente',UNVERIFIED:'Pendiente'};const sourceLabels={NOT_FOUND:'No encontrada'};const revisionNames={completed:'Finalizada',error:'Error'};"
        result=subprocess.run(['node','-e',globals+model+'\nconsole.log(JSON.stringify('+expression+'));'],capture_output=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def render_history(self, history, global_busy=False):
        source=(Path(__file__).resolve().parents[1]/'scripts/frontend.html').read_text(encoding='utf-8')
        model=source.split('// BEGIN RESEARCH MODEL:')[1].split('// END RESEARCH MODEL')[0]
        model=model[model.index('\n'):]
        render=source[source.index('function text(parent,value,tag='):source.index('function renderClaimTimeline(')]
        globals="""
function localDate(value){return value?new Date(value).toLocaleString('es-ES'):'Fecha no registrada'}
function timelineDate(value){return value?localDate(value):'Fecha no registrada'}
function operationStatusLabel(o){return ({queued:'En espera',running:'En curso',done:'Terminada',resolved:'Resuelta',completed_with_limits:'Completada con límites',failed:'Fallida',error:'Fallida',cancelled:'Cancelada'}[o.status]||o.status||'Estado no registrado')}
function operationResolution(o){return o.result?.scientific_resolution||o.result?.bounded_resolution||null}
function operationFinishLabel(o){if(o?.finished_at)return 'Finalizada: '+localDate(o.finished_at);if(o?.updated_at)return 'Última actualización: '+localDate(o.updated_at)+' · fecha de finalización no registrada';return 'Fecha de finalización no registrada'}
const document={createElement(tag){return {tag,children:[],attrs:{},append(...items){this.children.push(...items)},setAttribute(key,value){this.attrs[key]=value},getAttribute(key){return this.attrs[key]}}}}
function collect(node){return [node.textContent||'',...node.children.flatMap(collect)]}
"""
        expression="const root=document.createElement('section');renderClaimOperations(root,"+json.dumps({"claim_research_history":history})+",{globalBusy:"+json.dumps(global_busy)+"});console.log(JSON.stringify(collect(root)))"
        result=subprocess.run(['node','-e',globals+model+'\n'+render+'\n'+expression],capture_output=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        return '\n'.join(json.loads(result.stdout))

    def render_technical_history(self, claim):
        source=(Path(__file__).resolve().parents[1]/'scripts/frontend.html').read_text(encoding='utf-8')
        model=source.split('// BEGIN RESEARCH MODEL:')[1].split('// END RESEARCH MODEL')[0]
        model=model[model.index('\n'):]
        render=source[source.index('function text(parent,value,tag='):source.index('function renderClaimTimeline(')]
        globals="""
function localDate(value){return value?new Date(value).toLocaleString('es-ES'):'Fecha no registrada'}
function timelineDate(value){return value?localDate(value):'Fecha no registrada'}
function operationStatusLabel(o){return ({queued:'En espera',running:'En curso',done:'Terminada',resolved:'Resuelta',completed_with_limits:'Completada con límites',failed:'Fallida',error:'Fallida',cancelled:'Cancelada'}[o.status]||o.status||'Estado no registrado')}
const document={createElement(tag){return {tag,children:[],attrs:{},append(...items){this.children.push(...items)},setAttribute(key,value){this.attrs[key]=value}}}}
function collect(node){return [node.textContent||'',...node.children.flatMap(collect)]}
"""
        expression="const root=document.createElement('section');renderTechnicalCheckHistory(root,"+json.dumps(claim,ensure_ascii=False)+");console.log(JSON.stringify(collect(root)))"
        result=subprocess.run(['node','-e',globals+model+'\n'+render+'\n'+expression],capture_output=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        return '\n'.join(json.loads(result.stdout))

    def render_scientific_and_verdict_history(self, claim):
        source=(Path(__file__).resolve().parents[1]/'scripts/frontend.html').read_text(encoding='utf-8')
        render=source[source.index('function text(parent,value,tag='):source.index('function renderActionTrace(')]
        verdict_start=source.index('function renderVerdictHistory(')
        verdict_end=source.index('\n\nfunction humanReviewForm(',verdict_start)
        render+=source[verdict_start:verdict_end]
        globals="""
function timelineDate(value){return value?new Date(value).toLocaleString('es-ES'):'Fecha no registrada'}
const verdictNames={VERIFIED:'Verificada',UNSUPPORTED:'Sin respaldo suficiente',UNVERIFIED:'Pendiente'};
const document={createElement(tag){return {tag,children:[],attrs:{},append(...items){this.children.push(...items)},setAttribute(key,value){this.attrs[key]=value}}}}
function collect(node){return [node.textContent||'',...node.children.flatMap(collect)]}
"""
        expression="const resolution=document.createElement('section');renderScientificResolutionHistory(resolution,"+json.dumps(claim,ensure_ascii=False)+");const verdict=document.createElement('section');renderVerdictHistory(verdict,"+json.dumps(claim,ensure_ascii=False)+");console.log(JSON.stringify({resolution:collect(resolution),verdict:collect(verdict)}))"
        result=subprocess.run(['node','-e',globals+render+'\n'+expression],capture_output=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def test_finished_process_can_have_no_supported_conclusion(self):
        model=self.evaluate("researchModel({meta:{question:'Question',status:'completed'},claims:[{status:'UNSUPPORTED',evidence:[{type:'external'}]}],documents:{research:'# Results'}})")
        self.assertEqual(model['steps'],[True,True,True,True,True])
        self.assertEqual(model['ready'],0);self.assertEqual(model['attention'],1)

    def test_old_verified_with_unconfirmed_sources_needs_attention(self):
        model=self.evaluate("researchModel({meta:{question:'Question',status:'running'},claims:[{status:'VERIFIED',external_content_confirmed:false,evidence:[{type:'external'}]}],documents:{research:'Pendiente de esta pasada.'}})")
        self.assertFalse(model['published']);self.assertEqual(model['ready'],0)

    def test_inconclusive_report_is_published_but_initial_placeholder_is_not(self):
        completed=self.evaluate("researchModel({meta:{status:'completed'},documents:{research:'Todavía no hay claims VERIFIED consolidados.'}})")
        self.assertTrue(completed['published'])
        placeholder=self.evaluate("researchModel({meta:{status:'completed'},documents:{research:'# Resultados\\n\\nPendientes de investigación y revisión.'}})")
        self.assertFalse(placeholder['published'])
        recorded=self.evaluate("researchModel({meta:{status:'running',publication:{completed:true,outcome:'inconclusive'}},documents:{research:'# Informe'}})")
        self.assertTrue(recorded['published']);self.assertEqual(recorded['ready'],0)

    def test_no_events_fabricated_from_final_status(self):
        self.assertEqual(self.evaluate("activityEvents({meta:{status:'completed'},claims:[{status:'VERIFIED'}]})"),[])

    def test_activity_does_not_rebuild_claim_events_from_legacy_arrays(self):
        events=self.evaluate("activityEvents({claims:[{id:'a',source_checks:[{id:'receipt',checked_at:'2026-01-01',availability:'NOT_FOUND'}]}],revisions:[{id:'r',claim_id:'a',submitted_at:'2026-01-02',updated_at:'2026-01-03',status:'error',error:'Recorded failure'}]})")
        self.assertEqual(events,[])

    def test_research_action_allows_first_run_and_explicit_new_run_after_completion(self):
        first=self.evaluate("claimResearchActionState({operations:[],latest_operation:null,current_completed:null,has_active:false},false)")
        self.assertFalse(first['disabled']);self.assertEqual(first['label'],'Buscar respaldo y reevaluar automáticamente')
        operation={"kind":"claim_research","operation_id":"completed","status":"completed_with_limits","result":{}}
        completed=self.evaluate("claimResearchActionState("+json.dumps({"operations":[operation],"latest_operation":operation,"current_completed":operation,"has_active":False})+",false)")
        self.assertFalse(completed['disabled']);self.assertTrue(completed['newRun']);self.assertEqual(completed['label'],'Investigar de nuevo')

    def test_research_action_disables_only_while_incompatible_work_is_running(self):
        running={"kind":"claim_research","operation_id":"active","status":"running"}
        active=self.evaluate("claimResearchActionState("+json.dumps({"operations":[running],"latest_operation":running,"current_completed":None,"has_active":True})+",false)")
        self.assertTrue(active['disabled']);self.assertEqual(active['label'],'Investigación en curso')
        globally_busy=self.evaluate("claimResearchActionState({operations:[],latest_operation:null,current_completed:null,has_active:false},true)")
        self.assertTrue(globally_busy['disabled'])

    def test_old_operation_does_not_present_updated_at_as_finish_time(self):
        with_finish=self.evaluate("operationFinishLabel({finished_at:'2026-09-23T12:00:00Z',updated_at:'2026-09-23T12:01:00Z'})")
        without_finish=self.evaluate("operationFinishLabel({updated_at:'2026-09-23T12:01:00Z'})")
        no_dates=self.evaluate("operationFinishLabel({})")
        self.assertTrue(with_finish.startswith('Finalizada:'))
        self.assertIn('Última actualización:',without_finish)
        self.assertIn('no registrada',without_finish)
        self.assertEqual(no_dates,'Fecha de finalización no registrada')

    def test_failed_attempt_can_be_retried_and_completed_result_stays_distinct(self):
        completed={"kind":"claim_research","operation_id":"A","status":"completed_with_limits","result":{"scientific_resolution":{"resolution":"indeterminate"}}}
        failed={"kind":"claim_research","operation_id":"B","status":"failed","error":"broken"}
        history={"operations":[failed,completed],"latest_operation":failed,"current_completed":completed,"has_active":False}
        state=self.evaluate("claimResearchActionState("+json.dumps(history)+",false)")
        self.assertFalse(state['disabled']);self.assertTrue(state['newRun'])
        self.assertEqual(state['label'],'Investigar de nuevo')
        self.assertEqual(state['latest']['status'],'failed')
        self.assertEqual(state['current']['operation_id'],'A')
        self.assertEqual([row['operation_id'] for row in state['operations']],['B','A'])

    def test_operation_error_facets_are_all_preserved_and_exact_duplicates_are_collapsed(self):
        operation={"frontend_error":{"type":"UIError","message":"Refresh failed"},
                   "engine_error":{"type":"ValueError","message":"Research failed"},
                   "error":{"type":"ValueError","message":"Research failed"}}
        errors=self.evaluate("operationErrors("+json.dumps(operation)+")")
        self.assertEqual(errors,[{"type":"ValueError","message":"Research failed","origin":"Motor"},
                                 {"type":"UIError","message":"Refresh failed","origin":"Interfaz"}])
        same_message=self.evaluate("operationErrors({frontend_error:{type:'ProviderError',message:'same'},engine_error:{type:'ProviderError',message:'same'},error:{type:'ProviderError',message:'same'}})")
        self.assertEqual([row['origin'] for row in same_message],["Motor","Interfaz"])
        legacy=self.evaluate("operationErrors({error:'legacy failure'})")
        self.assertEqual(legacy,[{"type":"No registrado","message":"legacy failure","origin":"Operación"}])

    def test_failed_operation_detail_keeps_id_type_message_stage_and_failure_time(self):
        failed={"kind":"claim_research","operation_id":"failed-1","status":"failed",
                "requested_at":"2026-09-23T10:00:00Z","finished_at":"2026-09-23T10:03:00Z",
                "stage":"Revisión crítica","engine_error":{"type":"AgentOutputError","message":"Salida inválida"}}
        rendered=self.render_history({"operations":[failed],"latest_operation":failed,"has_active":False})
        for expected in ["failed-1","AgentOutputError","Salida inválida","Revisión crítica","Fecha del fallo:","Reintentar este intento"]:
            self.assertIn(expected,rendered)

    def test_failed_operation_error_survives_other_global_service_states_and_technical_check(self):
        failed={"kind":"claim_research","operation_id":"failed-2","status":"failed",
                "finished_at":"2026-09-23T10:00:00Z","stage":"Recopilando evidencia",
                "error":{"type":"ValueError","message":"Persisted research failure"}}
        completed={"kind":"claim_research","operation_id":"completed-1","status":"resolved",
                   "result":{"scientific_resolution":{"resolution":"indeterminate"}},"is_current_result":True}
        technical={"kind":"technical_check","operation_id":"check-1","status":"done","error":{"message":"Technical only"}}
        history={"operations":[failed,technical,completed],"latest_operation":failed,"current_completed":completed,"has_active":False}
        after_done=self.render_history(history,global_busy=False)
        while_busy=self.render_history(history,global_busy=True)
        for rendered in [after_done,while_busy]:
            self.assertIn("Persisted research failure",rendered)
            self.assertIn("failed-2",rendered)
            self.assertIn("completed-1",rendered)
            self.assertIn("indeterminate",rendered)
            self.assertNotIn("Technical only",rendered)

    def test_technical_check_history_is_separate_and_never_claims_scientific_resolution(self):
        research_failed={"kind":"claim_research","operation_id":"research-failed","status":"failed","error":{"type":"ValueError","message":"research remains failed"}}
        technical={"kind":"technical_check","operation_id":"technical-1","status":"done",
                   "requested_at":"2026-09-23T11:00:00Z","finished_at":"2026-09-23T11:01:00Z",
                   "result":{"checked":1,"changed":1,"unchanged":0,"errors":0,"verdict_changed":False,
                             "message":"HTTP 200; pasaje localizado; pertinencia no evaluada.",
                             "source_receipts":[{"source_id":"source-1","availability":"AVAILABLE","http_status":200,
                                                 "final_url":"https://example.org/final","excerpt_match":True,
                                                 "checked_at":"2026-09-23T11:00:30Z"}]}}
        rendered=self.render_technical_history({"technical_check_history":[technical],"latest_operations":[technical,research_failed]})
        for expected in ["Historial técnico de acceso y pasajes","HTTP","redirecciones/URL final","pasaje conocido sigue recuperable",
                         "no buscan estudios nuevos","no rehacen la investigación","no cambian el veredicto ni la resolución científica",
                         "technical-1","HTTP 200","URL final: https://example.org/final","pasaje localizado",
                         "Esta comprobación técnica no produce una resolución científica"]:
            self.assertIn(expected,rendered)
        self.assertNotIn("research-failed",rendered)
        self.assertNotIn("research remains failed",rendered)
        self.assertNotIn("Resolución científica: supported",rendered)

    def test_technical_check_action_copy_explains_its_limited_scope(self):
        source=(Path(__file__).resolve().parents[1]/'scripts/frontend.html').read_text(encoding='utf-8')
        self.assertNotIn('Volver a comprobar esta página',source)
        self.assertNotIn('Volver a comprobar las páginas',source)
        self.assertIn('Recomprobar acceso y pasajes de las fuentes',source)
        for expected in ['acceso HTTP','redirecciones/URL final','presencia literal del pasaje','No busca estudios nuevos',
                         'no rehace investigaciones','no cambia por sí sola veredictos ni resoluciones científicas']:
            self.assertIn(expected,source)

    def test_failed_research_retry_is_not_offered_for_older_failure(self):
        latest={"kind":"claim_research","operation_id":"latest-failed","status":"failed","error":"retry me"}
        older={"kind":"claim_research","operation_id":"older-failed","status":"failed","error":"older error"}
        history={"operations":[latest,older],"latest_operation":latest,"has_active":False}
        rendered=self.render_history(history)
        self.assertEqual(rendered.count("Reintentar este intento"),1)

    def test_research_view_model_keeps_all_claim_runs_and_ignores_technical_checks(self):
        completed={"kind":"claim_research","operation_id":"A","status":"resolved","result":{"scientific_resolution":{"resolution":"supported"}},"is_current_result":True}
        failed={"kind":"claim_research","operation_id":"B","status":"failed","error":{"message":"provider error"},"is_current_result":False}
        technical={"kind":"technical_check","operation_id":"check-1","status":"done","result":{}}
        history={"operations":[failed,technical,completed],"latest_operation":failed,"current_completed":completed,"has_active":False}
        model=self.evaluate("claimResearchViewModel("+json.dumps(history)+",false)")
        self.assertEqual([row['operation_id'] for row in model['operations']],['B','A'])
        self.assertEqual(model['current']['operation_id'],'A')
        self.assertEqual(model['latest']['operation_id'],'B')
        self.assertEqual(sum(row['is_current_result'] for row in model['operations']),1)

    def test_failed_only_history_still_offers_explicit_new_run(self):
        failed={"kind":"claim_research","operation_id":"failed","status":"failed","error":"provider error"}
        model=self.evaluate("claimResearchActionState("+json.dumps({"operations":[failed],"latest_operation":failed,"current_completed":None,"has_active":False})+",false)")
        self.assertFalse(model['disabled'])
        self.assertTrue(model['newRun'])
        self.assertEqual(model['label'],'Investigar de nuevo')

    def test_history_markup_is_semantic_mobile_friendly_and_does_not_invent_budget(self):
        source=(Path(__file__).resolve().parents[1]/'scripts/frontend.html').read_text(encoding='utf-8')
        self.assertIn("c.claim_research_history",source[source.index("function renderClaimOperations"):source.index("function renderClaimTimeline")])
        self.assertIn("setAttribute('aria-label','Historial de investigaciones')",source)
        self.assertIn("text(section,'Historial de investigaciones','h4')",source)
        self.assertIn("s.textContent='Ver detalle",source)
        detail=source[source.index("function renderOperationDetail"):source.index("function renderClaimOperations")]
        self.assertNotIn("1800",detail)
        self.assertIn("consumo:",detail)
        self.assertNotIn("technical_check",source[source.index("function renderClaimOperations"):source.index("function renderTechnicalCheckHistory")])
        self.assertRegex(source,r"@media\(max-width:480px\)")
        self.assertIn("function text(parent,value,tag='p')",source)
        self.assertIn("Estado global del servicio",source)
        self.assertIn("global-job-state",source)
        self.assertIn("Falló la ejecución general del expediente",source)

    def test_history_renderer_shows_current_result_latest_failure_and_each_run(self):
        current={"kind":"claim_research","operation_id":"A-current","status":"resolved","requested_at":"2026-09-22T10:00:00Z","finished_at":"2026-09-22T11:00:00Z","result":{"scientific_resolution":{"resolution":"indeterminate"},"research_summary":{"summary":"Conclusión limitada"}},"is_current_result":True}
        latest={"kind":"claim_research","operation_id":"B-failed","status":"failed","requested_at":"2026-09-23T10:00:00Z","stage":"Recopilando evidencia","evidence_mode":"documents_plus_search","document_ids":["doc-1"],"progress":{"queries":4,"pages":7,"elapsed_seconds":50},"budget_plan":{"operation_query_cap":16,"operation_page_cap":24,"hard_global_caps":{"seconds":1800}},"error":{"type":"ValueError","message":"Provider stopped"},"is_current_result":False}
        history={"operations":[latest,current],"latest_operation":latest,"current_completed":current,"has_active":False}
        rendered=self.render_history(history)
        self.assertIn("Resultado científico vigente",rendered)
        self.assertIn("A-current",rendered)
        self.assertIn("indeterminate",rendered)
        self.assertIn("Último intento · Fallida",rendered)
        self.assertIn("B-failed",rendered)
        self.assertIn("Provider stopped",rendered)
        self.assertIn("Historial de investigaciones",rendered)
        self.assertIn("PDFs + búsqueda",rendered)
        self.assertIn("doc-1",rendered)
        self.assertIn("16 consultas",rendered)
        self.assertIn("7 páginas",rendered)
        self.assertIn("VIGENTE",rendered)
        self.assertEqual(rendered.count("Ver detalle"),2)
        self.assertNotIn("Comprobación técnica",rendered)

    def test_empty_research_history_still_has_its_own_section(self):
        rendered=self.render_history({"operations":[],"latest_operation":None,"current_completed":None,"has_active":False})
        self.assertIn("Historial de investigaciones",rendered)
        self.assertIn("Aún no hay investigaciones registradas.",rendered)
        self.assertIn("Este historial no representa cambios del veredicto.",rendered)

    def test_research_verdict_and_scientific_resolution_histories_render_as_distinct_sections(self):
        claim={"scientific_resolution_history":[
            {"resolution_id":"res-supported","resolution":"supported","created_at":"2026-09-22T10:00:00Z","operation_id":"op-a","claim_version":2,"input_fingerprint":"fp-a","limitations":["Adult sample"],"dimensions":{"population":{"state":"supported"}}},
            {"resolution_id":"res-indeterminate","resolution":"indeterminate","created_at":"2026-09-23T10:00:00Z","operation_id":"op-b","claim_version":3,"input_fingerprint":"fp-b","limitations":["No delayed measure"],"dimensions":{"horizon":{"state":"unresolved"}}},
        ],"timeline":[
            {"category":"scientific_resolution","source_record_id":"res-supported","operation_id":"op-a","occurred_at":"2026-09-22T10:00:00Z","details":{"resolution_id":"res-supported","resolution":"supported","claim_version":2,"input_fingerprint":"fp-a","limitations":["Adult sample"],"dimensions":{"population":{"state":"supported"}},"evidence_links":[{"source_id":"source-a","evidence_id":"passage-a"}]}},
            {"category":"scientific_resolution","source_record_id":"res-indeterminate","operation_id":"op-b","occurred_at":"2026-09-23T10:00:00Z","details":{"resolution_id":"res-indeterminate","resolution":"indeterminate","claim_version":3,"input_fingerprint":"fp-b","limitations":["No delayed measure"],"dimensions":{"horizon":{"state":"unresolved"}},"evidence_ids":["passage-b"]}},
        ],"provenance":[]}
        rendered=self.render_scientific_and_verdict_history(claim)
        resolution='\n'.join(rendered['resolution']);verdict='\n'.join(rendered['verdict'])
        for expected in ['Historial de resolución científica','supported','indeterminate','op-a','op-b','2026','fp-a','fp-b','population: supported','horizon: unresolved','Adult sample','No delayed measure','source-a/passage-a','passage-b']:
            self.assertIn(expected,resolution)
        self.assertNotIn('Historial de evaluación',resolution)
        self.assertIn('Historial de evaluación',verdict)
        self.assertIn('Una investigación automática que no cambió el veredicto',verdict)
        self.assertIn('No hay cambios de veredicto registrados.',verdict)
        self.assertNotIn('supported',verdict)
        self.assertNotIn('indeterminate',verdict)

    def test_legacy_resolution_without_id_or_date_remains_visible_without_invented_values(self):
        rendered=self.render_scientific_and_verdict_history({"scientific_resolution_history":[
            {"resolution":"unresolved","limitations":"Registro antiguo"}
        ],"provenance":[]})
        resolution='\n'.join(rendered['resolution'])
        self.assertIn('unresolved',resolution)
        self.assertIn('Fecha no registrada',resolution)
        self.assertIn('Operación no registrada',resolution)
        self.assertIn('Versión de afirmación no registrada',resolution)

    def test_activity_uses_claim_timeline_without_duplicate_reevaluation_events(self):
        data={"activity_timeline":[
            {"event_id":"request","event_type":"investigation.requested","timestamp":"2026-01-01T00:00:00Z",
             "title":"Reevaluación supervisada solicitada","text":"Material conservado","claim_id":"claim-1","target_view":"claims"},
            {"event_id":"status","event_type":"investigation.failed","timestamp":"2026-01-02T00:00:00Z",
             "title":"Estado de reevaluación supervisada","text":"timeout","claim_id":"claim-1","target_view":"claims"}],
            "claims":[{"id":"claim-1","timeline":[]}],
            "revisions":[{"id":"revision-1","claim_id":"claim-1","submitted_at":"2026-01-01T00:00:00Z",
                           "updated_at":"2026-01-02T00:00:00Z","status":"error","error":"timeout"}]}
        events=self.evaluate("activityEvents("+json.dumps(data,ensure_ascii=False)+")")
        self.assertEqual(len(events),2)
        self.assertEqual([event['event_id'] for event in events],['request','status'])
        self.assertEqual(sum(event['title']=='Reevaluación supervisada solicitada' for event in events),1)
        self.assertEqual(sum(event['title']=='Estado de reevaluación supervisada' for event in events),1)
        self.assertEqual(events[0]['target_view'],'claims')

    def test_main_explanation_removes_flags_and_keeps_qualification(self):
        text=self.evaluate("humanText(\"domain='general', sensible=false; favorable=true. No hay evidencia primaria: status UNSUPPORTED. [Control del wrapper: FAVORABLE=True]\")")
        self.assertNotIn('false',text);self.assertNotIn('true',text);self.assertNotIn('domain=',text)
        self.assertIn('No hay evidencia primaria',text);self.assertIn('sin respaldo suficiente',text)

    def test_gaps_distinguish_missing_restricted_and_unconfirmed_passages(self):
        rows=self.evaluate("evidenceGaps({evidence:[{type:'external'},{type:'external'},{type:'external'}],source_checks:[{availability:'NOT_FOUND'},{availability:'RESTRICTED'},{availability:'AVAILABLE',excerpt_match:false,eligible:false}]})")
        self.assertEqual([r['kind'] for r in rows],['missing','restricted','unmatched'])
        self.assertEqual([r['source'] for r in rows],[1,2,3])

    def test_successful_retrieval_is_not_an_automatic_verdict(self):
        rows=self.evaluate("evidenceGaps({status:'UNSUPPORTED',evidence:[{type:'external'}],source_checks:[{availability:'AVAILABLE',excerpt_match:true,eligible:true}]})")
        self.assertEqual(rows,[])
        self.assertEqual(self.evaluate("evidenceGaps({evidence:[]})")[0]['kind'],'missing')

    def test_page_text_does_not_repeat_overlapping_retrieval_chunks(self):
        self.assertEqual(self.evaluate("documentPageText({chunks:[{offset:0,text:'abcdef'},{offset:4,text:'efghij'}]})"),'abcdefghij')
        self.assertEqual(self.evaluate("documentPageText({page_text:'original page',chunks:[]})"),'original page')

    def test_closure_controls_headline_even_if_some_claims_are_verified(self):
        blocked=self.evaluate("caseConclusion({meta:{status:'completed'},claims:[{status:'VERIFIED'}],closure:{ready:false,consolidated:false,total:2,resolved:1}})")
        self.assertIn('inconclusa',blocked);self.assertIn('1 de 2',blocked)
        ready=self.evaluate("caseConclusion({meta:{status:'completed'},closure:{ready:true,consolidated:false,total:1,resolved:1}})")
        self.assertIn('lista para consolidar',ready)
        done=self.evaluate("caseConclusion({meta:{status:'completed'},closure:{ready:true,consolidated:true,total:1,resolved:1}})")
        self.assertIn('resultados consolidados',done)

    def test_execution_distinguishes_evaluated_from_scientifically_resolved(self):
        text=self.evaluate("executionExplanation({meta:{scope:{selected_ids:['a','b']}},claims:[{id:'a',status:'UNSUPPORTED'},{id:'b',status:'UNVERIFIED'},{id:'outside',status:'VERIFIED'}],closure:{resolved:0}}, {})")
        self.assertIn('2 hipótesis',text)
        self.assertIn('1 tienen un veredicto',text)
        self.assertIn('0 están resueltas',text)
        self.assertIn('se conservan',text)

    def test_execution_errors_explain_recovery_without_claiming_success(self):
        text=self.evaluate("executionError({log:'ERROR: pass3: Antigravity superó 900 segundos; salida parcial conservada.'})")
        self.assertIn('una recopilación completa todavía válida',text)
        self.assertIn('Se agotó el tiempo',text)
        self.assertIn('Mensaje registrado: pass3:',text)

    def test_execution_error_prefers_structured_operation_message_and_identifies_scope(self):
        job={'status':'error','operation_id':'op-1','stage':'general stage','log':'',
             'operation':{'operation_id':'op-1','kind':'claim_research','claim_id':'claim-1',
                          'stage':'retriever','error':{'type':'AgentOutputError','message':'Fuente inválida'}}}
        detail=self.evaluate('executionDetail('+json.dumps(job,ensure_ascii=False)+')')
        summary=self.evaluate('executionSummary('+json.dumps(job,ensure_ascii=False)+')')
        link=self.evaluate('executionOperationLink('+json.dumps(job,ensure_ascii=False)+')')
        self.assertIn('Fuente inválida',detail)
        self.assertIn('AgentOutputError',detail)
        self.assertIn('op-1',detail)
        self.assertIn('retriever',detail)
        self.assertIn('estado global',detail)
        self.assertIn('Operación op-1',summary)
        self.assertIn('Etapa retriever',summary)
        self.assertEqual(link,{'view':'claims','claim_id':'claim-1'})

    def test_execution_error_without_registered_message_is_explicit_and_nonempty(self):
        job={'status':'error','operation_id':'op-empty','log':'',
             'operation':{'operation_id':'op-empty','kind':'claim_research','stage':'auditor',
                          'error':{'type':'ProviderError'}}}
        error=self.evaluate('executionError('+json.dumps(job)+')')
        detail=self.evaluate('executionDetail('+json.dumps(job)+')')
        self.assertIn('El error no fue registrado',error)
        self.assertTrue(detail.strip())
        self.assertIn('op-empty',detail)
        self.assertIn('auditor',detail)
        self.assertIn('ProviderError',detail)
        self.assertIn('detalle de la operación',error)

    def test_execution_error_reads_legacy_prefixed_and_unprefixed_logs(self):
        prefixed=self.evaluate("executionError({status:'error',log:'inicio\\nERROR: provider failed'})")
        plain=self.evaluate("executionError({status:'error',log:'provider failed without prefix'})")
        self.assertEqual(prefixed,'provider failed')
        self.assertEqual(plain,'provider failed without prefix')

    def test_execution_global_detail_survives_refresh_projection_and_keeps_scoped_error_separate(self):
        job={'status':'error','operation_id':'op-refresh','stage':'fallback','log':'',
             'operation':{'operation_id':'op-refresh','kind':'claim_research','claim_id':'claim-x',
                          'stage':'review','error':{'type':'ValueError','message':'persisted failure'}}}
        texts=self.evaluate('(()=>{const job='+json.dumps(job)+';return [executionLogText(job),executionLogText(job)]})()')
        self.assertEqual(texts[0],texts[1])
        self.assertIn('persisted failure',texts[0])
        self.assertIn('Este detalle resume el estado global',texts[0])
        self.assertIn('error canónico',self.evaluate('executionSummary('+json.dumps(job)+')'))
        self.assertIsNone(self.evaluate("executionOperationLink({status:'error',operation_id:'op-tech',operation:{kind:'technical_check',operation_id:'op-tech'}})"))


    def test_activity_records_scope_human_and_provider_without_inventing_events(self):
        events=self.evaluate("activityEvents({meta:{scope_history:[{id:'scope',status:'approved',approved_at:'2026-01-01'}]},human_reviews:[{id:'human',claim_id:'a',reviewed_at:'2026-01-02',actor:'Reviewer',notes:'Checked',limits:'One passage'}],claims:[{id:'a',execution_receipts:[{run_id:'run',stage:'pass2',status:'provider_completed',finished_at:'2026-01-03',elapsed_seconds:12,reused:true}]}]})")
        self.assertEqual(events,[])

    def test_activity_render_links_to_claim_and_uses_server_event_order(self):
        source=(Path(__file__).resolve().parents[1]/'scripts/frontend.html').read_text(encoding='utf-8')
        self.assertIn("function activityEvents(data){return Array.isArray(data?.activity_timeline)?data.activity_timeline:[]}",source)
        self.assertEqual(self.evaluate("[activityTargetView({claim_id:'claim-a'}),activityTargetView({claim_id:'claim-a',target_view:'sources'}),activityTargetView({})]"),['claims','sources','overview'])
        self.assertIn("caseLink(activeCase,activityTargetView(e),e.claim_id||null)",source)
        self.assertIn("const visible=limit?events.slice(-limit):events.slice(-100)",source)
        self.assertNotIn('return result.sort(',source[source.index('function activityEvents(data)'):source.index('function evidenceGaps')])
        self.assertIn("function renderClaimTimeline(card,c){\n const rows=c.timeline||[]",source)
        model=source.split('// BEGIN RESEARCH MODEL:')[1].split('// END RESEARCH MODEL')[0]
        model=model[model.index('\n'):]
        case_link=next(line for line in source.splitlines() if line.startswith('function caseLink('))
        globals="const location={href:'http://127.0.0.1:8765/?vista=actividad'};const activeCase='case-1';const viewNames={claims:'afirmaciones',sources:'fuentes',overview:'resumen'};"
        expression="JSON.stringify(['claim-a',null].map(claim=>{const event=claim?{claim_id:claim}:{};const url=new URL(caseLink(activeCase,activityTargetView(event),claim),location.href);return {view:url.searchParams.get('vista'),caseId:url.searchParams.get('investigacion'),claimId:url.searchParams.get('claim')}}))"
        result=subprocess.run(['node','-e',globals+case_link+model+'\nconsole.log('+expression+')'],capture_output=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),[
            {'view':'afirmaciones','caseId':'case-1','claimId':'claim-a'},
            {'view':'resumen','caseId':'case-1','claimId':None},
        ])

if __name__=='__main__':unittest.main()
