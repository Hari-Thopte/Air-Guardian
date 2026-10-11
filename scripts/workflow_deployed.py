"""Role-specific deployed checks. --publish writes a test plan in the designated pilot school."""
import argparse
import json
import os
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError

parser = argparse.ArgumentParser()
parser.add_argument('api')
parser.add_argument('school')
parser.add_argument('--other-school', required=True, help='Existing school none of the test users belongs to')
parser.add_argument('--publish', action='store_true', help='Publish and acknowledge a clearly labeled test plan')
args = parser.parse_args()
tokens = {r: os.environ.get('AG_' + r.upper() + '_TOKEN') for r in ('admin', 'teacher', 'parent')}
if not all(tokens.values()):
    raise SystemExit('Set AG_ADMIN_TOKEN, AG_TEACHER_TOKEN and AG_PARENT_TOKEN privately; never paste them into chat.')
def call(role, path, data=None):
    req = Request(args.api.rstrip('/') + path, headers={'Authorization': 'Bearer ' + tokens[role], 'Content-Type': 'application/json'},
                  data=None if data is None else json.dumps(data).encode(), method='GET' if data is None else 'POST')
    with urlopen(req, timeout=30) as response:
        return json.load(response)
prefix = '/v1/schools/' + args.school + '/'
for role in tokens:
    workspace = call(role, prefix + 'workspace')
    if workspace['membership']['role'] != role:
        raise SystemExit('Wrong test token role: ' + role)
    try:
        call(role, '/v1/schools/' + args.other_school + '/workspace')
    except HTTPError as error:
        if error.code != 403:
            raise SystemExit('Cross-school denial returned unexpected status: ' + str(error.code))
    else:
        raise SystemExit('FAIL: cross-school records accessible by ' + role)
    print('PASS:', role, 'workspace and cross-school denial')
if args.publish:
    event = call('admin', prefix + 'announce', {'note': 'Operator verification plan — fictional test participants only.',
                  'requestId': 'verify-' + str(uuid.uuid4())})['event']
    call('teacher', prefix + 'acknowledge', {'eventId': event['id'], 'checks': [True, True, True], 'minutesMoved': 0})
    call('parent', prefix + 'review', {'eventId': event['id']})
    workspace = call('admin', prefix + 'workspace')
    if not {'acknowledge', 'review'}.issubset({r['kind'] for r in workspace['receipts']}):
        raise SystemExit('FAIL: workflow receipts missing')
    print('PASS: deployed publication → teacher acknowledgment → parent review')
