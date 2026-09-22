"""Production infrastructure for the SSS2026 Interactive Learning Reports.

The `pipeline` package builds ONE school's report package exactly as the
V4.15 prototype and the V5.x real-school rounds did; nothing in `prod`
changes a sentence, a number or a gate. `prod` is the machinery around it:

  release   the frozen release manifest (every participating file's sha256)
  register  the recipient register: which schools get a report, under which
            profile, from the canonical dataset and PLASC 2026
  tokens    the unguessable per-school link token (HMAC-SHA256, key in Key Vault)
  chunker   the served package: entry page + state chunks + index + envelopes,
            and the verifier that proves the chunks equal the monolith
  htmlcore  the entry page and the shared release assets
  runner    the fresh-start build runner (rules 1–11), concurrency, ledger,
            attestations
  ledger    the SQLite ledger of jobs, attestations and events
  checks    rollup, reconciliation, served-package gate, hosting verifier,
            link export
  publish   staging upload, promotion, purge, withdrawal, rollback

See docs/production/ for the provisioning guide and the operations runbook.
"""
PROD_VERSION = "1.0.0"
SCHEMA_VERSION = "1"        # served-package schema (envelope + chunk map)
