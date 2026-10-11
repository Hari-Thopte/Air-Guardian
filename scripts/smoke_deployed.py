"""Account operator supplies a short-lived access token via environment, never CLI/logs."""
import argparse
import os
import urllib.request
import json

parser=argparse.ArgumentParser()
parser.add_argument('api')
parser.add_argument('school')
args=parser.parse_args()
token=os.environ.get('AG_ACCESS_TOKEN')
if not token:
    raise SystemExit('FAIL: set AG_ACCESS_TOKEN to your Cognito access token')
failed=False
for route in ['health','workspace']:
    try:
        request=urllib.request.Request(args.api.rstrip('/')+'/v1/schools/'+args.school+'/'+route,headers={'Authorization':'Bearer '+token})
        with urllib.request.urlopen(request,timeout=15) as response:
            data=json.load(response)
        assert isinstance(data,dict) and ('health' if route=='health' else 'planning') in data
        print('PASS:',route)
    except Exception as error:
        print('FAIL:',route,type(error).__name__)
        failed=True
raise SystemExit(int(failed))
