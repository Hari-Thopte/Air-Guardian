"""Bounded authenticated read load; never publishes plans or sends notifications."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

parser = argparse.ArgumentParser()
parser.add_argument('api')
parser.add_argument('school')
parser.add_argument('--requests', type=int, default=30)
parser.add_argument('--workers', type=int, default=2)
args = parser.parse_args()
if not 1 <= args.requests <= 500 or not 1 <= args.workers <= 10:
    raise SystemExit('Use 1–500 requests and 1–10 workers.')
token = os.environ.get('AG_ACCESS_TOKEN')
if not token:
    raise SystemExit('Set AG_ACCESS_TOKEN privately in your terminal.')
def request(_):
    started = time.monotonic()
    try:
        with urlopen(Request(args.api.rstrip('/') + '/v1/schools/' + args.school + '/workspace',
                             headers={'Authorization': 'Bearer ' + token}), timeout=30) as response:
            code = response.status
            json.load(response)
    except HTTPError as error:
        code = error.code
    except Exception:
        code = 0
    return code, round((time.monotonic() - started) * 1000)
with ThreadPoolExecutor(max_workers=args.workers) as pool:
    results = list(pool.map(request, range(args.requests)))
times = sorted(t for _, t in results)
print(json.dumps({'requests': len(results), 'statuses': {str(c): sum(code == c for code, _ in results) for c, _ in results},
                  'p95Ms': times[min(len(times)-1, int(len(times)*.95))], 'maxMs': max(times)}))
raise SystemExit(int(any(code not in (200, 429) for code, _ in results)))
