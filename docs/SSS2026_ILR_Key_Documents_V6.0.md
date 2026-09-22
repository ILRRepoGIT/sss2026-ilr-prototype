# SSS2026 Interactive Learning Report — V6.0: the production infrastructure (22 September 2026)

The machinery that turns the finalised prototype (V4.19 / V5.3: pipeline 0.30.0, Framework v2.12,
gate pack v8) into a published set of school reports — one independent, gate-checked build per school
from the finalised Stage 2 cleansed dataset, served as small entry pages plus verified state chunks
from private Azure storage behind Front Door, under an unguessable link per school on
`reports.schoolsportsurvey2026.co.uk`. Nothing in this round changes a sentence, a number or a gate:
the three V5.3 schools rebuilt through the production runner assert against their V5.3 corpus locks
with **0 states moved**. This document is the key record of the round; the operator documents are
`docs/production/SSS2026_ILR_Azure_Provisioning_Guide.md` (what the colleague sets up) and
`docs/production/SSS2026_ILR_Operations_Runbook.md` (what the operator runs, phase by phase).

## 1. Decisions of 22 September 2026 (owner) and how they are implemented

| Decision | Implementation |
|---|---|
| Dataset: the finalised Stage 2 v2 file (121,937 × 1,624, sha256 `802eda98…`) from cleansing handover v2.3 | The runner refuses any other dataset hash; the loose 8 Sep copy in "Pupil responses" (sha256 `1f970703…`, 1,598 columns, 382 columns with different values) is the superseded Stage 2 v1 and should be removed or marked |
| 8 or 16 cores, then a 64-vCPU quota approved; cut the build time | One Standard_D64as_v5 (64 vCPU / 256 GiB, UK South, 1 TB SSD); the runner builds about 50 schools at once (its default is cores − 2, with a memory guard); measured per-school cost on a two-core sandbox 209–424 s including all assurance → the ≈935 eligible schools in roughly 1½–2 hours |
| Unique URL per school, hosted on Industryline's SSS2026 website (agreed with Welsh Government) | HMAC-SHA256 link tokens (key in Key Vault, 130 bits), static hosting on a subdomain of `schoolsportsurvey2026.co.uk` through Front Door, `noindex`, no listing, 404 for an unknown link |
| Schools first; LA and regional reports to follow | The link scheme reserves `/2026/la/` and `/2026/region/`; the register and runner take a `family` field |
| Colleague sets up the estate from written instructions (subscription, resource group and quota already in place); GitHub carries the build | The provisioning guide (CLI steps and Bicep), the VM bootstrap script, the runbook; the repository at `ILRRepoGIT/sss2026-ilr-prototype`, branch `production/v6.0` (tag `v6.0-rc3`; rc2 is the commit the owner's agent pushed, rc3 the handover-review corrections to the operator documents, bootstrap and publication commands), delivered as a gitbundle in the deployment folder |

## 2. What was built

**The recipient register** (`prod/register.py`): the definitive report universe from the dataset and
PLASC January 2026 — 1,016 schools with a matched school id (121,881 accepted responses; 56 rows have
no reference school and get no report). Official names from PLASC for 1,013 schools; local-authority
Welsh names from Framework sheet 53; the Regional Sport Partnership from the survey region (the five
regions map one-to-one onto the five partnerships on sheet 53; the three V5.3 profiles are
reproduced exactly). Status on the 22 September data after the owner's decisions: **786 eligible**, 23 below the rule-of-five
threshold (`no_report_below_threshold`), **207 held** (`held_la_name_cy`: the four authorities whose dataset
spelling has no Welsh row on Framework sheet 53 — option A, the translator's rows, then built under the same
tag). The 58 schools with a year group inside their range that has no accepted response are eligible: EN-11
(owner, 22 Sep 2026) gives them the overview sentence without "All" (`ui.overview_note_gap`, Framework v2.14),
and Crickhowell High School (Years 7, 8, 10, 11; 244 responses) was built through the runner as the test —
8,064 states, every check clean. Sixteen special
schools are built under the family their years imply and flagged. The per-school profile the pipeline
reads is generated from the register row (`profile_for`); for the three real schools it is identical
to the hand-written V5.3 profile, field for field (the report-version field aside).

**The served package** (`prod/chunker.py`, `prod/htmlcore.py`, `web/app.js`, `web/template.html`):
the monolithic package is split into a core payload (everything but the states, plus the three
whole-school "none" states the default view reads) and content-hashed chunk files, one per
scope × gender group, capped at 6 MiB raw (Front Door compresses under 8 MB), each carrying an
identity envelope `{family, recipient, release, schema, binding}`. The entry page is the template
assembled exactly as `build_html` assembles the monolith (the same D79/D80 checks and the 2022-claim
gate) with the client script, fonts, artwork and cover images as shared, content-hashed release
assets under `/r/<tag>/assets/`. Entry page 428–444 KB against a 93–172 MB monolith; New Inn 38 chunks,
Castell Alun 42, Ysgol Bro Pedr 41; the largest chunk 6.29 MB raw, about 1 MB gzipped. The client
loads a view's chunks on demand and **fails closed**: a chunk is used only after its sha256 matches
the map in the entry page, its envelope matches the report's, its group and key count are right; a
late response from an earlier selection is discarded; nothing — no label, no figure — renders until
every needed chunk has verified; on failure a bilingual, retryable message is shown over a masked
page and printing is disabled. On the monolithic assurance copy (no chunk map) the client behaves
exactly as before. Three sheet-43 frames were added for the mask (`ui.loading_view`, `ui.load_error`,
`ui.retry`; Framework v2.13 from v2.12) and one for the gap-year overview sentence (`ui.overview_note_gap`,
Framework v2.14, EN-11) — English by Industryline under the owner's instruction, Welsh pending the translator. The chunk
verifier proves, for every school, that the chunks reconstruct the monolith's states key by key and
byte by byte (canonical JSON); the real-Chromium probe (`tests/browser/chunked_probe.py`) proves the
client's behaviour under the production Content-Security-Policy, with a failed request, a truncated
chunk and a chunk with another recipient's identity.

**The runner** (`prod/runner.py`) enforces the eleven rules of the deployment plan's build
contract: the release manifest (`prod/release.py`: the sha256 of every participating file, verified
against the tagged commit) before any job; an empty, job-owned work tree that is deleted afterwards
(the pupil-level export never outlives its job, even on failure); a job reads only the release
tree, the dataset filtered to its school and its register row; the full V5.3 assurance on every job
(QA with the school's corpus lock, the bundle's two stock reruns, the independent figure check, the
jsdom regression and provenance port, optionally the Chromium render probe) with any gate failure
outside the recorded pending/disputed list failing the job; write-once served and evidence trees;
one attestation per report as the single statement of identity; everything keyed by release; the
mode recorded and dev builds refused at publication; a `rebuild` command that builds a random
fraction again and compares every served file byte for byte; nothing written under `config/`.
Concurrency is a process pool with a memory guard; one run per release at a time; interrupted jobs
are cleaned and retried. The **attestation** carries the release identity, the profile and its hash,
the membership fingerprint (an HMAC over the school's response ids under a release-scoped secret kept
with the private evidence, never served), the binding hash the served envelope carries, the token,
the gate stamp and bundle outcome, the figure check, the jsdom results, the chunk index summary and
the inventory of every served file with sha256, MD5 and size; the served core is deterministic (the
build time and the two volatile stamp hashes stay in the attestation and the assurance copy).

**Checks at scale** (`prod/checks.py`): `rollup` (every attestation must carry the same identity
and gate outcome and be clean), `reconcile` (the universe: every eligible register row built exactly
once; the report's own accepted count, the export's row count and a fresh dataset count agree, per
school and over the set), `served-gate` (the artefact actually served — over a directory or over
HTTPS — re-fetched, hashes and envelopes checked, the state set rebuilt from the chunks and compared
with the private per-state index; headers, the 404 for an unknown token and for a listing, the shared
assets), `link-export` (one row per school in the register, built or not, with the URL; written
0600 — bearer links).

**Publication** (`prod/publish.py`): upload the release tree to the private `staging` container;
verify every blob's size and Content-MD5 against the attestations; the publication index (only
`verified` reports, dev mode refused without a signed waiver, an unverified release refused outright,
two named approvers, the index's own sha256); atomic activation (server-side copy of the immutable
release tree into `$web`, then one small `no-cache` entry page per school, then a Front Door purge)
so that a reader sees a complete old release or a complete new one, never a mixture; per-report
withdrawal (entry page and chunk directory deleted, edge purged) and whole-release rollback.

