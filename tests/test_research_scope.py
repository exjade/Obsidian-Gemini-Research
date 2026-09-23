import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import unittest,tempfile,copy
from unittest.mock import patch
import library as lib
import research_scope as scope

class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for attr,value in [('ROOT',self.root),('BASE',self.root/'library')]:
            p=patch.object(lib,attr,value);p.start();self.addCleanup(p.stop)
        self.folder=lib.case_path('case');self.folder.mkdir(parents=True)
        self.meta={'id':'case','question':'What helps?','status':'completed','tags':[],'title':'Case','claim_ids':['a','b'],'created_at':'2026-01-01'}
        lib.save(self.folder/'case.json',self.meta)
        self.rows=[{'id':i,'claim':'Claim '+i,'investigation_id':'case','category':'architecture','status':'UNSUPPORTED','evidence':[],'hypothesis_source':'candidate origin'} for i in ('a','b')]
        lib.save(self.folder/'claims.json',self.rows)
        lib.save(self.root/'.project-intelligence/claims/architecture.json',self.rows)
        class Runner:
            run_id='separate-review'
            def call(self,stage,instructions,data):
                return [{'id':c['id'],'recommended':n==0,'reason':'Relevant' if n==0 else 'Secondary','answers':'Main question'} for n,c in enumerate(data['candidates'])]
        self.runner=Runner()
    def test_approval_required_and_does_not_change_verdicts(self):
        with self.assertRaisesRegex(ValueError,'Falta aprobar'):scope.admitted(self.meta,self.rows)
        scope.propose('case',self.rows,self.runner)
        with self.assertRaises(ValueError):scope.admitted(lib.read(self.folder/'case.json'),self.rows)
        scope.approve('case',['a'])
        selected=scope.admitted(lib.read(self.folder/'case.json'),self.rows)
        self.assertEqual([c['id'] for c in selected],['a'])
        self.assertEqual(lib.read(self.folder/'claims.json'),self.rows)
        self.assertEqual(len(lib.read(self.folder/'case.json')['scope_history']),2)
    def test_changed_question_claim_or_stale_proposal_blocks_admission(self):
        proposal=scope.propose('case',self.rows,self.runner)
        with self.assertRaises(ValueError):scope.approve('case',['a'],proposal_id='stale')
        with self.assertRaises(ValueError):scope.approve('case',['foreign'])
        scope.approve('case',['a'],proposal_id=proposal['id'])
        meta=lib.read(self.folder/'case.json');meta['question']='Different question'
        with self.assertRaises(ValueError):scope.admitted(meta,self.rows)
        rows=copy.deepcopy(self.rows);rows[0]['claim']='Altered'
        with self.assertRaises(ValueError):scope.admitted(lib.read(self.folder/'case.json'),rows)
    def test_new_scope_review_does_not_silently_remove_candidates(self):
        scope.propose('case',self.rows,self.runner);scope.approve('case',['a'])
        scope.propose('case',self.rows,self.runner)
        meta=lib.read(self.folder/'case.json')
        self.assertEqual([c['id'] for c in scope.admitted(meta,self.rows)],['a'])
        self.assertEqual([c['id'] for c in meta['scope_proposal']['candidates']],['b'])
        self.assertEqual(lib.read(self.folder/'claims.json'),self.rows)
        with self.assertRaises(ValueError):scope.approve('case',['a','a'])
    def test_invented_review_id_does_not_replace_approved_scope(self):
        scope.propose('case',self.rows,self.runner);scope.approve('case',['a'])
        before=lib.read(self.folder/'case.json')
        self.runner.call=lambda *args:[{'id':'fake','recommended':True,'reason':'x','answers':'x'}]
        with self.assertRaises(ValueError):scope.propose('case',self.rows,self.runner)
        self.assertEqual(lib.read(self.folder/'case.json'),before)

    def test_expansion_is_additive_and_preserves_verdicts(self):
        self.rows.extend([{**self.rows[0],'id':i,'claim':'Claim '+i,'status':'VERIFIED',
                           'provenance':[{'run_id':'previous-review'}]} for i in ('c','d','e','f')])
        lib.save(self.folder/'claims.json',self.rows)
        lib.save(self.root/'.project-intelligence/claims/architecture.json',self.rows)
        scope.propose('case',self.rows,self.runner);scope.approve('case',['a','b','c'])
        before=copy.deepcopy(self.rows)
        proposal=scope.propose('case',self.rows,self.runner)
        self.assertEqual({c['id'] for c in proposal['candidates']},{'d','e','f'})
        approved=scope.approve('case',['d','e','f'],reason='New questions',proposal_id=proposal['id'])
        self.assertEqual(approved['selected_ids'],['a','b','c','d','e','f'])
        self.assertEqual(approved['added_ids'],['d','e','f'])
        self.assertEqual(lib.read(self.folder/'claims.json'),before)
        self.assertEqual(len(scope.admitted(lib.read(self.folder/'case.json'),self.rows)),6)
        self.assertEqual(len(lib.read(self.folder/'case.json')['scope_history']),4)
        with self.assertRaisesRegex(ValueError,'No hay propuestas adicionales'):scope.propose('case',self.rows,self.runner)

    def test_cancel_expansion_preserves_scope_and_history(self):
        scope.propose('case',self.rows,self.runner);scope.approve('case',['a'])
        original=lib.read(self.folder/'case.json')['scope']
        proposal=scope.propose('case',self.rows,self.runner)
        with self.assertRaises(ValueError):scope.cancel_expansion('case','stale','Later')
        scope.cancel_expansion('case',proposal['id'],'Not relevant yet')
        meta=lib.read(self.folder/'case.json')
        self.assertEqual(meta['scope'],original);self.assertNotIn('scope_proposal',meta)
        self.assertEqual(meta['scope_history'][-1]['status'],'cancelled')
        self.assertEqual(lib.read(self.folder/'claims.json'),self.rows)

    def test_expansion_rejects_changes_to_original_hypotheses(self):
        scope.propose('case',self.rows,self.runner);scope.approve('case',['a'])
        proposal=scope.propose('case',self.rows,self.runner)
        altered=copy.deepcopy(self.rows);altered[0]['claim']='Different'
        lib.save(self.folder/'claims.json',altered)
        with self.assertRaises(ValueError):scope.approve('case',['b'],proposal_id=proposal['id'])
        self.assertEqual(lib.read(self.folder/'case.json')['scope']['selected_ids'],['a'])

    def test_user_candidate_is_unverified_and_does_not_change_admission(self):
        scope.propose('case',self.rows,self.runner);scope.approve('case',['a'])
        original=lib.read(self.folder/'case.json')['scope']
        candidate=scope.add_candidate('case','A new testable hypothesis','It addresses another part of the question')
        meta=lib.read(self.folder/'case.json');rows=lib.read(self.folder/'claims.json')
        self.assertEqual(meta['scope'],original);self.assertEqual(candidate['status'],'UNVERIFIED')
        self.assertEqual([c['id'] for c in scope.admitted(meta,rows)],['a'])
        self.assertEqual(rows[:2],self.rows)
        with self.assertRaises(ValueError):scope.add_candidate('case',candidate['claim'],'Duplicate')

if __name__=='__main__':unittest.main()
