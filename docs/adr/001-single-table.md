# Single application table

Keep memberships, notices, idempotency records and receipts in the existing table with scoped partition/sort keys. Conditional revisions and transactional writes keep publication/review state consistent. Readings stay in a separate retention-focused table. Avoid a second role-specific data model.
