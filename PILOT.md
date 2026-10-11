# Real-school pilot and evidence gate

The product claim is **school-area estimate** until a colocated reference study demonstrates school-gate performance. Do not replace that label based only on station-to-station cross-validation.

## 1. Configure real air sources

1. Copy `.env.example` to `.env` and add an operator-owned `OPENAQ_API_KEY`, `WAQI_API_KEY` and/or `OPENWEATHER_API_KEY`.
2. Set the exact campus latitude and longitude in the admin School desk and select live mode.
3. Confirm the Sources panel says `Credential configured`; never record or screenshot the key itself.
4. Record the provider, station names, observation timestamps, units, nearest distance, 25 km radius and 120-minute cutoff in the pilot log.
5. If fewer than two fresh, mutually covered measurement stations are available, record held-out MAE as unavailable rather than zero.

WAQI AQI is displayed separately and is never converted into PM2.5 mass. OpenWeather and CAMS are model estimates, not measurement stations. CAMS is approximately a 45 km regional grid in India.

## 2. Validate at the school

Place a maintained reference or audited co-location monitor at the school gate for at least 14 school days. Synchronize timestamps to UTC, retain the raw hourly PM2.5 values in µg/m³, and pre-register exclusions for maintenance, warm-up and missing data.

Evaluate unseen time blocks, not random adjacent rows:

- Hold out complete days or weeks.
- Report sample count, coverage period, MAE, median absolute error, RMSE and mean bias in µg/m³.
- Report results by planning band and the confusion matrix for band decisions.
- Report station/model distance, observation age and missing-data rate.
- Keep the school-area label unless the predefined error and band-agreement thresholds are met on held-out school-gate observations.

The in-app leave-one-station-out number is a diagnostic for spatial consistency only. It is not this calibration study.

## 3. Run the daily routine

Use one real school day and one notice:

1. Admin opens School desk and publishes the Indoor PE routine.
2. Each teacher reads the notice, confirms space/supervision, tells the class and acknowledges.
3. Each linked parent reads the same notice with their child and marks it reviewed.
4. Admin records teacher and parent eligible counts, completions, rates and median completion minutes shown in the funnel.

Page loads and alert opens do not count. A teacher checklist or parent review receipt is the completion event. Follow up separately on the pending-teacher and pending-parent friction shown in the admin view. After the pilot, interview at least one person from each role and record confusing wording, permission problems, duplicate steps and missed notifications.

## 4. Verify closed-browser notifications

Generate an operator-owned VAPID key pair, set `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` and `VAPID_SUBJECT`, install dependencies, restart the server and enable Web Push in the staff account. Close the page, publish a new notice from another signed-in browser, and verify the service worker notification appears.

The delivery status `accepted-by-push-service` proves only that the push service accepted the request. Record the real-device display check separately. SMS and WhatsApp remain `mock-not-sent` and must not be presented as delivered.

## 5. Release gates and deferred work

Required before a production claim:

- Real identity enrollment, verified guardians and auditable child linking.
- Approved cloud hosting, encrypted storage, scheduler ownership, backups and incident procedures.
- Real-school calibration and connected indoor-sensor quality controls.
- Recipient consent, opt-out and delivery receipts for any SMS/WhatsApp provider.

Intentionally deferred from the core pilot:

- More charts or trained ML forecasts.
- Street navigation and tiles as a core feature.
- Broader cloud architecture work before the pilot evidence exists.
- Dense measurements or repeated decorative imagery on the Kids screen.
