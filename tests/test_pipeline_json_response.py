import sys
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


if __name__=='__main__':
    unittest.main()
