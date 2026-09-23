from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from research_closure import guidance

class GuidanceTests(unittest.TestCase):
    def test_plan_is_not_reported_as_executed_or_mandatory_manual_audit(self):
        row=guidance({'owner':'sistema','reason':'Pending'})
        self.assertEqual(row['attempt_state'],'available_on_reevaluation')
        self.assertIn('No necesitas auditar',row['help_needed'])
        self.assertTrue(row['why_it_matters'])
        self.assertTrue(any('todavía no disponible' in step for step in row['system_attempts']))
    def test_user_controls_scope_while_system_conserves_prior_work(self):
        row=guidance({'owner':'usuario','reason':'Scope'})
        self.assertEqual(row['attempt_state'],'awaiting_scope_decision')
        self.assertIn('Tu decisión',row['help_needed'])
        self.assertIn('Conservar',row['system_attempts'][0])
