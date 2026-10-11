#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/package_cloud.py
sam validate --lint --template-file template.yaml
sam build --use-container --template-file template.yaml
sam deploy --guided --stack-name "${1:-air-guardian-pilot}" --region ap-south-1