**The Azure estate** (`infra/`): Bicep for the two storage accounts (private data; web origin with
static website and a private staging container), Key Vault (the link key, custodian role), Log
Analytics, Front Door (Premium with a Private Link origin by default, Standard with an IP-range
firewall script as the documented alternative), the rule set (noindex and security headers, immutable
caching for `/r/`, revalidation for `/2026/`), the custom domain; the build VM with its identity,
network and disks; the role assignments (dataset read; register, evidence, ledger, staging write;
`$web` write and Front Door purge while the VM is also the publisher; Key Vault secrets read);
`deploy.sh` for the whole estate and `vm-bootstrap.sh` for the machine.

## 3. Measurements (two-core sandbox, concurrency 2)

| School | Responses | States (visible) | Runner job seconds | of which states / QA+write / HTML / assurance / served | Peak memory (single build) |
|---|---|---|---|---|---|
| New Inn Primary School | 272 | 7,884 (3,942) | 209 | 44 / 55 / 11 / 74 / 10 | 1.5 GiB |
| Castell Alun High School | 771 | 8,244 (4,809) | 391 | 102 / 85 / 63 / 92 / 14 | 1.6 GiB |
| Ysgol Bro Pedr | 439 | 8,208 (8,208) | 424 | 85 / 104 / 68 / 121 / 18 | 2.2 GiB |

