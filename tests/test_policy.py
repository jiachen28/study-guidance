import unittest
from app.policy import assess,baseline,TOOL_TYPES,LABELS
from app.study import read_csv

class PolicyTests(unittest.TestCase):
    def test_categories_are_distinct(self):
        self.assertEqual(set(TOOL_TYPES),set(LABELS))
    def test_programming(self):
        self.assertEqual(baseline('Debug my Django Python function and run unit tests'),'Coding')
    def test_research(self):
        self.assertEqual(baseline('Search academic literature and validate sources'),'Research')
    def test_team_workflow(self):
        self.assertEqual(baseline('Coordinate a team project meeting and schedule'),'Workflow')
    def test_unknown_baseline(self):
        self.assertEqual(baseline('What next?'),'None')
    def test_restricted_exam(self):
        self.assertTrue(assess('A closed-book exam explicitly prohibits AI use. Can I use it?').prohibited)
    def test_publishing_secrets(self):
        self.assertTrue(assess('Can I upload a private student medical record?').prohibited)
    def test_allowed_code_with_privacy_note(self):
        x=assess('I need to debug code but cannot share my password.')
        self.assertFalse(x.prohibited)
        self.assertEqual(x.level,'Review required')
    def test_review_only_input(self):
        self.assertFalse(assess('How can I verify citations without using AI?').prohibited)
    def test_representative_restricted_scenarios(self):
        rows={s['id']:s['task'] for s in read_csv('data/scenarios.csv')}
        for id in ['S04','S16','S20','S36','S40','S44','S48','S52','S56','S60']:
            with self.subTest(id=id):self.assertTrue(assess(rows[id]).prohibited)
