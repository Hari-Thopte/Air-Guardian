"""Read-only forecast comparison. Does not train or deploy an unvalidated model."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloud.store import DynamoStore
from cloud.pipeline import history
from cloud.forecast import evaluate

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--table', required=True)
    parser.add_argument('--school', required=True)
    parser.add_argument('--region', default='ap-south-1')
    args = parser.parse_args()
    os.environ['AWS_DEFAULT_REGION'] = args.region
    store = DynamoStore(args.table)
    actuals = history(store, args.school, 30)['readings']
    forecasts = store.query('SCHOOL#' + args.school, 'FORECAST#', limit=1000)
    print(json.dumps({'evaluation': evaluate(forecasts, actuals),
                      'note': 'Empty results mean no matched measured targets. Modeled observations are not ground truth.'}, indent=2))
