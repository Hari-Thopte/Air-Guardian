import unittest
from cloud.store import MemoryStore, change
from cloud.contracts import school
from cloud.api import workspace
from scripts.demo_scenario import select_scenario


class IndependentScenarioTests(unittest.TestCase):
    def test_every_role_recomputes_from_isolated_fixture(self):
        config = school({'id':'fixture','name':'Example school','lat':28.6,'lon':77.2})
        store, readings = MemoryStore(), MemoryStore()
        store.commit([change('SCHOOL#fixture','CONFIG',config)])
        for scenario, flag, code in [('red','red','indoor-pe'),('green','green','usual'),
                                     ('yellow','yellow','gentle'),('orange','orange','indoor-pe'),
                                     ('stale','unknown','verify')]:
            select_scenario(store,readings,config,scenario)
            current = store.get('SCHOOL#fixture','CURRENT')
            self.assertNotIn('stability',current)
            self.assertIsNone(store.get('SCHOOL#fixture','NOTICE'))
            self.assertEqual(readings.rows,{})
            for role in ['admin','teacher','parent','staff','kid']:
                w = workspace(store,'fixture',{'role':role,'sub':role})
                actual = w['kid'] if role=='kid' else w['planning']
                self.assertEqual(actual['flag'],flag,(scenario,role))
                self.assertEqual(actual['actionCode'] if role=='kid' else actual['actions'][0]['id'],code)

    def test_manual_fixture_clears_cached_history_and_override(self):
        store, readings = MemoryStore(), MemoryStore()
        config = school({'id':'fixture','name':'Example','lat':28.6,'lon':77.2})
        for key in ['CURRENT','ALERTSTATE','NOTICE','DECISION#1','RECEIPT#1','TASK#1']:
            store.commit([change('SCHOOL#fixture',key,{'stability':{'flag':'red'}})])
        readings.commit([change('SCHOOL#fixture#today','READING#1',{'pm25':150})])
        select_scenario(store,readings,config,'green')
        self.assertEqual(set(store.rows),{('SCHOOL#fixture','CURRENT')})
