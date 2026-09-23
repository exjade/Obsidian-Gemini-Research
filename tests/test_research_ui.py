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
        globals="const verdictNames={VERIFIED:'Verificada',UNSUPPORTED:'Sin respaldo suficiente',UNVERIFIED:'Pendiente'};const sourceLabels={NOT_FOUND:'No encontrada'};const revisionNames={completed:'Finalizada',error:'Error'};"
        result=subprocess.run(['node','-e',globals+model+'\nconsole.log(JSON.stringify('+expression+'));'],capture_output=True,encoding='utf-8')
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

    def test_source_checks_deduplicate_and_revision_links_to_target(self):
        events=self.evaluate("activityEvents({claims:[{id:'a',source_checks:[{id:'receipt',checked_at:'2026-01-01',availability:'NOT_FOUND'}]},{id:'b',source_checks:[{id:'receipt',checked_at:'2026-01-01',availability:'NOT_FOUND'}]}],revisions:[{id:'r',claim_id:'b',submitted_at:'2026-01-02',updated_at:'2026-01-03',status:'error',error:'Recorded failure'}]})")
        self.assertEqual(len(events),3);self.assertEqual(events[0]['claim'],'b');self.assertEqual(events[0]['tone'],'failure')

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


    def test_activity_records_scope_human_and_provider_without_inventing_events(self):
        events=self.evaluate("activityEvents({meta:{scope_history:[{id:'scope',status:'approved',approved_at:'2026-01-01'}]},human_reviews:[{id:'human',claim_id:'a',reviewed_at:'2026-01-02',actor:'Reviewer',notes:'Checked',limits:'One passage'}],claims:[{id:'a',execution_receipts:[{run_id:'run',stage:'pass2',status:'provider_completed',finished_at:'2026-01-03',elapsed_seconds:12,reused:true}]}]})")
        self.assertEqual(len(events),3)
        rendered=json.dumps(events,ensure_ascii=False)
        self.assertIn('Alcance aprobado',rendered)
        self.assertIn('No modifica veredictos',rendered)
        self.assertIn('12 segundos',rendered)
        self.assertIn('reutilizada',rendered)

if __name__=='__main__':unittest.main()
