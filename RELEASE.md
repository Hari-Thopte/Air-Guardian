# Release — 9 October 2026

Air Guardian opens on a welcome page with a current regional air card, an azure/teal banner, warm-white light theme and ink/cyan dark theme. The animated A/wind logo retains reduced-motion support. Kids now have a dedicated layout, Breezy mascot, picture navigation, a three-choice game, translated plan/learning guidance and a larger speaker button. Adult navigation prioritizes Today, School plan and Alerts; settings and advanced tools are grouped. Existing vanilla JavaScript and Python/Powertools/SQLite stack retained. Parents can open the school plan directly, record their review, and admins can see the aggregate count. Published notices remain visible when air alerts change.

## Verification

- 29 Python checks cover station math/staleness/cache/provider failures, model provenance, forecast validation, same-hour historical comparison, planning policy, alert controls, role/child/school isolation, review and acknowledgment workflows, exposure/check-in scopes, and backup-based test-fixture cleanup.
- 4 existing JavaScript rule checks pass.
- Guardian browser suite checks parent/teacher/admin/staff and second-school flows, exposure, check-in, Leaflet map/routes, escaped observations, language controls, weekly CSV and responsive map widths 360/390/768/1024/1440.
- PWA browser check verifies offline shell and explicit offline API failure; private APIs never enter Cache Storage.
- Existing preview browser suites cover scenario/plans, campus setup, journal/CSV, Kids learning/accessibility/reduced motion and public shared plans.
- Experience browser suite covers welcome-page entry points, both themes, layout widths 360/390/768/1024/1440, direct school-plan links, distinct Kids artwork, scenario buttons and visible keyboard focus.
- Editorial visual checks cover sampled Kids/parent text and button contrast, parent Today layout in both themes at five widths, and data-saver handling of the new illustration. Larger illustrations load when visited; PWA shell installation does not prefetch them.
- Feedback browser checks cover current/unavailable landing readings, four-button Kids navigation, explicit checklist completion, game retry/completion/replay, Hindi/Marathi speech text and plan/learning content, both themes and widths 360–1440.

Keyed station credentials and physical school-gate accuracy remain unverified in this repository; all output is therefore scoped to a school-area estimate. CAMS coverage in India is approximately 45 km. Closed-browser Web Push is implemented but requires operator-provided VAPID keys, browser permission and a real-device acceptance test. Push-service acceptance is not a device receipt. No SMS/WhatsApp messages are sent.

## Scope

Done: local role protection/model, explainable school planning rules, school-area evidence limits and held-out station errors, configurable coordinates, notice-specific pilot completion tracking, alert history, exposure proxies, coordinate route comparisons, source-labelled forecast, private optional check-ins, observations, manual indoor fixtures, adult workflow language controls, closed-browser Web Push path, PWA, recorded class-hours and weekly export.

Mocked: demo station/forecast readings, indoor sensors and SMS/WhatsApp.

Left: operator-provided station credentials, real-school calibration, production enrollment/child linking, cloud storage/scheduler, SMS/WhatsApp and receipt webhooks, hardware sensors, street routing/tiles and any trained historical-weather model. These remain release gates or intentionally deferred scope. Local demo accounts use a public fictional password. Planning policies, confidence, routes and budgets make no medical/safe-route claim.

Packages exclude `.env`, installed vendor dependencies and SQLite databases. Install the documented Python requirement before running the local zip. The static zip only supports public browser previews without its API.
