import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import pipeline as p

class ExecutionReceiptTests(unittest.TestCase):
    def test_real_wrapper_records_provider_call_not_truth(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(p,'INTEL',Path(temp)):
            runner=p.Runner.__new__(p.Runner);runner.run_id='fixture'
            with patch.object(p.Runner,'_call',return_value=[]),patch('time.monotonic',side_effect=[10,12.5]):
                runner.call('pass3','fixture',[{'id':'a'}])
            receipt=json.loads((Path(temp)/'execution-receipts/fixture_pass3.json').read_text())
            self.assertEqual(receipt['elapsed_seconds'],2.5)
            self.assertEqual(receipt['claim_ids'],['a'])
            self.assertEqual(receipt['status'],'provider_completed')
            self.assertNotIn('VERIFIED',json.dumps(receipt))
    def test_failed_call_retains_timing_and_error(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(p,'INTEL',Path(temp)):
            runner=p.Runner.__new__(p.Runner);runner.run_id='fixture'
            with patch.object(p.Runner,'_call',side_effect=ValueError('provider timeout')):
                with self.assertRaises(ValueError):runner.call('pass2','fixture',{'claims':[{'id':'a'}]})
            receipt=json.loads((Path(temp)/'execution-receipts/fixture_pass2.json').read_text())
            self.assertEqual(receipt['status'],'failed');self.assertIn('timeout',receipt['error'])
            self.assertGreaterEqual(receipt['elapsed_seconds'],0)
            self.assertTrue(receipt['started_at']);self.assertTrue(receipt['finished_at'])

if __name__=='__main__':unittest.main()
