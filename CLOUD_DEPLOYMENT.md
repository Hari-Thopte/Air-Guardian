# Air Guardian cloud pilot

The St. Xaviers Manickpur backend is deployed, with real Cognito administrator login, ARM64 Lambda ingestion, DynamoDB persistence and an SQS-triggered in-app receipt verified. Follow [the pilot runbook](deployment/RUNBOOK.md), [current verification status](deployment/STATUS.md) and [completed demo](deployment/DEMO_COMPLETE.md).

Use container builds for Linux ARM64 dependencies. Public CloudFront hosting remains blocked by account verification; the accepted demo frontend runs locally against deployed AWS services.

The new cloud application is `cloud.html`; the original local demo remains available separately. The cloud handlers use DynamoDB and Cognito, never local demo cookies or SQLite. This is a controlled pilot implementation, not a clinically validated air-quality system. See [implementation status](IMPLEMENTATION_STATUS.md) for the remaining full-vision work.

## Build and validate

Use Python 3.12, AWS CLI v2 and AWS SAM CLI. On Windows the Lambda dependency bundle must contain Linux wheels. From this directory:

```powershell
python -m pip install --target .test-output/deps boto3 "moto[dynamodb,sqs]" aws-lambda-powertools tzdata
python scripts/run_cloud_tests.py
python scripts/package_cloud.py
sam build --use-container --template-file template.yaml
sam validate --lint --template-file template.yaml
```

The package script copies allowlisted application files. Do not upload the project directory, SQLite files, `.env`, `.devices`, or `.test-output`. For a clean dependency rebuild use a fresh checkout/build directory. The script does not prune old third-party dependency versions. A Linux Lambda runtime smoke test remains required before enrolling real users.

## Deploy the private website and API

This creates billable AWS resources. Begin with one school and external delivery disabled. AWS login was expired during implementation; no live deployment has been verified.

```powershell
aws login
aws sts get-caller-identity
sam deploy --template-file .aws-sam/build/template.yaml --stack-name air-guardian-pilot --region ap-south-1 --resolve-s3 --capabilities CAPABILITY_IAM --parameter-overrides CognitoDomainPrefix=YOUR-GLOBALLY-UNIQUE-PREFIX --guided
python scripts/package_cloud.py --stack airguardian-pilot --region ap-south-1
```

The last command creates `dist/cloud-config.js` from stack outputs and prints the destination bucket/distribution. Upload only `dist` to that bucket, then invalidate CloudFront:

```powershell
aws s3 sync dist s3://YOUR-WEB-BUCKET --cache-control "no-cache" --region ap-south-1
aws cloudfront create-invalidation --distribution-id YOUR-DISTRIBUTION-ID --paths "/*"
```

CloudFront uses a private S3 origin and HTTPS. Cognito callback/logout URLs and API CORS use the generated distribution hostname. S3 + CloudFront is the chosen hosting option; adding Amplify as well is unnecessary. Do not use the fictional preview as a deployed authentication layer.

Sign up through the website and verify the administrator email. Using `AppTableName` and `UserPoolId` from stack outputs:

```powershell
python scripts/bootstrap_school.py --table YOUR-APP-TABLE --pool YOUR-USER-POOL --admin-email YOUR-VERIFIED-EMAIL --school-id school-1 --name "Your school" --lat 19.07 --lon 72.88 --region ap-south-1
```

Sign in again. Set actual school coordinates/context, create classes and child aliases, and issue verified-email-bound invitations. Existing parents can be linked to additional children through Enrollment. Invitation codes expire after 24 hours and are single-use. Signup alone grants no school access. Subscribe an operator to the `OperationsTopicArn` output and confirm the subscription so alarms reach someone.

## Activate data sources

The default is regional Open-Meteo/CAMS, labeled as a model. School ingestion runs every 15 minutes; that is a polling interval, not a promise of fresh provider observations. Source observation time is preserved. More than two hours old becomes unknown.

Store provider credentials as SSM SecureString parameters under `/airguardian/`; keep values out of shell history, source control and frontend config. Supply a JSON `ProviderParameters` mapping (`openaq`, `openweather`, `cpcb`, `waqi`, `iqair`) to parameter names. Supply `RetainProviders` only after confirming provider terms permit the intended retention. Exact source labels appear in `cloud/providers.py`. CPCB additionally needs `CpcbResourceId` and the exact city in school settings. Records with unclear units are rejected. Provider keys, quotas and commercial usage permissions are operator prerequisites.

WAQI and AQICN are the same source here. WAQI/IQAir comparisons are admin-requested, not archived, and are never mixed with India particle estimates. Confirm display licensing before enabling keys. Quota reservations include failed attempts and are conservative, not provider billing guarantees.

