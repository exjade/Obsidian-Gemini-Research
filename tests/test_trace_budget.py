import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_trace
import pipeline


def tool(index,name,target,state='DONE'):
    key='query' if name=='search_web' else 'Url'
    return {'step_update':{'conversation_id':'c','step_index':index,'step_type':'tool',
            'state':state,'tool_name':name,'tool_info':{'parameters':{key:target}}}}


class TraceBudgetTests(unittest.TestCase):
    def test_totals_are_before_truncation_and_queries_are_grouped(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'.project-intelligence/evidence';folder.mkdir(parents=True)
            events=[tool(i,'search_web',' Same   Query ' if i in (0,1) else 'query '+str(i)) for i in range(88)]
            (folder/'run_pass2.raw.json').write_text('\n'.join(map(json.dumps,events)),encoding='utf-8')
            (folder/'run_pass2.input.json').write_text(json.dumps({'message':{'content':'x\n\nDATOS:\n'+json.dumps({'claims':[{'id':'a'}]})}}))
            claim={'id':'a','provenance':[{'run_id':'run'}]}
            self.assertEqual(len(action_trace.for_claim(root,claim)),80)
            summary=action_trace.summary_for_claim(root,claim)
            self.assertEqual((summary['total'],summary['visible'],summary['omitted']),(88,80,8))
            same=next(g for g in summary['query_groups'] if g['query'].strip()=='Same   Query')
            self.assertEqual((same['occurrences'],same['repeated']),(2,1))
            self.assertEqual(action_trace.for_claim(root,claim)[0]['attribution_label'],
                             'Ejecución iniciada para esta afirmación')

    def test_manifest_is_primary_attribution_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'.project-intelligence/evidence';folder.mkdir(parents=True)
            (folder/'run_pass2.manifest.json').write_text(json.dumps({'run_id':'run','stage':'pass2','claim_ids':['a']}))
            (folder/'run_pass2.input.json').write_text('{broken')
            self.assertEqual(action_trace.attribution(root,'run','pass2','a'),'single_claim')

    def test_call_writes_agent_budget_manifest(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(pipeline,'ROOT',Path(temp)),patch.object(pipeline,'INTEL',Path(temp)/'.project-intelligence'):
            (Path(temp)/'GEMINI.md').write_text('fixture')
            runner=pipeline.Runner.__new__(pipeline.Runner);runner.run_id='run';runner.exe='fake';runner.incremental=True
            envelope={'event':'result','result':{'status':'SUCCESS','response':'[]'}}
            with patch.object(runner,'_run_incremental',return_value=(0,(json.dumps(envelope)+'\n').encode(),b'',None)):
                runner.call('pass2','fixture',{'claims':[{'id':'a'}]},agent='locator',
                            budget={'timeout_seconds':30,'max_tool_actions':5})
            manifest=json.loads((Path(temp)/'.project-intelligence/evidence/run_pass2.manifest.json').read_text())
            self.assertEqual(manifest['claim_ids'],['a']);self.assertEqual(manifest['agent'],'locator')
            self.assertEqual(manifest['budget']['max_tool_actions'],5)

    def test_budget_stop_rejects_partial_result(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(pipeline,'ROOT',Path(temp)),patch.object(pipeline,'INTEL',Path(temp)/'.project-intelligence'):
            (Path(temp)/'GEMINI.md').write_text('fixture')
            runner=pipeline.Runner.__new__(pipeline.Runner);runner.run_id='run';runner.exe='fake';runner.incremental=True
            partial=(json.dumps(tool(1,'search_web','one'))+'\n'+json.dumps(tool(2,'search_web','two'))+'\n').encode()
            with patch.object(runner,'_run_incremental',return_value=(-15,partial,b'','exceder 1 consultas nuevas')):
                with self.assertRaisesRegex(ValueError,'salida parcial conservada y rechazada'):
                    runner.call('pass2','fixture',{'claims':[{'id':'a'}]},budget={'max_search_queries':1})
            prefix=Path(temp)/'.project-intelligence/evidence/run_pass2'
            self.assertTrue(prefix.with_suffix('.raw.json').is_file())
            self.assertFalse(prefix.with_suffix('.json').exists())


if __name__=='__main__':unittest.main()
