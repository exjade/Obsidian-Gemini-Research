import copy
import json
import unittest
from unittest.mock import patch
import test_revisions as fixtures
import pipeline as p
import collector_checkpoint as checkpoint

class CollectorResumeTests(unittest.TestCase):
    setUp=fixtures.ReviewTests.setUp
    tearDown=fixtures.ReviewTests.tearDown
    def candidate(self):return {**self.rows[0],'status':'UNVERIFIED','risk_policy':None}
    def failed_skeptic(self,context=None):
        self.fail_stage='pass3'
        with self.assertRaises(ValueError):p.evaluate(self.runner(),[self.candidate()],context or {'fixture':1})
        self.fail_stage=None
    def test_retry_reuses_collector_and_preserves_origin(self):
        self.failed_skeptic();self.seen.clear()
        reviewed=p.evaluate(self.runner(),[self.candidate()],{'fixture':1})[0]
        self.assertEqual([s for s,_ in self.seen],['pass3'])
        self.assertTrue(reviewed['provenance'][-1]['collector_reused'])
        self.assertIn('fixture-run_pass2',reviewed['provenance'][-1]['collector_result'])
        self.assertEqual(p.all_claims()[0]['status'],'UNSUPPORTED')
    def test_changed_context_does_not_reuse(self):
        self.failed_skeptic();self.seen.clear()
        p.evaluate(self.runner(),[self.candidate()],{'fixture':2})
        self.assertEqual([s for s,_ in self.seen],['pass2','pass3'])
    def test_changed_source_file_invalidates_even_if_excerpt_still_matches(self):
        self.failed_skeptic();self.seen.clear()
        (self.root/'src/proof.txt').write_text('fixture proof\nnew context\n')
        p.evaluate(self.runner(),[self.candidate()],{'fixture':1})
        self.assertEqual(self.seen[0][0],'pass2')
    def test_corrupted_and_expired_checkpoint_invalidated(self):
        for kind in ['corrupt','expire']:
            self.failed_skeptic()
            path=next((p.INTEL/'collector-checkpoints').glob('*.json'))
            data=json.loads(path.read_text())
            if kind=='corrupt':data['result'][0]['claim']='wrong text'
            else:data['created_at']='2000-01-01T00:00:00+00:00'
            path.write_text(json.dumps(data));self.seen.clear()
            p.evaluate(self.runner(),[self.candidate()],{'fixture':1})
            self.assertEqual(self.seen[0][0],'pass2')
    def test_collector_partial_failure_never_becomes_checkpoint(self):
        self.fail_stage='pass2'
        with self.assertRaises(ValueError):p.evaluate(self.runner(),[self.candidate()],{})
        self.assertFalse((p.INTEL/'collector-checkpoints').exists())
    def test_contract_and_policy_invalidate(self):
        self.failed_skeptic();self.seen.clear()
        (self.root/'GEMINI.md').write_text('changed contract')
        p.evaluate(self.runner(),[self.candidate()],{'fixture':1})
        self.assertEqual(self.seen[0][0],'pass2')
        self.failed_skeptic();self.seen.clear()
        with patch.object(p,'RISK_POLICY','changed-policy'):
            p.evaluate(self.runner(),[self.candidate()],{'fixture':1})
        self.assertEqual(self.seen[0][0],'pass2')
    def test_retry_progress_names_pending_and_preserved_review(self):
        rows=[self.rows[0],{**self.rows[1],'status':'UNVERIFIED','risk_policy':None}]
        labels=[]
        base=self.runner
        class Capture(base):
            def call(inner,stage,instructions,data):
                labels.append(inner.progress_label)
                return super().call(stage,instructions,data)
        with patch.object(p,'Runner',Capture):p.evaluate_incrementally(rows,[rows[1]],{})
        self.assertIn('Pendiente 1 de 1',labels[0])
        self.assertIn('alcance: 2',labels[0])
        self.assertIn('conservadas: 1',labels[0])

if __name__=='__main__':unittest.main()