The HTML step's 60 s at the two larger schools was the artwork preparation repeated per build; pipeline
0.31.0 caches the prepared WebP bytes per release (`SSS_ASSET_CACHE`, byte-identical output), which
is why New Inn's HTML step is 11 s. With the median school at 75 responses, the expectation for the
VM is 2–4 CPU-minutes per school all in; on the approved 64-vCPU quota (one Standard_D64as_v5, about 50 concurrent jobs) the eligible set is roughly one and a half to two hours.

## 4. What the rebuild through the runner proved

For each of the three schools: QA PASS with the prototype's stamp 69/72 (pending GOV-rerun/GOV-bundle,
disputed STK-caption-case), paths 17/18; the bundle's reruns dev 71/72 · release 72/75 with exactly the
three known items (STK-caption-case, CAT-values, GOV-mode); the rerun's emitted lock equal to the
build's baseline in all three parts; **0 states moved against the V5.3 lock** (New Inn 7,884, Castell
Alun 8,244, Ysgol Bro Pedr 8,208); the independent figure check all match; jsdom school regression
40/40; provenance 0 / 0 / 0 with the fixture toggle 1,152/1,152; the served package verified with
0 states moved and 38 / 42 / 41 chunks; the rollup uniform and clean; the reconciliation exact; the
served-package gate clean over the directory and over HTTP with the production headers; the browser
probe 11/11 in real Chromium under the production CSP.

## 5. What stays with humans

The translator: the two frames pending since V4.17 (`ui.a11y_switch_desc`, `ui.a11y_glossary_heading`), the three
loading-mask frames and the gap-year variant (`ui.overview_note_gap`), the four sheet-22 qualifier rows from V5.0, and
**four local-authority rows on sheet 53 in the dataset's spelling** (Carmarthenshire, Conwy, Rhondda Cynon Taf, The
Vale of Glamorgan — option A, owner 22 Sep 2026; 207 eligible schools are held until the rows exist). The owner: the
signed D69; EN-08; the profile matrix for special schools. Decided 22 Sep 2026: schools with 5–13 responses receive
a report; gap-year schools take EN-11. Sport Wales: partial-response wording, the artwork credit, the
partnership names, the FSM and teacher-survey fields, the O09/O10 sign-off. Operations: the Azure
subscription, quota, DNS and the custodian of the link key; the pilot's linguist sample and print
checks; the two approvers of the publication index.

Two departures from the 15 September plan, for the record: the runner reads the link key from Key
Vault by the VM's identity to compute tokens (the plan had the tokens precomputed and passed in; the
key never touches a file, a log or an output, and a precomputed-token mode is a small addition if
Sport Wales prefers it); and the membership fingerprint is keyed with a release-scoped secret rather
than the link key, so that rotating the link key changes only the paths and not a served byte.

## 6. Rebuild instructions

    git clone https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git && cd sss2026-ilr-prototype && git checkout production/v6.0
    python -m prod.release verify --tag v6.0                      # on the tagged commit; refuses a dirty tree
    python -m prod.register build <stage2.parquet> <register dir> --plasc <plasc2026.xlsx>
    ILR_KEY_VAULT=kv-sss2026-ilr python -m prod.runner run --release v6.0 --register <register dir>/register.json \
        --dataset <stage2.parquet> --out <out> --evidence <evidence> --work <work> --concurrency 12 --all --jsdom <node_modules/jsdom>
    python -m prod.checks rollup --evidence <evidence> --release v6.0
    python -m prod.checks reconcile --evidence <evidence> --release v6.0 --register <register.json> --dataset <stage2.parquet>
    python -m prod.checks served-gate --evidence <evidence> --release v6.0 --site <out>/v6.0 --all-chunks
    python -m prod.runner rebuild --release v6.0 … --fraction 0.05 --seed 2026

(then the publication steps of the runbook, Phases E–F). A development run in a working copy uses
`ILR_LINK_KEY=<test key>` and `--allow-dirty`; its attestations are marked `releaseVerified: false`
and can never be published.
