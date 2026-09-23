import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import workflow_compare as compare

class ComparisonTests(unittest.TestCase):
    def fixture(self):
        return {'question':'Question','approved_claim_ids':['a'],'claims':[{'id':'a','claim':'Claim','status':'UNSUPPORTED','evidence':[]}]}
    def test_missing_observations_are_unknown_not_zero_errors_or_seconds(self):
        data=compare.metrics(self.fixture())
        for key in ('calls_recorded','quality_errors_observed','total_call_seconds_recorded'):
            self.assertIsNone(data[key])
        self.assertEqual(data['critical_reviews_recorded'],1)
        self.assertEqual(data['verified_verdicts_recorded'],0)
    def test_different_question_or_scope_is_rejected(self):
        a=self.fixture();b=copy.deepcopy(a);b['question']='Different'
        with self.assertRaisesRegex(ValueError,'comparación controlada'):compare.compare(a,b)
    def test_receipts_deduplicated_and_missing_duration_is_not_partial_total(self):
        a=self.fixture();r={'run_id':'run','stage':'pass2','status':'failed','elapsed_seconds':2}
        a['receipts']=[r,r];data=compare.metrics(a)
        self.assertEqual(data['calls_recorded'],1);self.assertEqual(data['failed_calls_recorded'],1)
        self.assertEqual(data['total_call_seconds_recorded'],2)
        a['receipts'].append({'run_id':'run','stage':'pass3','status':'provider_completed'})
        self.assertIsNone(compare.metrics(a)['total_call_seconds_recorded'])
