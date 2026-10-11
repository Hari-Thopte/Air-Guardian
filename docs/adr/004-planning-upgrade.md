# Shared state and honest presentation

The existing single DynamoDB application table stays authoritative for membership, plan and review state. Forecast/readings remain in the readings table. This avoids a parallel role model.

The local role header is accepted only by the loopback preview adapter. The deployed API derives identity from validated Cognito access-token claims and verifies memberships for every school action. Client role menus never authorize actions.

Labels distinguish synthetic fixtures, regional models, cached data, published school instructions and illustrative sky effects. No regional reading is described as a school-gate sensor or health measurement. A read-only Kid response uses an explicit allowlist instead of filtered adult response fields.
