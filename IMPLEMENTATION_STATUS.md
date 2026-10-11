# Implementation status

The user's narrowed five-item AWS demo is complete: [verified demonstration](deployment/DEMO_COMPLETE.md). Real Cognito administrator login, real ARM64 Lambda ingestion, DynamoDB persistence, matching dashboard readings and a real SQS-triggered in-app receipt are verified. Public CloudFront hosting is blocked by account verification; the locally served AWS-connected portal is the accepted fallback. Phone verification UI, required authenticator MFA and resumable operator account erasure are implemented. Broader teacher/parent workflow, scheduled-run observation, external channel delivery, hardware and forecast validation remain outstanding. The older gap table below describes the original baseline, not the latest deployment state.

The cloud pilot is implemented as a separate vanilla JavaScript frontend and Python serverless backend. The original local demo and Kids experience remain intact. Backend deployment and real regional-provider ingestion are verified; the complete public school workflow is not yet verified.

| Gap | Implemented | Remaining before claiming the full vision |
| --- | --- | --- |
| Multi-source ingestion | CAMS fallback; OpenAQ/OpenWeather adapters; defensive CPCB adapter; WAQI/IQAir separate index views; quotas, timestamps, source selection and licensed retention gate | Obtain keys/permissions; verify each live response and CPCB resource/units; broader provider resilience/load testing |
| School sensors | Optional AWS IoT rule, restricted per-device certificate provisioning, registered school identity, validated telemetry and history | Hardware/firmware, field installation, calibration, maintenance; reviewed sensor promotion |
| AWS serverless | SAM HTTP API, Lambda, DynamoDB, Cognito, EventBridge schedules, SQS, SNS operations/feedback, SES, private S3/CloudFront, logs/alarms | Authenticate AWS CLI, deploy, runtime smoke test, verify alarms; Amplify intentionally unnecessary |
| Risk policy | Existing explainable age/caution policy, freshness failure state, building/ventilation context, weather display, forecast activity windows, versioned inputs | Expert validation; validated indoor/outdoor model; no arbitrary AC/time/weather risk multipliers or clinical claims |
| Notifications | Consent, quiet hours/caps, role/language messages, per-recipient queue, retries/receipts, Web Push/SES/SMS/WhatsApp adapters and feedback parsing | Sender identities, VAPID keys, DLT/business templates, paid channel onboarding, live delivery testing, phone verification UI |
| Auth/enrollment | Cognito PKCE; trusted JWT identity; database-enforced school membership; verified-email-bound single-use invitations; parent/teacher linking/revocation | Deployed end-to-end test, administrator MFA enforcement/recovery and phone account management |
| History/trends | 7/30-day source-separated charts and coverage; timestamp deduplication; 90-day TTL | Accumulate real history; larger-data pagination/performance |
| Forecasts | Regional provider forecasts, honest issue/retrieval labels, snapshots, persistence baseline and offline MAE/bias evaluator | Measured validation dataset and published skill metrics; no trained local predictor |
| Frontend/hosting | Separate responsive cloud portal; role workspaces, school settings, enrollment, child aliases, plans, history, preferences, export/unlink | Deploy HTTPS; migrate Kids and other local-only features if needed; broader accessibility/browser audit |
| School model | Coordinates/timezone, AC/non-AC/mixed, ventilation/filtration, schedule, classes/rooms, outdoor-area assessment notes/score, CPCB city | Locally agreed assessment rubric; score is descriptive and not a health multiplier |
| Scheduling | Every-15-minute ingestion, retry/DLQ, freshness handling, minute outbox/erasure relay | Verify deployed schedules and incident notifications; per-school fan-out beyond pilot |
| Sensor confidence | Staleness, clock bounds, sample count, high humidity, jumps, flatline review, identity binding | Reference calibration, drift modeling and validated confidence thresholds |
| Privacy/multi-school | Tenant membership checks, private parent records, teacher-minimum class view, consent, export, unlink/cleanup recovery, TTL/log retention | Full account/child erasure and backup procedures, legal review, public scale/load/abuse controls |

## Practical rollout order

1. Deploy the one-school cloud pilot with CAMS and in-app delivery; smoke-test all role boundaries.
2. Activate verified email and Web Push; test preference, retry and suppression paths.
3. Collect 7–30 days of source-labeled history and evaluate forecasts against independent observations.
4. Add one licensed measured provider and one physically calibrated sensor pilot.
5. Add phone enrollment and paid messaging only after approval, consent and budget setup.
6. Complete privacy administration, enforced admin MFA, accessibility and load tests before broader school enrollment.

For hackathon judging, demonstrate the authenticated plan → teacher acknowledgment → parent review loop, provenance/freshness, real regional data and honest history. Show sensors/paid channels as configured extensions only when actually activated. Do not train ML, buy a sensor fleet, add Kubernetes, migrate to React, or claim all channels are live merely because adapters exist.

## Local verification

`python scripts/run_cloud_tests.py` runs workflow, authorization, DynamoDB transaction, ingestion/outbox, privacy, sensor and provider-boundary tests using local fixtures/moto. Paid channel request contracts use botocore stubs, not actual messages. `sam validate --lint --template-file template.yaml` checks the infrastructure schema. These checks do not establish live AWS or third-party service operation.

`python scripts/preview_cloud.py --port 5186` exposes a loopback-only fictional preview with role links and an explicit banner. It makes no real provider or messaging calls. It is excluded from deployed artifacts.
