# Air Guardian

## Project summary
Air Guardian helps a school turn air information into a reviewed school-day plan. A principal sees the source, freshness and a planning flag, edits a suggested instruction, and publishes it. Teachers check classroom arrangements, parents review the notice, and staff receive a short duty instruction. Explicit receipts show who reviewed the plan. A public learning area explains the process to children without collecting their information. The local demonstration uses fictional air readings and no external messaging. Python planning rules power both the workspace and interactive landing examples. Powertools for AWS Lambda runs a credential-free engine slice; cloud deployment remains unverified.

## Problem and change
An air number alone does not coordinate assembly, PE or pickup. This prototype closes that operational loop for administrators, teachers, staff and parents. It does not diagnose risk or certify a safe activity.

Default fictional timetable: assembly 20 minutes, PE 30, break 15, pickup 20. At orange/red, reviewing PE and assembly indoors changes planned outdoor time from 85 to 35 minutes, assuming the room is assessed and the suggested plan is followed. This is a planning estimate, not measured exposure avoided. The preview uses synthetic nearby-station fixtures; every reading shows observation and retrieval times. Forecast examples are also synthetic. Real provider adapters exist but are not called by the demo.

## AWS
The real Powertools Python resolver and Lambda logger dispatch the local `/local-engine` slice. `template-local.yaml` defines a SAM API/engine slice. SAM and Docker were unavailable for container verification. The separate cloud template implements Cognito, API Gateway, Lambda, DynamoDB, SQS and optional delivery/sensor resources; none is claimed deployed. See AWS_USAGE.md and assets/architecture.svg.

## Run in under five minutes
From updated-project: install `cloud/requirements.txt` if needed, then `python scripts/preview_cloud.py --port 5187`. Open http://127.0.0.1:5187/home.html. Demo data loads at startup. Run `python scripts/run_cloud_tests.py` for backend checks. The local preview binds only to loopback and makes no provider or external delivery calls.

## Recorded demonstration, 3:00
- 0:00–0:25: Explain one school's assembly/PE decision and why a number alone is insufficient. Open the landing day instrument; select Red.
- 0:25–0:55: Show the architecture, then `/local-engine` returning a result from the actual Powertools handler. State that cloud deployment is unverified.
- 0:55–1:20: Open admin Today. Demo tools → Green, then Red starts a new draft with zero reviews. Show current source/freshness, Morning brief and engine reasons.
- 1:20–1:45: Open School plan, edit wording, review phone preview and Publish plan. Explain consent/caps and that the demo sends no external messages.
- 1:45–2:15: Switch Parent, open plan, Mark as read. Switch Admin, Refresh and show the unique receipt count rise from 0 of 6 to 1 of 6. Explain that review is not an outcome.
- 2:15–2:45: Show the outdoor-time planning estimate and teacher checklist. Inspect history gaps and labelled synthetic source.
- 2:45–3:00: Close with the people served, kids' learning panel, and next steps: school pilot, calibrated measurements, actual deployment and verified delivery.

## Limitations
No school-gate accuracy is established. Policy thresholds are illustrative and require school approval. Indoor conditions are unknown unless measured. Custom school instructions are not automatically translated. Regional forecasts are not gate predictions. Local MemoryStore resets on restart. No deployment, real school pilot, health outcome or live WhatsApp/SMS delivery is claimed.
