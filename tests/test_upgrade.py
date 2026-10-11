import unittest
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo
import test_cloud
from cloud.planning_tools import stabilize, cleanest_windows
from cloud.store import change
from cloud.contracts import Problem
from backend.functions.air_engine import iso
from backend.functions.guardian_rules import child_risk


class PlanningUpgradeTests(unittest.TestCase):
    def test_recovery_needs_distinct_consecutive_hours_and_no_flapping(self):
        state = stabilize(None, 'orange', 36000, 45)
        state = stabilize(state, 'yellow', 39600, 25)
        self.assertEqual(state['flag'], 'orange')
        state = stabilize(state, 'yellow', 39601, 25)
        self.assertEqual(state['count'], 1)
        state = stabilize(state, 'orange', 43200, 45)
        state = stabilize(state, 'yellow', 46800, 25)
        self.assertEqual(state['flag'], 'orange')
        self.assertEqual(stabilize(state, 'yellow', 50400, 25)['flag'], 'yellow')
        self.assertEqual(stabilize(state, 'red', 50400, 110)['flag'], 'red')

    def test_missing_hours_and_unknown_break_recovery(self):
        state = stabilize(None, 'red', 36000, 110)
        state = stabilize(state, 'green', 39600, 8)
        self.assertEqual(stabilize(state, 'green', 46800, 8)['flag'], 'red')
        self.assertEqual(stabilize(state, 'unknown', None, None)['flag'], 'unknown')

    def test_boundaries_and_monotonic_concentration(self):
        ranks = ['green', 'yellow', 'orange', 'red']
        for age in ['5-8', '9-12', '13-17']:
            values = [0, 15, 15.001, 20, 25, 35, 35.001, 40, 50, 60, 60.001, 75, 90, 90.001, 120, 500]
            flags = [ranks.index(child_risk({'aqi': 1, 'pm25': pm}, age)['flag']) for pm in values]
            self.assertEqual(flags, sorted(flags))

    def test_cleaner_slot_requires_complete_fresh_forecast(self):
        now = datetime(2026, 10, 11, 7, tzinfo=ZoneInfo('Asia/Kolkata')).timestamp()
        points = [{'time': iso(now + h * 3600), 'pm25': 90 if h < 5 else 20} for h in range(10)]
        air = {'pm25': 90, 'observedAt': iso(now), 'forecast': points}
        config = {'timezone': 'Asia/Kolkata'}
        windows = cleanest_windows(air, config, now)
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0]['suggested'], '12:00')
        self.assertLess(windows[0]['suggestedPm25'], windows[0]['originalPm25'])
        self.assertEqual(cleanest_windows(dict(air, stale=True), config, now), [])
        self.assertEqual(cleanest_windows(dict(air, forecast=[]), config, now), [])


class KidPrivacyTests(unittest.TestCase):
    setUp = test_cloud.WorkflowTests.setUp
    call = test_cloud.WorkflowTests.call

    def prepare(self):
        self.store.commit([change('SCHOOL#a', 'MEMBER#explorer', {'sub':'explorer','school':'a','role':'kid','active':True})])

    def test_kid_allowlist_contains_no_personal_records_or_arbitrary_adult_note(self):
        self.prepare()
        result = self.call('workspace', sub='explorer', method='GET')
        self.assertEqual(set(result), {'school','membership','kid'})
        self.assertEqual(result['kid']['actionCode'], 'verify')
        self.assertNotIn('children', result)

    def test_kid_cannot_read_history_or_mutate_any_school_action(self):
        self.prepare()
        for action in ['history','operations','health']:
            with self.assertRaises(Problem):
                self.call(action, sub='explorer', method='GET')
        for action in ['review','announce','checklist','preferences','profile','remind']:
            with self.assertRaises(Problem):
                self.call(action, {}, sub='explorer')


class RoundSafetyTests(unittest.TestCase):
    setUp = test_cloud.WorkflowTests.setUp
    call = test_cloud.WorkflowTests.call

    def test_request_limit_is_per_identity_and_window(self):
        from cloud.rate_limit import reserve
        for _ in range(5):
            reserve(self.store, 'admin', 'notification')
        with self.assertRaises(Problem) as error:
            reserve(self.store, 'admin', 'notification')
        self.assertEqual(error.exception.status, 429)
        reserve(self.store, 'other-admin', 'notification')

    def test_override_requires_admin_and_reason_and_is_audited(self):
        with self.assertRaises(Problem):
            self.call('schedule-decision', {'decision':'keep-outdoors','reason':'short'})
        with self.assertRaises(Problem):
            self.call('schedule-decision', {'decision':'keep-outdoors','reason':'Review room conditions first'},sub='parent')
        self.call('schedule-decision', {'decision':'keep-outdoors','reason':'Review room conditions first'})
        self.assertTrue(self.store.query('SCHOOL#a','DECISION#'))
        self.assertTrue(self.store.query('SCHOOL#a','AUDIT#'))

    def test_deadline_reminder_is_once_per_day_and_excludes_reviewed(self):
        from cloud.deadline import nudge_changes
        now=datetime(2026,10,11,8,5,tzinfo=ZoneInfo('Asia/Kolkata')).timestamp()
        self.store.commit([change('SCHOOL#a','NOTICE',{'id':'n','flag':'orange','expiresAt':now+3600,'audience':[{'sub':'parent','role':'parent'},{'sub':'staff','role':'staff'}]}),change('SCHOOL#a','RECEIPT#n#parent',{'sub':'parent'})])
        changes=nudge_changes(self.store,self.school,{'flag':'orange'},now)
        self.assertTrue(changes)
        event=next(c['value'] for c in changes if c['sk'].startswith('EVENT#'))
        self.assertEqual([p['sub'] for p in event['audience']],['staff'])
        self.store.commit(changes)
        self.assertEqual(nudge_changes(self.store,self.school,{'flag':'orange'},now+60),[])
