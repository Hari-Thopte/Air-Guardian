"""Loopback frontend for actual AWS backend. No fixture engine or preview role identities."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=5191)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1] / 'dist'
if not (root / 'cloud-config.js').exists():
    raise SystemExit('Generate deployed frontend configuration first.')
print(f'Local frontend connected to configured AWS services: http://localhost:{args.port}/cloud.html', flush=True)
print('This frontend is not publicly hosted. Cognito authentication and AWS membership checks apply.', flush=True)
ThreadingHTTPServer(('127.0.0.1', args.port), partial(SimpleHTTPRequestHandler, directory=str(root))).serve_forever()
