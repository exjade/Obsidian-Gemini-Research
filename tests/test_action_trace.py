import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_trace
import library


class TraceTests(unittest.TestCase):
    def test_reused_collector_has_original_actions_and_observed_attribution(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'.project-intelligence/evidence';folder.mkdir(parents=True)
            event={'step_update':{'step_index':1,'conversation_id':'c','step_type':'tool','state':'DONE','tool_name':'search_web','tool_info':{'parameters':{'query':'original'}}}}
            (folder/'previous_pass2.raw.json').write_text(json.dumps(event))
            (folder/'previous_pass2.input.json').write_text(json.dumps({'message':{'content':'contract\n\nDATOS:\n'+json.dumps({'claims':[{'id':'a'}]})}}))
            claim={'id':'a','provenance':[{'run_id':'current','collector_result':'evidence/previous_pass2.json','skeptic_result':'evidence/current_pass3.json'}]}
            rows=action_trace.for_claim(root,claim)
            self.assertEqual(len(rows),1);self.assertTrue(rows[0]['reused']);self.assertEqual(rows[0]['run_id'],'previous')
            self.assertEqual(rows[0]['attribution'],'single_claim')
            (folder/'previous_pass2.input.json').write_text(json.dumps({'message':{'content':'contract\n\nDATOS:\n'+json.dumps({'claims':[{'id':'a'},{'id':'b'}]})}}))
            self.assertEqual(action_trace.for_claim(root,claim)[0]['attribution'],'batch')
            claim['provenance'][0]['collector_result']='evidence/../../outside_pass2.json'
            self.assertEqual(action_trace.for_claim(root,claim),[])

    def test_only_observed_tools_latest_run_and_no_reasoning(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'.project-intelligence/evidence';folder.mkdir(parents=True)
            events=[{'event':'step_update','step_update':{'step_index':1,'conversation_id':'c','step_type':'thinking','text_delta':'PRIVATE REASONING'}},
                    {'event':'step_update','step_update':{'step_index':2,'conversation_id':'c','step_type':'tool','state':'ACTIVE','tool_name':'search_web','tool_info':{'parameters':{'query':'observed query','secret':'EXCLUDED'}}}},
                    {'event':'step_update','step_update':{'step_index':2,'conversation_id':'c','step_type':'tool','state':'DONE'}}]
            (folder/'new_pass2.raw.json').write_text('\n'.join(json.dumps(e) for e in events),encoding='utf-8')
            (folder/'old_pass2.raw.json').write_text(json.dumps(events[1]),encoding='utf-8')
            rows=action_trace.for_claim(root,{'provenance':[{'run_id':'old'},{'run_id':'new'}]})
            self.assertEqual(len(rows),1);self.assertEqual(rows[0]['state'],'DONE');self.assertEqual(rows[0]['target'],'observed query')
            self.assertNotIn('PRIVATE',json.dumps(rows));self.assertNotIn('EXCLUDED',json.dumps(rows))
            self.assertEqual(action_trace.for_claim(root,{'provenance':[{'run_id':'../outside'}]}),[])

    def test_unreadable_partial_events_do_not_fabricate_actions(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'.project-intelligence/evidence';folder.mkdir(parents=True)
            (folder/'new_pass2.raw.json').write_text('null\n{"event":"result"}\n{broken',encoding='utf-8')
            self.assertEqual(action_trace.for_claim(root,{'provenance':[{'run_id':'new'}]}),[])

    def test_verified_external_without_receipt_stays_pending(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(library,'ROOT',Path(temp)):
            self.assertTrue(library.needs_review({'status':'VERIFIED','evidence':[{'type':'external','url':'https://example.com','excerpt':'claim passage'}]}))
            self.assertTrue(library.needs_review({'status':'UNSUPPORTED','evidence':[]}))
            self.assertFalse(library.needs_review({'status':'VERIFIED','evidence':[{'type':'file','path':'src/file'}]}))


if __name__=='__main__':unittest.main()
