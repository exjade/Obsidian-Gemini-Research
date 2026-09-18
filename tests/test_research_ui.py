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


if __name__=='__main__':unittest.main()
