# Three-minute recorded demo

For the judge-facing one-page version, including accounts and real-versus-simulated scope, see [JUDGES.md](JUDGES.md).

Use fictional accounts/data only. Run the Python server and open `/` for the welcome page. Use the same Delhi demo campus throughout the recording. Keep live-source and practice-day labels visible.

- 0:00–0:25: Open the landing page and show the current PM2.5 value, timestamp and source. Explain the specific problem: families and staff need a clear school-day action before the school run and outdoor PE. The keyless Open-Meteo/CAMS fallback is a regional model, about 45 km across in India; it does not verify conditions at the school gate. If fetching fails, show the honest unavailable state.
- 0:25–0:45: Enter Kids. Show Breezy, the short action message, large Read aloud button, and Today / My Plan / Play / Learn navigation. Open the plan directly and briefly demonstrate one decision in the practice game. Explain that a grown-up confirms the actual school plan.
- 0:45–1:25: Enter the authenticated school workspace as admin. Enable the labelled polluted-day simulation. Show the planning flag and one explanation, then publish: “Today’s practice plan: PE in classrooms; collect children promptly at the usual gate.” Sign in as teacher, review the three checks, enter 30 minutes moved indoors, and acknowledge.
- 1:25–1:55: Sign in as parent. Follow Today’s Read school plan button, read the notice, and mark it reviewed. Explain that this receipt is explicit: opening the dashboard alone does not mark a notice read. Briefly show the child alias and optional extra-caution setting.
- 1:55–2:15: Sign in as staff. Show the local-language flag and short duty instruction. Explain that in-app messages work, while WhatsApp/SMS delivery remains a labelled mock. Do not imply that a message was sent externally.
- 2:15–2:40: Sign back in as admin. Show the teacher acknowledgment and parent review count. Show recorded class-hours moved indoors, explaining that this is a logged planning action rather than a measured health outcome. Show the shared event history without test fixture notes.
- 2:40–3:00: Show `/api/health` and the Powertools resolver source. Explain that the running local backend uses the AWS open-source Powertools project and SQLite. End with the next validation step: nearby measured stations or a classroom sensor. Cloud Lambda, DynamoDB and OpenSearch are future deployment work.

Fictional account password: `AirDemo2026!`. Do not show `.env` values or private child information. If time is tight, prioritize the announcement → teacher acknowledgment → parent review → admin tracker workflow. Keep the experimental route comparison out of the main recording: it currently uses manually supplied paths and pollution proxies, not verified street-level navigation. Do not present synthetic held-out station error as real-world accuracy evidence.

## Prepare a clean recording

After all browser tests have finished, run `python scripts/prepare_demo.py` to inspect an aggregate dry report. Run `python scripts/prepare_demo.py --apply` to back up the SQLite database and remove exact known browser-test observations and demo announcements, plus their linked delivery, review, acknowledgment, schedule and history records. The backup path is printed; backups stay under `backend/.local/backups` and must not be published.

The script is deliberately narrow and repeatable. It preserves automatic flag transitions, other announcements, school settings, check-ins and preferences because their origin cannot be established safely. It does not manufacture a fresh notice or reset the impact number. Publish the practice announcement in the recording and record only the minutes actually demonstrated. Re-running the script when there are no matches makes no backup and removes nothing.

Before recording, close extra browser tabs, choose the intended language, and read each account’s current school name. Confirm the app shows the selected source and timestamp. A stale or unavailable provider remains visible as such; switch explicitly to the labelled simulation when demonstrating the plan workflow.
