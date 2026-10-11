# Pilot threat model

Invite brute force: verified-email binding, hashed single-use expiring invitations, per-identity redemption limit and gateway throttling. Distributed account creation is not yet prevented; Cognito abuse controls need account review.

Notification spam: admin membership, idempotency, gateway/identity limits, explicit channel consent, quiet hours, daily caps and delivery retries. External providers remain disabled until configured. Operational alarms require a monitored email/topic subscription.

Parent enumeration/cross-school access: membership and guardian links checked server-side; unauthorized child access rejected; generic invitation failures. No child data in trace payloads or API error logs.

Role spoofing: Cognito JWT access tokens plus durable membership. X-Preview-Role exists only in the loopback preview. Kid responses use a strict allowlist and school writes are denied.

Cached/stale plans: observation times retained, source failures do not invent data, stale conditions block publication. Browser last-known state is session memory only and cannot authorize offline writes. Public service-worker caching excludes all private routes and credentials.

Remaining: penetration test, account-level WAF/bot controls, backup/restore exercise, real school consent review and incident response rehearsal before a real pilot.
