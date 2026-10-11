# Current Air Guardian upgrade

## Completed live AWS demo

The minimal AWS demo is now verified: real Cognito login → real ARM64 Lambda ingestion → DynamoDB persistence → authenticated dashboard, plus a real SQS-triggered in-app notification receipt. See [demo evidence and click path](deployment/DEMO_COMPLETE.md).

```powershell
python scripts/serve_deployed.py --port 5191
```

Open http://localhost:5191/cloud.html. This frontend is locally served but connects to deployed AWS API/Cognito. Keep the server running. CloudFront public hosting remains blocked by AWS account verification; the local frontend is the accepted demo fallback. CAMS readings are real regional model estimates, not school sensor measurements. The preview instructions below are a separate fictional demonstration.

Run this version: the current landing and role workspace are `home.html` and `cloud.html` on port 5187. The UI polish retains the original logo, routes and vanilla JavaScript/Python stack. The section marked Legacy below describes the preserved older local application on port 5174.

## Start the current preview

```powershell
python -m pip install --target .test-output/deps -r cloud/requirements.txt -r tests/requirements.txt
python scripts/preview_cloud.py --port 5187
```

Open http://127.0.0.1:5187/home.html. This is fictional loopback data, not an AWS deployment. A week of observations, three classes, aliases, previous plans and experimental sensor fixtures load automatically. Viewing as: Admin → Demo tools… → Refresh demo fixtures adds missing fixtures without overwriting reviews and refreshes the synthetic active sensor. The Fictional air scenario control selects Green/Yellow/Orange/Red or a stale reading. The stale reading blocks publication.

Demo display timestamps are shifted to a school morning; published/review timestamps show a labelled 07:30 IST. Freshness, expiry, notification quiet hours and daily limits still use the actual clock. Forecast-valid times are not shifted. Changing a demo scenario starts a draft with zero displayed reviews; earlier publication records remain in history, and publishing creates a separate event. Figtree and the Devanagari fallback are served locally; font licenses and provenance are in `assets/fonts`. Small WebP header images and a PNG favicon preserve the supplied emblem.

```powershell
python scripts/run_cloud_tests.py
node --test tests/ui_consistency.test.mjs
python scripts/check_preview.py --port 5187
python scripts/export_scenarios.py
python scripts/package_cloud.py
```

The HTTP check mutates fictional preview data only. It verifies publication, a unique parent review, role privacy and stale-data rejection. No external messages are sent. Presentation mode is `/cloud.html?role=admin&present=1`; role controls and the demo banner/tools are hidden, text enlarged and scrollbars hidden. Regular page scrolling remains available.

## Three-minute demo path

1. Home: choose Red in the example instrument and move its hour marker. Explain that the wording is exported from the actual policy, not a live school instruction.
2. Open the school workspace → Viewing as: Admin → Demo tools… → Green, then Red. Show the new Draft with zero reviews, source/freshness, Morning brief and outdoor-time planning estimate.
3. Publish plan (or Edit wording first). Read the draft and adult audience count in the confirmation dialog. Confirm publication.
4. Viewing as → Parent → School plan → Mark as read.
5. Viewing as → Admin → Today → Refresh. Show the updated count. The count uses unique adults at publication; the demo currently contains six.
6. Notifications → Remind people who have not confirmed. If disabled, show its quiet-hours/cap reason rather than bypassing it. This generates in-app records only in the preview.
7. Return Today for the outdoor-time summary, then show the kids' public learning panel and the AWS architecture. `/local-engine` demonstrates the actual Powertools Lambda resolver.

Use SUBMISSION.md for the timed 3:00 narration; AWS_USAGE.md for the exact implementation boundaries.

## Mocked and unverified

Air/forecast/history/sensors/adults are fictional. No real messages, school-gate accuracy, indoor clearance or health outcome is claimed. Custom school wording stays in its original language; preview headings and the print footer can use English/Hindi/Marathi. The workspace shares the school timetable across classes. The flag-change banner records this browser session, not a complete audit of air changes. The current-hour fallback is stated when no matching hourly forecast exists.

