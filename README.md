# controls-rules

Delivery-owned authorization rules, mask policies, endpoint registry entries,
DQ rules and environment overlays for the controls sidecar.

This repository produces **signed, immutable bundles**. The sidecar never reads
this repo directly; the pipeline resolves layering, validates against the
published contracts, runs conformance tests, and emits one bundle per service.

## Layout

```
policies/         authorization rules (deny-first)
mask-policies/    field masking per journey
registry/         route → resource binding per service
dq/               request data-quality rules
env/{dev,staging,prod}/   environment overlays
tools/validate.py local validation (stdlib only)
```

## Workflow

1. Branch, edit rules/policies/registry.
2. `make validate` locally.
3. PR: CI runs validation + locked-field checks + conformance.
4. Merge: pipeline renders the effective bundle, signs it, records the digest.
5. Deploy: bundle digest is pinned in the service's deployment.
6. Rollback: redeploy the previous digest — no application rebuild.

## Ownership

| Path | Owner | Reviewers |
|---|---|---|
| `policies/` | Delivery | Delivery + security |
| `mask-policies/` | Delivery | Delivery + security (relaxations), data owner |
| `registry/` | Delivery merges | Service team (mapping), core (contract) |
| `dq/` | Delivery | Delivery + data steward |
| `env/` | Delivery | Delivery |

## Rules of the road

- **Deny-first.** `defaultEffect` is `deny`; allow rules must be justified.
- **Never relax locked fields.** `ssn`, `pan`, `cvv`, `cardNumber` are
  `full` only; validation fails otherwise.
- **No secrets or payloads in this repo.** Rules reference fields, never values
  from production data.
- **Every registry entry needs fixtures** (allow, deny, mismatch) before merge.

See [`docs/AUTHORING.md`](docs/AUTHORING.md) for the rule language. Normative
schemas live in the `controls-core` repo under `contracts/`.

## Local validation

```bash
make validate
```

Requires only Python 3; the validator checks JSON syntax, unique ids, mask
policy references, locked fields and production guardrails.
