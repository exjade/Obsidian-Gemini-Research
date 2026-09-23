import sys
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import pipeline


class JsonResponseTests(unittest.TestCase):
    def test_accepts_fenced_single_object_as_one_item_array(self):
        self.assertEqual(pipeline.array_response('```json\n{"matrix": []}\n```'), [{'matrix': []}])

    def test_accepts_array_without_fence(self):
        self.assertEqual(pipeline.array_response('[{"ok": true}]'), [{'ok': True}])

    def test_rejects_scalar_and_surrounding_prose(self):
        with self.assertRaises(ValueError):
            pipeline.array_response('"hello"')
        with self.assertRaises(ValueError):
            pipeline.array_response('Aquí está: [{"ok": true}]')

    def test_specialized_prompt_policy_isolated_from_project_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'GEMINI.md').write_text('INSTRUCCIÓN AMBIENTE: usa MCP',encoding='utf-8')
            runner=pipeline.Runner.__new__(pipeline.Runner)
            runner.run_id='isolated';runner.exe='unused';runner.incremental=True
            result={'event':'result','result':{'status':'SUCCESS','response':'[{"decision":"continue"}]'}}
            observed={}
            def provider(input_bytes,budget,workdir=None):
                observed['prompt']=json.loads(input_bytes)['message']['content']
                observed['workdir']=Path(workdir)
                observed['has_project_contract']=(Path(workdir)/'GEMINI.md').exists()
                observed['budget']=budget
                return 0,(json.dumps(result)+'\n').encode(),b'',None
            with patch.object(pipeline,'ROOT',root),patch.object(pipeline,'INTEL',root/'.project-intelligence'):
                with patch.object(runner,'_run_incremental',side_effect=provider):
                    rows=runner.call('agent_final_auditor','Compara pasajes.',
                                     {'claims':[{'id':'c'}]},agent='final_auditor',
                                     budget={'max_tool_actions':0,'allowed_tools':[]})
            self.assertEqual(rows,[{'decision':'continue'}])
            self.assertNotIn('INSTRUCCIÓN AMBIENTE',observed['prompt'])
            self.assertNotEqual(observed['workdir'],root)
            self.assertFalse(observed['has_project_contract'])
            self.assertEqual(observed['budget']['allowed_tools'],[])

    def test_retriever_view_file_attempt_is_rejected_and_partial_stream_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(pipeline,'ROOT',Path(temp)), patch.object(pipeline,'INTEL',Path(temp)/'.project-intelligence'):
            root=Path(temp)
            (root/'GEMINI.md').write_text('untrusted project context',encoding='utf-8')
            runner=pipeline.Runner.__new__(pipeline.Runner)
            runner.run_id='view-file-rejected';runner.exe='unused';runner.incremental=True
            internal_path=r'C:\Users\example\.gemini\antigravity-cli\brain\conversation\.system_generated\steps\4\content.md'
            partial=json.dumps({'step_update':{'conversation_id':'c','step_index':12,'step_type':'tool',
                'tool_name':'view_file','tool_info':{'parameters':{'AbsolutePath':internal_path}}}})+'\n'
            observed={}
            class InputSink:
                def write(self,value): observed['provider_input']=value
                def close(self): pass
            class PartialProcess:
                def __init__(self):
                    self.stdin=InputSink();self.stdout=io.BytesIO(partial.encode());self.stderr=io.BytesIO();self.returncode=0
                def poll(self): return self.returncode
                def terminate(self): self.returncode=-15
                def wait(self,timeout=None): return self.returncode
                def kill(self): self.returncode=-9
            def process(command,stdin,stdout,stderr,cwd,bufsize):
                observed['workdir']=Path(cwd)
                return PartialProcess()
            instructions='La skill dice que nunca abras brain/<conversation>/.system_generated.'
            with patch.object(pipeline.subprocess,'Popen',side_effect=process):
                with self.assertRaisesRegex(ValueError,'view_file.*salida parcial conservada y rechazada'):
                    runner.call('agent_retriever',instructions,
                        {'claims':[{'id':'claim'}],'payload':{}},agent='retriever',
                        budget={'allowed_tools':['search_web','read_url_content'],'max_tool_actions':80})
            prefix=root/'.project-intelligence/evidence/view-file-rejected_agent_retriever'
            self.assertNotEqual(observed['workdir'],root)
            self.assertFalse(observed['workdir'].joinpath('GEMINI.md').exists())
            self.assertTrue(prefix.with_suffix('.raw.json').is_file())
            preserved=json.loads(prefix.with_suffix('.raw.json').read_text(encoding='utf-8').splitlines()[0])
            self.assertEqual(preserved['step_update']['tool_info']['parameters']['AbsolutePath'],internal_path)
            self.assertFalse(prefix.with_suffix('.json').exists())

    def test_retriever_tool_policy_names_internal_paths_and_forbidden_file_tools(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(pipeline,'ROOT',Path(temp)), patch.object(pipeline,'INTEL',Path(temp)/'.project-intelligence'):
            (Path(temp)/'GEMINI.md').write_text('project instructions are excluded',encoding='utf-8')
            runner=pipeline.Runner.__new__(pipeline.Runner);runner.run_id='retriever-policy';runner.exe='unused';runner.incremental=True
            observed={}
            envelope={'event':'result','result':{'status':'SUCCESS','response':'[]'}}
            def provider(input_bytes,budget,workdir=None):
                observed.update(prompt=json.loads(input_bytes)['message']['content'],budget=budget,workdir=Path(workdir))
                return 0,(json.dumps(envelope)+'\n').encode(),b'',None
            with patch.object(runner,'_run_incremental',side_effect=provider):
                runner.call('agent_retriever','retriever skill',{'claims':[{'id':'c'}],
                    'payload':{'authorized_documents':[{'document_id':'doc-1','text':'authorized'}]}},
                    agent='retriever',budget={'allowed_tools':['search_web','read_url_content']})
            self.assertEqual(observed['budget']['allowed_tools'],['search_web','read_url_content'])
            self.assertIn('No uses view_file, list_dir, grep_search, sed_file',observed['prompt'])
            self.assertIn('brain/<conversation>/.system_generated/steps/<n>/content.md',observed['prompt'])
            self.assertIn('authorized_documents',observed['prompt'])
            self.assertNotIn('project instructions are excluded',observed['prompt'])
            self.assertNotEqual(observed['workdir'],Path(temp))


if __name__=='__main__':
    unittest.main()
