# Authoring guide

All files are JSON in this reference repo; the pipeline may render YAML into the
same structures. Normative schemas live in `controls-core/contracts/`.

## 1. Authorization rules

`policies/*.json`

```json
{
  "version": "1.0",
  "defaultEffect": "deny",
  "rules": [
    {
      "id": "account.read.owner-or-region",
      "effect": "allow",
      "resourceType": "account",
      "action": "read",
      "when": {
        "any": [
          { "field": "subject.sub", "op": "eq", "value": "$resource.ownerId" },
          { "field": "subject.claims.region", "op": "eq", "value": "$resource.region" }
        ]
      }
    }
  ]
}
```

- Evaluate **deny rules first**; a matching deny is absolute.
- Allow rules are OR-ed. No allow match ⇒ `defaultEffect` (deny).
- `resourceType` / `action` may be `"*"`.
- Conditions compose with `all` / `any`.
- Ops: `eq`, `neq`, `in`, `contains`, `exists`, `gt`, `gte`, `lt`, `lte`.
- Values beginning with `$` are references: `$resource.ownerId`,
  `$subject.sub`, `$subject.claims.tenant`.
- Keep rule ids stable — they appear in decision logs and dashboards.

### Anti-patterns

- Using payload `_type` to select a policy (the registry owns that).
- Allowing on the absence of an attribute; treat missing data as deny.
- Broad `resourceType: "*"` allow rules.

## 2. Mask policies

`mask-policies/*.json`

```json
{
  "version": "1.0",
  "policies": {
    "journey.account.read": {
      "default": "none",
      "fields": {
        "accountNumber": { "mode": "partial", "keepSuffix": 4 },
        "holder.email": { "mode": "partial", "keepPrefix": 1, "preserveDomain": true },
        "ssn": { "mode": "full" }
      }
    }
  }
}
```

- `default` applies to unlisted leaf fields: `none` or `full`.
- Partial requires explicit parameters; a bare partial fails validation.
- Locked fields (`ssn`, `pan`, `cvv`, `cardNumber`) must be `full`.
- `rejectFields` blocks write requests containing those fields.
- Changing the exact masked output is a contract change; expect downstream tests
  to pin it.

## 3. Registry entries

`registry/*.json`

```json
{
  "version": "1.0",
  "defaultUnregistered": "deny",
  "endpoints": [
    {
      "id": "get-account",
      "service": "accounts",
      "method": "GET",
      "path": "/accounts/{accountId}",
      "resourceType": "account",
      "action": "read",
      "resourceId": { "from": "path", "name": "accountId" },
      "resourceSource": "pip",
      "attributes": ["ownerId", "region", "status"],
      "maskPolicy": "journey.account.read",
      "maskErrors": true
    }
  ]
}
```

- `service` is required for per-service rendering; the renderer keeps only
  endpoints whose `service` matches the requested service.
- Type and identity come from the route; payload `_type` is only a cross-check.
- `resourceSource`: `pip` for existing resources, `body` for creation, `both`
  when the payload carries some fields.
- `attributes` is a projection — list only what the policy reads.
- Every endpoint needs fixtures: allow, deny and (if applicable) mismatch.

## 4. Data-quality rules

`dq/*.json`

```json
{
  "version": "1.0",
  "rules": [
    { "id": "payment.amount.positive", "resourceType": "payment",
      "field": "amount", "op": "gt", "value": 0, "blocking": true }
  ]
}
```

- Default is observe-only; `blocking: true` rejects.
- Prefer quarantine + alert over rejection for statistical rules.
- Ops: `gt`, `gte`, `lt`, `lte`, `eq`, `pattern`, `maxLength`, `type`.

## 5. Environment and service overlays

`env/<env>/overrides.json` and `services/<service>/overrides.json` share this
schema:

```json
{
  "environment": "prod",
  "bundle": {
    "defaultUnregistered": "deny",
    "disableRules": ["rule.id"],
    "disableDQRules": ["dq.rule.id"],
    "disableEndpoints": ["endpoint-id"],
    "maskPolicies": {
      "journey.account.read": { "default": "full", "fields": {} }
    }
  }
}
```

Unknown disable ids fail the render. Mask policy overrides must name an existing
policy and are re-validated (locked fields included) before a bundle is emitted.
Overlays may **not** change failure modes, filter order or set
`defaultUnregistered: allow` in production.

## 6. Rendering and conformance

```bash
bundle -src . -env prod -service accounts -out dist/accounts
conformance -bundle dist/accounts -fixtures tests/fixtures -service accounts -v
```

Rendering is deterministic: identical sources produce the same digest, recorded
in `dist/<service>/manifest.json`. Conformance runs fixtures for the service and
asserts decisions, reasons and masked fields.

## 7. Change checklist

- [ ] `make validate`
- [ ] Decision logs would identify the change (stable ids, no renames)
- [ ] Fixtures updated and passing in the pipeline
- [ ] Mask output asserted exactly
- [ ] No locked field relaxed
- [ ] Rollback digest recorded in the PR
