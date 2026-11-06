# Changelog

## [0.1.0] — 2026-11-06

### Added

- Initial authorization rules for account reads and payment writes.
- Mask policies for account read (partial/full) and payment write
  (reject `pan`/`cvv`).
- Endpoint registry entries for `GET /accounts/{accountId}` and
  `POST /payments`.
- DQ rules for payment amount and currency, plus a non-blocking account email
  check.
- Environment overlays for dev, staging and prod.
- Local validator (`make validate`) covering JSON syntax, unique ids, mask
  policy references, locked fields, production guardrails and fixture shape.
- Fixtures for the account-read and payment-create journeys.