The AWS backend is deployed and the minimal live demo above is verified. The fictional preview remains separate. Earlier browser checks covered the landing at 1440, 1024, 768 and 390px in both themes, admin publication at 1280×800, parent review and sensor cards at 390px, role-menu keyboard focus and the hour slider. These are targeted checks, not a full accessibility certification. The primary-button contrast ratios measured 5.37:1 in light and 7.96:1 in dark. See [the completed AWS demo](deployment/DEMO_COMPLETE.md) for current live evidence.

---

# Legacy local application — port 5174

**New home page and school portal:** run `python scripts/preview_cloud.py --port 5187`, then open http://127.0.0.1:5187/. The local cloud preview is fictional and sends no messages. The landing page is `home.html`; `cloud.html` remains the authenticated school portal in a configured deployment.

**Cloud pilot implementation:** [deployment guide](CLOUD_DEPLOYMENT.md) · [implemented features and remaining work](IMPLEMENTATION_STATUS.md) · [verified live demo](deployment/DEMO_COMPLETE.md). The Cognito/DynamoDB portal is `cloud.html`; run `python scripts/preview_cloud.py --port 5186` only for an explicitly fictional local preview. The instructions below describe the original local demo, not the deployed backend.

School-area air estimates and practical school-day plans for children, parents, teachers and staff. Existing vanilla JavaScript UI retained; Python local API uses the real **Powertools for AWS Lambda** open-source resolver with SQLite persistence. No AWS account required. No Lambda/DynamoDB deployment is claimed.

## Run

```powershell
python -m pip install --target backend/vendor -r backend/functions/requirements.txt
python server.py --port 5174
```

Open http://127.0.0.1:5174/ for the welcome page, then enter the school workspace or Kids view. Direct workspace link: `/?page=guardian`. The preview binds to loopback only.
The existing simplified Kids preview remains available at `/?view=student`.
Install the Python dependency for Guardian tools; the legacy browser preview can run without it.

## Accounts and workflows

Select `parent`, `teacher`, `staff`, `admin` or `parent-other` on the login form. All fictional accounts use **AirDemo2026!**. Parent-other belongs to the Mumbai demo school; the other roles belong to Delhi. These publicly documented accounts are for fictional demo information only.

- Parent: a readable school plan, explicit review receipt and 48-hour child-free share link, two linked child aliases, age-group/caution settings, private yes/no check-in, daily exposure proxy, two-path comparison, forecast, observations and notification preferences.
- Teacher: class-only aliases and explicit parent-selected caution labels, three-step action review, acknowledgment and minutes moved indoors. No symptoms, age bands or exposure records returned.
- Staff: current flag and a translated instruction; no child records returned.
- Admin: school coordinates/data mode, polluted-day simulation, conservative four-hour overrides, announcements, a completion-status hero, today/weekly response metrics, labelled indoor fixtures, history and weekly CSV.

One server-side user/school/class/child model protects `/api/guardian/*`. Session tokens are hashed at rest; cookies are HttpOnly/SameSite Strict; credentials use salted PBKDF2. The header-based `/api/plans/*` endpoints remain explicitly public legacy practice previews containing no private child data. Role buttons in the header select those previews and never grant authenticated permissions.

## Sources and estimates

The welcome page fetches a current reading through the local API. Open-Meteo/CAMS supplies a keyless regional fallback when configured providers have no usable concentration data. Its approximately 45 km grid in India is explicitly labelled; it does not establish school-gate air quality. The landing card shows PM2.5, a separately labelled India particle-index estimate, the input age and source. Failed refreshes clear the current value.

For station data, copy `.env.example` to `.env`, add only your own keys and restart the server. `.env` is ignored and never served. Supported keyed adapters are OpenAQ v3, WAQI and OpenWeather Air Pollution. Missing keys, errors, unusable observations and stale cached data are explicit states; live mode never silently supplies demo data.

Measured nearby station concentrations use inverse-distance-squared interpolation within 25 km with a two-hour freshness cutoff. Every result is labelled **school-area estimate**, never school-gate measurement. OpenWeather is a separately labelled model fallback. WAQI pollutant indices are not treated as mass concentrations or mixed into concentration interpolation. The particle index uses India breakpoint interpolation on instantaneous particle inputs: it is an **estimate**, not a complete official AQI calculation. Coverage confidence is a heuristic, not a probability of accuracy. Leave-one-station-out PM2.5 MAE, units, calculation time, individual held-out errors, radius and freshness limits are displayed where enough usable stations exist; demo errors remain explicitly synthetic.

