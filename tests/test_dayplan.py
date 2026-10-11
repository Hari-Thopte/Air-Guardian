import unittest
import test_cloud
from cloud.dayplan import validate_blocks, timetable
from cloud.contracts import Problem
from cloud.dayplan import health, outdoor_summary, morning_brief
from backend.functions.air_engine import iso
from cloud.store import change
from cloud.contracts import DEFAULT_PREFS, local_day


class DayPlanTests(unittest.TestCase):
    setUp = test_cloud.WorkflowTests.setUp
    call = test_cloud.WorkflowTests.call
    # Reuse the workflow fixture, not its suite.
    def test_publication_receipts_are_unique_and_private(self):
        event = self.call('announce', {'note': 'Review the indoor room.', 'requestId': 'day-plan'})['event']
        self.assertEqual(len(event['audience']), 5)
        for role in ('parent', 'staff', 'teacher'):
            self.call('review', {'eventId': event['id']}, sub=role)
            self.call('review', {'eventId': event['id']}, sub=role)
            w = self.call('workspace', sub=role, method='GET')
            self.assertNotIn('audience', w['notice'])
            self.assertIsNone(w['receiptSummary'])
        w = self.call('workspace', method='GET')
        self.assertEqual(w['receiptSummary']['confirmed'], 3)
        self.assertEqual(w['receiptSummary']['total'], 5)

    def test_timetable_rejects_overlap_and_uses_engine(self):
        with self.assertRaises(Problem):
            validate_blocks([{'name':'PE','start':'09:00','end':'08:00','outdoors':True}])
        w = self.call('workspace', method='GET')
        blocks = w['dayPlan']['timetable']
        self.assertEqual(sum(b['minutes'] for b in blocks), 85)
        self.assertEqual(blocks[0]['actionId'], 'indoor-pe')

    def test_freshness_and_outdoor_minutes_follow_existing_policy(self):
        self.assertEqual(health(self.air,self.now+3601)['status'],'Getting old')
        self.assertEqual(health(self.air,self.now+7201)['status'],'Stale')
        self.assertEqual(health({},self.now)['status'],'Unavailable')
        w=self.call('workspace',method='GET')
        self.assertEqual(w['outdoorSummary']['before'],85)
        self.assertEqual(w['outdoorSummary']['after'],35)
        self.assertFalse(w['morningBrief']['available'])

    def test_reminder_excludes_reviewed_and_respects_cap_and_quiet(self):
        self.call('announce',{'note':'Reviewed plan','requestId':'plan'})
        self.call('review',{'eventId':'plan'},sub='parent')
        for sub in ['admin','teacher','staff','other-parent']:
            self.store.commit([change('USER#'+sub,'PREFERENCES',dict(DEFAULT_PREFS,quietStart='00:00',quietEnd='00:00'))])
        result=self.call('remind',{'requestId':'reminder'})
        self.assertEqual(result['queued'],4)
        event=self.store.get('OUTBOX','a#reminder')['event']
        self.assertNotIn('parent',[p['sub'] for p in event['audience']])
        self.store.commit([change('USER#staff',f'CAP#a#{local_day(self.school)}#in-app',{'count':4})])
        with self.assertRaises(Problem): self.call('remind',{'requestId':'capped'})
        self.store.commit([change('USER#staff','PREFERENCES',dict(DEFAULT_PREFS,quietStart='00:00',quietEnd='23:59'),self.store.get('USER#staff','PREFERENCES'))])
        with self.assertRaises(Problem): self.call('remind',{'requestId':'quiet'})
        with self.assertRaises(Problem): self.call('remind',{'requestId':'forged'},sub='parent')

    def test_checklist_only_assigned_role_can_confirm(self):
        self.call('announce',{'note':'Reviewed plan','requestId':'tasks'})
        with self.assertRaises(Problem): self.call('checklist',{'eventId':'tasks','taskId':'indoor-pe'},sub='staff')
        self.call('checklist',{'eventId':'tasks','taskId':'indoor-pe'},sub='teacher')
        self.call('checklist',{'eventId':'tasks','taskId':'indoor-pe'},sub='teacher')
        teacher=self.call('workspace',method='GET',sub='teacher')
        self.assertEqual(len(teacher['completions']),1)
        parent=self.call('workspace',method='GET',sub='parent')
        self.assertEqual(parent['completions'],[])

    def test_seed_is_idempotent_and_history_has_honest_gaps(self):
        from scripts.seed_demo import seed
        first=seed(self.store,self.readings,self.school,self.now)
        second=seed(self.store,self.readings,self.school,self.now)
        self.assertGreater(first['created'],100)
        self.assertEqual(second['created'],0)
        w=self.call('workspace',method='GET')
        self.assertGreaterEqual(len(w['classes']),3)
        result=self.call('operations',method='GET')
        self.assertEqual(len(result['plans']),2)
        self.assertIsNotNone(result['weekly']['medianSecondsToReview'])
        staff=self.call('workspace',method='GET',sub='staff')
        self.assertEqual(staff['children'],[])
        with self.assertRaises(Problem):self.call('operations',method='GET',sub='parent')

    def test_school_day_save_persists_and_rejects_invalid_input(self):
        blocks=[{'name':'PE','start':'10:00','end':'10:45','outdoors':True}]
        self.call('school',{'timetable':blocks})
        self.assertEqual(self.call('workspace',method='GET')['dayPlan']['timetable'][0]['minutes'],45)
        with self.assertRaises(Problem):self.call('school',{'timetable':[dict(blocks[0],end='09:00')]})

