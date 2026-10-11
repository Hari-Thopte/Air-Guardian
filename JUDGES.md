# Air Guardian — current judge guide

Use the `home.html` / `cloud.html` demo on port **5187**. The older port 5174 application and its demo passwords are separate; they are not needed for this walkthrough.

## Start

Follow the installation command at the top of README.md, then run:

```powershell
python scripts/preview_cloud.py --port 5187
```

Open http://127.0.0.1:5187/home.html. The preview uses synthetic air, forecast, sensor and school records. No real messages are sent. The preview role switch is not production authentication; a configured deployment uses Cognito. Do not deploy `preview_cloud.py`.

## Three-minute recording

Use SUBMISSION.md for the complete timed narration.

1. Show the landing example. Select Red and move the hour marker; explain the suggested assembly/PE change and its engine reason.
2. Show `/local-engine`: the actual Powertools for AWS Lambda resolver runs locally. Cloud resources are implemented in templates; AWS deployment remains unverified.
3. Open admin Today. Demo tools → Green, then Red starts a new draft with zero reviews. Show PM2.5, the source/freshness evidence and outdoor-time planning estimate. Review wording and confirm Publish plan.
4. Viewing as → Parent → School plan → Mark as read. Return Admin → Today → Refresh: 0 of 6 becomes 1 of 6. The count records unique adult reviews, not page views or health outcomes; the fictional audience contains six adults.
5. Show the teacher checklist and the kids' short learning question. Close with the intended school pilot and measurement/delivery validation needed next.

Demo tools are under Viewing as: Admin → Demo tools…. Green shows “No change needed”; a stale scenario blocks publication. Display timestamps are shifted to a labelled 07:30 IST morning; actual freshness and notification limits are not altered.

## Claim boundaries

- Working locally: Python planning rules, real Powertools resolver, role-scoped API paths, publication, review receipts, teacher checklists and planning estimates.
- Synthetic in this preview: station readings, forecast/history, school audience and active sensor fixtures. The sensor does not prove classroom conditions are suitable.
- Implemented but unverified in AWS: Cognito, API Gateway, Lambda, DynamoDB, SQS and optional delivery/sensor resources. See AWS_USAGE.md and CLOUD_DEPLOYMENT.md.
- Not claimed: school-gate accuracy, official full AQI, medical advice, forecast skill, measured exposure/health improvements, real WhatsApp/SMS delivery or a completed school pilot.

Custom school instructions keep their original wording when navigation language changes. Mention that limitation when demonstrating Hindi or Marathi. Hard-refresh before recording to pick up the latest local UI.
