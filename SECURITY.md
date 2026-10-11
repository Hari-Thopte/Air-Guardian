# Security reporting and pilot limits

Do not include tokens, child records or private school data in public issues. Report a minimal reproduction privately to the deployment operator; the repository has no designated public security inbox yet.

Use Cognito access tokens, school membership checks and SSM SecureString credentials. The fictional loopback preview server must never be exposed or deployed as production authentication.

Run the role/expiry/notification tests before changes. Review THREAT_MODEL.md and docs/CHILD_DATA_REVIEW.md before enrolling a real school. No certification or legal-compliance claim is made.
