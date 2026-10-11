# St. Xaviers, Manickpur pilot

School coordinates are approximately 19.372139, 72.828225, from a [published campus location](https://kiwix.scoggi.net/content/wikipedia_en_all_maxi_2023-11/A/St._Xavier%27s_English_Medium_School_%28ICSE%29%2C_Manickpur). Administrator, operations and budget email: harshikathopte@gmail.com, as requested. This does not establish affiliation with the school. Create actual classes and invitations only for authorized participants. Use fictional aliases for verification.

## Authenticate, build, deploy and publish

From the project directory:

```powershell
python -m pip install --target .test-output/deps -r tests/requirements.txt aws-lambda-powertools tzdata
aws login
aws sts get-caller-identity
.\scripts\deploy.ps1 -ExpectedAccount YOUR_12_DIGIT_ACCOUNT_ID
```

AWS account email cannot substitute for the account ID; inspect the authenticated identity. The script runs tests, packages allowlisted files, validates SAM, builds in a Linux ARM64 container, checks native imports, deploys the built template, generates frontend config, uploads private S3 content, invalidates CloudFront and writes verification evidence. `-Profile` selects an alternate CLI profile. The configured Cognito domain is a candidate; if unavailable, choose another prefix in `pilot.parameters.yaml`.

Cloud resources are billable. The USD 10 monthly budget sends an 80% actual-spend warning and does not stop spending. Confirm the SNS subscription email. A pending confirmation or school awaiting ingestion makes the verification command return nonzero even if stack creation succeeded. Rerun after completing those steps.

Docker is working; the ARM64 container build and native runtime import checks passed. The backend is deployed. Public hosting currently uses `EnableWebsiteHosting: 'false'` because AWS blocks CloudFront pending account verification; see `AWS_SUPPORT_DRAFT.md`. Until resolved, run `python scripts/serve_deployed.py --port 5191` and open http://localhost:5191/cloud.html. Once AWS verifies the account, enable hosting and rerun deployment/publishing; regenerated frontend config uses the public origin. Do not present localhost as a public deployment.

## Establish the school

Open the deployed `/cloud.html`, sign up as harshikathopte@gmail.com, verify the email, and finish authenticator MFA setup. Then:

```powershell
python scripts/bootstrap_pilot.py
```

Sign in again. In Enrollment create actual classes, authorized teacher/parent invitations and fictional test aliases. Invitations are email-bound, expire, and cannot be reused. Do not invent recipient contacts or class rosters. Configure school hours, classrooms, ventilation and outdoor context from actual school information.

## Real data and schedules

```powershell
python scripts/probe_air.py
python scripts/verify_deployment.py
```

The first command records the actual CAMS response, units and source timestamp. It never substitutes demo fixtures. The second checks AWS functions, schedules, retries, SQS mappings, MFA, hosting, alarms, budget and fresh school ingestion. Observe at least two scheduled ingestion intervals and compare `lastSuccessfulAt` and provider `observedAt`; polling a model does not make it a new measurement. Tests cover stale rejection, failed providers, retries and tenant isolation; these remain distinct from deployed evidence.

For additional providers, obtain credentials and retention/display permission, then run `python scripts/configure_channels.py --provider openaq` (or another supported provider). The hidden prompt writes SSM SecureString; combine printed parameter mappings with existing mappings before redeployment. Never paste secrets in chat. Set retention only after provider licensing review. CPCB additionally needs an exact city and resource ID, and explicit concentration units.

## Push, email and phone channels

```powershell
python scripts/configure_channels.py --push
python scripts/configure_channels.py --ses-email harshikathopte@gmail.com
```

The VAPID key and parameter name are already provisioned and saved in `pilot.parameters.yaml` with the operator mailto subject. The private key remains in SSM. Verify the SES identity email; set `SesFrom` only after verification. SES sandbox requires verified recipients. Request production access before wider rollout. Use an opted-in operator test recipient and inspect feedback/suppression records.

SMS needs approved origination, configuration set and India DLT identity/template. WhatsApp needs an onboarded business phone, approved template and valid Meta API version. Configure feedback destinations using stack outputs. Then supply the existing SMS/WhatsApp template parameters and enable `PaidChannels`. Configure Cognito's SMS publishing role/external ID separately for phone verification. The Notifications page sends/verifies a code, clears the old delivery contact when a number changes, and requires renewed consent. Do not mark a number verified administratively to bypass this flow.

## Complete deployed workflow and load evidence

Use separate verified adult accounts and a separate existing school with no test-user memberships. Set short-lived access tokens privately in the terminal:

```powershell
python scripts/workflow_deployed.py API_URL st-xaviers-manickpur --other-school OTHER_SCHOOL_ID
python scripts/workflow_deployed.py API_URL st-xaviers-manickpur --other-school OTHER_SCHOOL_ID --publish
python scripts/load_deployed.py API_URL st-xaviers-manickpur --requests 30 --workers 2
```

The workflow reads `AG_ADMIN_TOKEN`, `AG_TEACHER_TOKEN`, `AG_PARENT_TOKEN`; load/smoke read `AG_ACCESS_TOKEN`. `--publish` writes a labeled test plan, teacher acknowledgment and parent review. Publishing may fan out to opted-in recipients: use a controlled test school before enrollment. Verify revocation immediately denies the existing token. The load probe is bounded/read-only; 429 is reported as throttling, not an application outage. It does not establish production capacity.

For alarm receipt, use a controlled alarm test after confirming the subscription and record the actual received email. Verify retries/DLQ in a test stack; do not inject failures into an enrolled school's ingestion. Receipt configuration alone does not prove receipt.

## Account erasure and recovery

`python scripts/delete_account.py --username EMAIL --subject COGNITO_SUB` first prints a review plan. Add `--execute` to disable the identity, globally sign out, delete memberships/personal rows and sole-guardian aliases, then delete Cognito. Another administrator must be assigned before deleting the last one. Rerunning resumes interrupted cleanup. The durable `ACCOUNT_ERASURE` ledger blocks surviving access tokens and must be preserved/replayed before restoring a backup. School receipts retain their existing TTL; PITR and retained resources expire independently and need operator tracking. This procedure is not a privacy compliance certification.

## Sensors, forecasts and hackathon recording

Optional sensors still require physical hardware, calibration and authorized installation. Enable `EnableSensors`, register a device, and use `scripts/provision_sensor.py`; restricted certificates publish only the device's topic. Never promote uncalibrated experimental readings as school measurements. Accumulate independent observations before `scripts/evaluate_forecasts.py`; modeled data is excluded from forecast ground truth.

Record the demo after deployment verification: (1) deployed HTTPS URL and MFA login; (2) school coordinates, actual source and timestamp; (3) publish → teacher acknowledgment → parent review; (4) CloudFormation, ARM64 Lambda, private hosting, schedules, queues and alarms; (5) saved cross-school denial and verification report. Describe CAMS as a real regional model. Show local fixtures, paid channels or sensors only with their actual simulated/configured/live status. No deployed video exists until these steps have actually run.
