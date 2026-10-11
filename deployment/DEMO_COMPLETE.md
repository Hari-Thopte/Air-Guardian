# Completed AWS demo — 11 October 2026

The requested minimal demo is verified. This is not a claim of full production readiness.

## Open the real dashboard

From the project directory, run:

```powershell
python scripts/serve_deployed.py --port 5191
```

Open http://localhost:5191/cloud.html and sign in using your Cognito account. The server must stay running; this URL is local to this computer, not public hosting. CloudFront is still blocked by AWS account verification, which is outside this demo's accepted scope.

## Verified demonstration

1. Real Cognito OAuth login completed in the browser. The verified account for harshikathopte@gmail.com has active authenticator MFA and administrator membership for St. Xaviers School, Manickpur. No demo-role headers or operator-generated JWTs were used for the browser.
2. The deployed ARM64 ingestion Lambda fetched Open-Meteo/CAMS data and persisted current/history records in real DynamoDB. At source time 21:30 IST on 11 October, PM2.5 was 46.7 µg/m³ and PM10 was 50.6 µg/m³. The authenticated dashboard displayed the matching 46.7 reading, source timestamp, successful retrieval and fresh status. These are regional model estimates, not measured school sensors. Data will change on refresh.
3. A real SQS notification event was consumed by the deployed delivery Lambda, which wrote a durable in-app receipt to DynamoDB. Message ID: `c8ae4dc2-f3ea-4071-86fa-2226e2f08953`. Event ID: `aws-demo-c16f1717-e38d-4e5b-9c29-e0e96c9bf7dc`. The portal's Notifications → Refresh → School send log displayed the admin / in-app / in-app result at 21:42 IST. Only the administrator was targeted; no SMS, WhatsApp, email or push was requested.
4. The local frontend uses the real deployed API, https://u3mieg0j2e.execute-api.ap-south-1.amazonaws.com, and Cognito. Browser preflight returns 204; anonymous API access still returns 401.
5. Cleanup removed 58 regenerable files (478,073 bytes): four source Python `__pycache__` directories and the unused fallback `http_ece` wheel cache. They can be recreated by Python/the fallback build script. No source, credentials, school records, deployment artifacts, test dependencies or evidence were deleted.

Evidence: `.test-output/live-backend-smoke.json`, `.test-output/demo-queue-evidence.json`, `.test-output/deployment-verification.json`, plus direct browser observation of the dashboard and notification log. The operator smoke alone does not establish browser authentication; that was verified separately.

## Show it to judges

- Sign in → Today: show the source, timestamp, fresh status and PM2.5 reading. Explain that haze is illustrative and the data is a regional model.
- AWS console, ap-south-1: show stack `air-guardian-pilot`, IngestionFunction, AppTable/ReadingsTable and DeliveryQueue.
- Notifications → Refresh: show the actual in-app delivery receipt. Use `demo-queue-evidence.json` for the SQS message/event IDs and processing proof.
- Do not present the fictional preview on port 5187 as live AWS. School timetable/context defaults are not a verified campus assessment or a published real school instruction. No school plan was published as part of this data/queue demo.

For another bounded operator run:

```powershell
python scripts/smoke_backend.py
python scripts/demo_queue_evidence.py
```

The queue demonstration refuses external-channel preferences and respects delivery caps. Do not repeatedly run it to bypass the cap. Actual public hosting, alert email confirmation, external channels, teacher/parent review, sensors and broader production validation remain separate from the requested minimal demo.
