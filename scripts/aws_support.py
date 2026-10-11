"""Use workspace test dependencies when available without changing global Python."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
deps = ROOT / '.test-output' / 'deps'
if deps.exists():
    sys.path.insert(0, str(deps))


def outputs(session, stack):
    return {r['OutputKey']: r['OutputValue'] for r in
            session.client('cloudformation').describe_stacks(StackName=stack)['Stacks'][0]['Outputs']}
