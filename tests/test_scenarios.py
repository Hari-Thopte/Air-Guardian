import json
import unittest
from scripts.export_scenarios import export, ROOT

class ScenarioTests(unittest.TestCase):
    def test_export_is_current_and_engine_driven(self):
        self.assertEqual(json.loads((ROOT/'landing-scenarios.json').read_text(encoding='utf-8')), export())
        for scenario in export()['scenarios']:
            for hour in scenario['hours']:
                self.assertIn(hour['flag'], export()['flags'])
                self.assertEqual(hour['headline'],hour['actions'][0]['text'])