Real provider requests send the configured campus coordinates to the selected providers. A public Delhi-coordinate Open-Meteo response was checked during development; keyed station providers and school-gate accuracy remain unverified. The optional public overview uses provider US AQI; the school engine exposes its derived India particle estimate separately. School planning flags use conservative illustrative thresholds and have an on-screen explanation. [Open-Meteo coverage documentation](https://open-meteo.com/en/docs/air-quality-api).

## Planning rules and exposure

Age-band thresholds and a higher-caution flag produce an illustrative school planning priority, not a clinical risk score. Explainable actions cover indoor PE, fit/suitability-aware mask reminders, gate waiting/idling, traffic, ventilation checks and staff duty rotation. Existing school instructions and care plans take precedence.

Exposure sums entered PM2.5 concentration × minutes for commute/outdoor/indoor activity. The adjustable budget is a **planning target**, never a medically safe limit. Unrecorded time is unknown. Route comparisons sample station interpolation along user-entered coordinate paths and multiply by entered travel time. The offline Leaflet map shows coordinates, stations and paths; it has no street tiles, navigation or proof of a safe route.

## Alerts and offline behavior

While the local server runs, a minute monitor checks threshold changes and a 06:30–06:39 IST morning forecast window. Threshold events deduplicate and have a four-event daily school cap; user preferences add channel caps, quiet hours and morning suppression. Announcements use the same role-template/delivery pipeline. In-app event history works. With VAPID keys configured, browser Push API subscriptions receive instructions through the service worker even after the page closes. Delivery history reports push-service acceptance or send failure; acceptance is not proof that a device displayed the notification.

SMS/WhatsApp are **mock-not-sent** records. They are disabled as real channels until a reviewed provider integration, verified recipients and receipt webhook exist. Reliable cloud scheduling remains future work. Forecasts use OpenWeather or CAMS provider data, or clearly synthetic fixtures. The Today view shows a same-hour PM2.5 change only when matching regional historical data is available.

PWA caches the public application shell only. `/api/` data is network-only; offline private data and current air flags are unavailable. Core controls, adult workflow labels and role messages support English/Hindi/Marathi; dynamic measurement evidence retains pollutant names, units and provider identifiers. Read aloud selects the matching browser voice language, subject to installed voices. Data saver skips large illustrations. Indoor readings are manual, labelled fixtures; observations are unverified school-shared notes. Optional check-ins expire after 30 days and stay parent-only.

The admin → teacher → parent pilot is tracked against the latest published school notice. The admin sees eligible counts, explicit completions, rates, median completion time and pending friction; page views are never counted. The Kids view remains intentionally sparse. Routes stay experimental, forecasts stay provider-labelled, and cloud expansion is deferred. See [PILOT.md](PILOT.md) for real-school evidence and rollout gates and [DEMO.md](DEMO.md) for the walkthrough.

## Verify and package

```powershell
python -m unittest discover -s tests -p "*_test.py"
node --test tests/data.test.js
node tests/guardian.cjs
node tests/experience.cjs
node tests/editorial.cjs
node tests/pwa.cjs
node tests/feedback.cjs
node tests/ui-check.cjs
node tests/features.cjs
node tests/kids.cjs
node tests/campus.cjs
node tests/shared-plan.cjs
python scripts/build.py
```

Browser tests require Playwright and Chrome; set `AIR_GUARDIAN_BROWSER` and `AIR_GUARDIAN_URL=http://127.0.0.1:5174`. External browser requests are blocked; provider responses are controlled fixtures. Unit tests use temporary stores. Browser tests create fictional local records.

The local zip includes server/source/setup instructions but excludes credentials, vendor installation and local databases. The static zip supports public previews; authenticated Guardian tools need the Python API. See [implementation status](IMPLEMENTATION_STATUS.md), [live AWS demo](deployment/DEMO_COMPLETE.md), [legacy demo](DEMO.md), [release instructions](RELEASE.md) and [asset provenance](ASSETS.md).

AWS project: https://github.com/aws-powertools/powertools-lambda-python
Separate `backend/template.yaml` is an undeployed cloud foundation, not the SQLite application's deployment definition.
