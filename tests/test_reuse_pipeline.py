import copy
import unittest
from unittest.mock import patch
import test_revisions as fixtures
import pipeline as p

class ReusePipelineTests(unittest.TestCase):
    setUp=fixtures.ReviewTests.setUp
    tearDown=fixtures.ReviewTests.tearDown
    def test_candidate_origin_reaches_skeptic_and_blocked_source_does_not_transfer_verdict(self):
        test=self
        proposal={'candidate_id':'candidate','origin_case_id':'old-case','origin_claim_id':'old-claim',
                  'origin_evidence_index':0,'target_claim_id':'target','url':'https://example.invalid/paper','excerpt':'Recorded passage'}
        class Runner:
            run_id='reuse-test'
            def call(self,stage,instructions,data):
                test.seen.append((stage,copy.deepcopy(data)))
                if stage=='pass2':
                    test.assertEqual(data['cross_case_candidates'],[proposal])
                    return [{'id':'target','claim':data['claims'][0]['claim'],'status':'UNVERIFIED',
                             'evidence':[{'type':'external','url':proposal['url'],'excerpt':proposal['excerpt'],
                                          'searched':True,'fetched':True,'retrieved_at':'2026-01-01T00:00:00Z'}]}]
                test.assertEqual(data[0]['evidence'][0]['reuse_origins'][0]['origin_case_id'],'old-case')
                data[0]['evidence'][0]['reuse_relevance']={'target_claim_id':'target','decision':'context','reason':'Different comparison','limits':'Does not support entire claim'}
                return [{**data[0],'status':'VERIFIED','domain':'general','sensible':False,'favorable':False,
                         'skeptic_note':'Relevance reviewed for current claim','contradiction_search':'Checked','primary_sources':[]}]
        with patch.object(p.evidence_reuse,'candidates',return_value=[proposal]),patch.object(p.source_check,'record_check',return_value={'id':'blocked'}):
            result=p.evaluate(Runner(),[self.rows[0]])[0]
        self.assertEqual(result['status'],'UNSUPPORTED')
        self.assertEqual(result['evidence'][0]['relation'],'context')
        self.assertEqual(result['evidence'][0]['reuse_relevance']['target_claim_id'],'target')
        self.assertEqual(result['evidence'][0]['reuse_origins'][0]['origin_claim_id'],'old-claim')
        self.assertIn('reuse_candidates_manifest',result['provenance'][-1])
        self.assertEqual(p.all_claims(),self.rows)