## Activate notifications

All channels require the recipient's saved consent. Quiet hours and per-channel daily caps apply. No contacts or messages are created by deployment.

* **In-app:** available immediately; persistent event and review records.
* **Web Push:** generate a VAPID key pair; keep the private key in SSM SecureString. Set `VapidPublicKey`, `VapidPrivateParameter`, and `VapidSubject` (operator mailto). Users must enable the browser subscription and select Push. Browser support/permissions still apply.
* **Email:** verify an SES identity in the deployment region and set `SesFrom`. The template creates a configuration set and delivery/bounce/complaint feedback. In the SES sandbox recipients must also be verified; request production access for real enrollment. Bounces/complaints suppress future email.
* **SMS:** set `PaidChannels=sms` only after obtaining the origination identity, configuration set, India DLT entity and approved template. Supply `SmsOrigination`, `SmsConfigSet`, `SmsEntityId`, `SmsTemplateId`. Register the exact message structure in `cloud/channels.py`. Configure the SMS configuration-set event destination to the stack feedback SNS topic with appropriate service publishing permissions. The adapter enforces a per-message price ceiling; it is not a monthly spending cap.
* **WhatsApp:** requires an onboarded AWS End User Messaging Social business phone number and approved template, billing and valid Meta API version. Set `WhatsAppOrigin`, `WhatsAppTemplate`, `MetaApiVersion`, and the paid channel parameter. Configure the phone number event destination to `FeedbackTopicArn` using `FeedbackPublisherRoleArn`. The approved template needs one body parameter for the flag. This is not free or an unapproved free-form messaging workaround.

SMS/WhatsApp consent requires a Cognito-verified E.164 phone number. Phone enrollment, resend and verification are available in Notifications. Configure `CognitoSmsRoleArn` and `CognitoSmsExternalId` with an approved SMS publishing role before use. Users must save their notification consent again after verification. The app fails closed if the phone is unverified.

SQS delivers one job per recipient. A durable lease/receipt avoids ordinary duplicate retries, but a process crash after provider acceptance and before saving its ID can still cause a duplicate. Provider acceptance is not human receipt. Push has no end-device delivery confirmation. Callback mappings and receipts expire after 30 days.

## Sensors and forecasting

See [sensor setup](sensors/README.md). Enable the optional IoT resources, register the device in the admin UI, then run `scripts/provision_sensor.py --help`. Each certificate publishes to its own exact topic. Physical hardware, firmware, enclosure, power, installation and calibration still need field work. Experimental readings never automatically replace the regional planning input.

History starts accumulating after deployment. Seven/thirty-day charts never synthesize missing observations. Daily values are sampled means with coverage, not official daily AQI. Provider forecast snapshots and a persistence baseline are available; `scripts/evaluate_forecasts.py --help` evaluates only against actual station/sensor observations, not modeled data masquerading as ground truth. No trained ML model or demonstrated accuracy is claimed.

## Retention and operations

Readings/events/operational review receipts: 90 days. Forecasts, sensor telemetry, parent check-ins, exposure records and delivery records: 30 days. Application reads hide expired records immediately; DynamoDB TTL deletion is asynchronous. Logs: 14 days. Profiles and membership records remain until removed. Parent unlinking immediately removes access and creates a durable cleanup job for private school records. Complete Cognito account deletion, orphaned child deletion and backup erasure require an operator process; this is not a complete privacy compliance certification.

Application DynamoDB point-in-time recovery and the website bucket are retained on stack deletion. Budget for retained resources and document any required deletion. Backups can retain deleted data until their retention window expires; do not restore erased records into active service without replaying erasure requests.

The intended pilot is 1–3 schools and up to 500 memberships per school. Queries are deliberately bounded; this is not unlimited multitenancy. Split ingestion/fan-out into per-school jobs and add pagination/load tests before growing beyond the pilot. Review administrator MFA, provider licensing, consent, retention, accessibility and abuse throttling before public enrollment.

Set an AWS Budget before rollout and inspect costs daily during the pilot. Credits/Free Tier depend on account eligibility; on-demand DynamoDB, PITR, Cognito Essentials, logs, SMS, WhatsApp and SES can cost money. There is no guaranteed-zero-cost claim and no hard global spending cutoff. The design avoids NAT gateways, provisioned servers, OpenSearch and duplicate hosting services.

Smoke test the deployed site with fictional aliases first: sign in; bootstrap; invite one teacher and parent; observe ingestion; publish; acknowledge; review; inspect history; revoke a membership and confirm immediate denial; test one opted-in channel with a verified operator recipient; inspect alarm and dead-letter paths. Only then enroll real families.
