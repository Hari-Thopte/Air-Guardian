import json
import unittest
from types import SimpleNamespace
from cloud.local_engine import handler


class LocalEngineTests(unittest.TestCase):
    def test_real_powertools_dispatches_the_lambda_event(self):
        event={'httpMethod':'GET','path':'/engine','headers':{},'queryStringParameters':None,
               'requestContext':{'stage':'local','requestId':'test'},'body':None,'isBase64Encoded':False}
        context=SimpleNamespace(function_name='local-engine',memory_limit_in_mb=256,
                                invoked_function_arn='local-only',aws_request_id='test')
        result=handler(event,context)
        self.assertEqual(result['statusCode'],200)
        body=json.loads(result['body'])
        self.assertIn('Powertools',body['awsOpenSource'])
        self.assertEqual(body['planning']['flag'],'red')
        self.assertEqual(len(body['dayPlan']['timetable']),4)
