# controls-rules

Delivery-owned authorization rules, mask policies, endpoint registry entries,
DQ rules and environment overlays for the controls sidecar.

This repository produces **signed, immutable bundles**. The sidecar never reads
this repo directly; the pipeline resolves layering, validates against the
published contracts, runs conformance tests, and emits one bundle per service.

## Layout

```
policies/         authorization rules (JSON) or *.cedar (Cedar engine)
mask-policies/    field masking per journey
registry/         route → resource binding per service
dq/               request data-quality rules
env/{dev,staging,prod}/   environment overlays
services/<service>/       per-service overlays (optional)
tools/validate.py local validation (stdlib only)
dist/             rendered bundles (generated, not committed)
```

## Workflow

1. Branch, edit rules/policies/registry.
2. `make validate` locally.
3. PR: CI runs validation and the conformance gate; Jenkins renders the bundle
   (`bundle`) and runs the same checks before signing.
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
  Cedar policies likewise deny unless a `permit` matches.
- **Never relax locked fields.** `ssn`, `pan`, `cvv`, `cardNumber` are
  `full` only; validation fails otherwise.
- **No secrets or payloads in this repo.** Rules reference fields, never values
  from production data.
- **Every registry entry needs fixtures** (allow, deny, mismatch) before merge.

See [`docs/AUTHORING.md`](docs/AUTHORING.md) for the rule language. Normative
schemas live in the `controls-core` repo under `contracts/`.

## Local validation

```bash
make validate      # stdlib-only JSON/invariant checks
make render        # bundle -src . -env $ENV -service $SERVICE
make conformance   # conformance -bundle dist/$SERVICE -fixtures tests/fixtures
```

`validate` needs only Python 3. `render`/`conformance` need the
`controls-tools` image (or the binaries on `PATH`); the Jenkins job uses the
pinned image. See `controls-core/docs/PIPELINE.md`.
