# SSS2026 Interactive Learning Reports — operations runbook (build, check, publish)

Version 1.0 · 22 September 2026 · Industryline Research for Sport Wales · companion to the Azure provisioning guide

This runbook is what the operator runs on the build VM once the provisioning guide has been completed and `vm-bootstrap.sh` has printed "release manifest verified". Every command is given in full. The order matters: nothing becomes reachable by a school until the last phase, and each phase ends with a check that must pass before the next begins. Where a step needs a human decision it says so and stops.

Throughout, `$ILR_REPO`, `$ILR_VENV` and the storage/vault names come from `/etc/profile.d/ilr.sh`, written by the bootstrap; open a fresh login shell (or `source /etc/profile.d/ilr.sh`) before starting. All Python commands run from `$ILR_REPO`.

```
cd $ILR_REPO && source $ILR_VENV/bin/activate
export RELEASE=v6.0-rc1                  # the tag the VM was bootstrapped at (v6.0-rc1 today; the owner cuts v6.0 with tools/cut_release.sh)
export EVID=/data/ilr/evidence            # private: attestations, bundles, locks, ledger
export OUT=/data/ilr/out                  # the served trees (release + entry pages)
export WORK=/data/ilr/work                # per-job scratch, deleted job by job
export DATASET=/data/ilr/private/SSS2026_pupil_stage2_full_cleaned.parquet
```

---

## Phase A — the inputs (once)

**A1. The dataset.** Copy the parquet from the private storage account into `/data/ilr/private/` and verify it. The runner checks the hash again before every run and refuses on a mismatch.

```
mkdir -p /data/ilr/private && chmod 700 /data/ilr/private
az login --identity
az storage blob download --account-name $ILR_DATA_ACCOUNT --container-name dataset --auth-mode login \
   --name SSS2026_pupil_stage2_full_cleaned.parquet --file $DATASET
sha256sum $DATASET     # must print 802eda98fdeef512cce11e11aa38a45df5b0f33beb81b505acfc4ce9bbe13625
```

**A2. PLASC 2026.** The official school names come from the PLASC January 2026 workbook bundled with the cleansing handover (`06_pipeline/plasc2026.xlsx`). Copy it beside the dataset.

**A3. The recipient register** — the definitive report universe (review P0.2). Built from the dataset and PLASC; nothing is typed by hand.

```
python -m prod.register build $DATASET /data/ilr/private/register --plasc /data/ilr/private/plasc2026.xlsx
cat /data/ilr/private/register/register_summary.json
```

On the 22 September dataset this gives 1,016 schools: 786 eligible, 23 below the rule-of-five threshold (no report), 207 held until the translator's four sheet-53 local-authority rows exist (`held_la_name_cy`; re-run `register build` after the rows are in the framework and the runner picks them up under the same tag). Upload the three register files to the `register` container so the universe is on record before anything is built:

```
az storage blob upload-batch --account-name $ILR_DATA_ACCOUNT --destination register/$RELEASE --source /data/ilr/private/register --auth-mode login
```

**A4. The link key.** Nothing to do: the runner reads it from Key Vault through the VM's identity. Check once that it can: `az keyvault secret show --vault-name $ILR_KEY_VAULT --name $ILR_LINK_SECRET --query attributes.enabled` prints `true`. Never print the value.

---

## Phase B — reproduction check (the three V5.1 schools)

Before building anything new, prove that this machine reproduces the reports the owner has already reviewed. The three V5.3 corpus locks are in the repository (`docs/V5.3_schools/<school>/lock_<school>_v8.json`); build the same three schools and assert against them.

```
mkdir -p /data/ilr/private/v53_locks
for s in new-inn-primary-school castell-alun-high-school ysgol-bro-pedr; do
  cp docs/V5.3_schools/$s/lock_${s}_v8.json /data/ilr/private/v53_locks/ 2>/dev/null || \
  cp docs/V5.3_schools/$s/bundle/lock_${s}_v8.json /data/ilr/private/v53_locks/
done
python -m prod.runner run --release $RELEASE --register /data/ilr/private/register/register.json --dataset $DATASET \
   --out $OUT --evidence $EVID --work $WORK --concurrency 3 --schools 6782320,6644017,6675500 \
   --key-vault $ILR_KEY_VAULT --jsdom $JSDOM \
   --previous-locks /data/ilr/private/v53_locks \
   --lock-ruling "production release $RELEASE asserted against the V5.3 lock: client, template and Framework v2.14 changes only; corpus unchanged"
```

Expected: three lines `built … (69/72, mode dev)` and, in each job's evidence (`$EVID/$RELEASE/<slug>/validation-summary.txt` and `job.log`), the note "0 of N states moved from the previous lock". If a state moved, stop: the machine does not reproduce V5.1 and the difference must be explained before anything else is built (Python or Node version, a dependency, the dataset).

Then the checks:

```
python -m prod.checks rollup    --evidence $EVID --release $RELEASE
python -m prod.checks reconcile --evidence $EVID --release $RELEASE --register /data/ilr/private/register/register.json --dataset $DATASET
python -m prod.checks served-gate --evidence $EVID --release $RELEASE --site $OUT/$RELEASE --all-chunks
python -m tests.browser.chunked_probe $OUT/$RELEASE /2026/$(python - <<'EOF'
import json,glob; print(json.load(open(glob.glob("/data/ilr/evidence/*/new-inn-primary-school-6782320/attestation.json")[0]))["token"])
EOF
)/ --json $EVID/$RELEASE/chunked_probe_newinn.json --shots $EVID/$RELEASE/probe_shots
```

`reconcile` will list the eligible schools not yet built as "missing" at this point — expected; it must show zero "extra" and no count problems. The rollup must say `uniform: true` and `ok: true`; the served gate `ok: true`; the probe `PASS`.

---

## Phase C — the school pilot (20 schools) and the timings

Twenty schools chosen by the runner across primary/secondary/combined and three size bands, built with the Chromium render probe on so that the A4 print output of each is in the evidence for the human checks. This is also where the per-job time and memory on this VM are measured.

```
python -m prod.runner run --release $RELEASE --register /data/ilr/private/register/register.json --dataset $DATASET \
   --out $OUT --evidence $EVID --work $WORK --concurrency 20 --sample 20 --seed 2026 --probe \
   --key-vault $ILR_KEY_VAULT --jsdom $JSDOM
python -m prod.checks rollup --evidence $EVID --release $RELEASE
python -m prod.runner status --evidence $EVID --release $RELEASE
```

Read the mean and maximum `seconds` from the rollup and the peak memory from `/data/ilr/evidence/$RELEASE/<slug>/job.log` (`Maximum resident set size` is not recorded by the runner; `free -g` while the run is on, or `ps -o rss` on the workers, is enough). Set the full-run concurrency so that concurrency × peak-per-job stays under 75 % of the VM's memory and about one job per vCPU less a little headroom: on the D64as_v5 (64 vCPU, 256 GiB) with 2.5 GiB peaks that is about 48–56; the runner's default is cores − 2 and it also pauses new jobs when free memory drops under 3 GiB.

Stage the pilot into private storage and run the served gate against it over HTTP through Front Door — this exercises the real serving path with nothing yet reachable by a school (the entry pages are not in `$web` until Phase F):

```
python -m prod.publish stage --release $RELEASE --out $OUT --account stsss2026ilrweb --evidence $EVID
python -m prod.publish verify-staging --release $RELEASE --evidence $EVID --account stsss2026ilrweb
```

Human checks on the pilot (they are what the machine cannot do): the linguist's sample method applied to at least six of the twenty (small schools first — the singular and low-count forms), the owner's read of the print PDFs in `probe/`, and the English figures spot-checked against the data tables for two schools. Findings that need a workbook or code change mean a new tag and a return to Phase B; findings that are questions go on the flags register.

---

## Phase D — the full run

```
python -m prod.runner run --release $RELEASE --register /data/ilr/private/register/register.json --dataset $DATASET \
   --out $OUT --evidence $EVID --work $WORK --concurrency 48 --all \
   --key-vault $ILR_KEY_VAULT --jsdom $JSDOM 2>&1 | tee -a /data/ilr/evidence/$RELEASE/full_run.log
```

The run is resumable: schools already `built` under this release are skipped, so an interrupted run is simply started again with the same command. A school that fails is recorded in the ledger with the reason (`python -m prod.runner status …`; `python -m prod.ledger export $EVID/$RELEASE/ledger.sqlite $EVID/$RELEASE/ledger_export`). Read every failure. The expected kinds are the ones the plan predicts: a template path the prototype never exercised (a missing lexicon entry, a held sentence) — those are fixed in the workbook by its owner, never in code, and the affected schools are rebuilt under the tag that carries the corrected workbook (rule 8: that is a new tag and, strictly, a full regeneration; for a lexicon row that changes no existing school's corpus the locks prove it, and the rollup shows one tag across the set).

When it completes: the rollup, the reconciliation (now expecting zero missing) and the five-per-cent reproduction on a second tree (rule 10):

```
python -m prod.checks rollup    --evidence $EVID --release $RELEASE
python -m prod.checks reconcile --evidence $EVID --release $RELEASE --register /data/ilr/private/register/register.json --dataset $DATASET
python -m prod.runner rebuild --release $RELEASE --register /data/ilr/private/register/register.json --dataset $DATASET \
   --out $OUT --evidence $EVID --work $WORK --fraction 0.05 --seed 2026 --key-vault $ILR_KEY_VAULT --jsdom $JSDOM
```

`rebuild` writes `$EVID_rebuild/$RELEASE/rebuild_report.json`; every sampled school must be `identical` (every served file byte for byte; the timestamps live in the attestation, not the served files). The plan asks for the second build on a separately provisioned machine: run the same command on a second VM created from `infra/build-vm.bicep` if Sport Wales requires that literal reading; on the same VM it still proves determinism across processes and runs.

---

## Phase E — staging and verification of the whole set

```
python -m prod.publish stage          --release $RELEASE --out $OUT --account stsss2026ilrweb --evidence $EVID
python -m prod.publish verify-staging --release $RELEASE --evidence $EVID --account stsss2026ilrweb
```

Then the served gate through Front Door against the staged tree. Front Door serves `$web`, not `staging`, so for this check promote the release tree only (no entry pages) and point the gate at a temporary entry page written under a test token:

```
python -m prod.publish promote --release $RELEASE --evidence $EVID --account stsss2026ilrweb \
   --profile afd-sss2026-ilr --rg rg-sss2026-ilr --endpoint sss2026-reports --dry-run      # read the plan first
```

(`promote` without `--dry-run` also writes the entry pages — do not run it yet.) The full served-package check over HTTP is run after activation in Phase F within minutes, on 100 % of routes; before activation the file-mode check over the staged bytes (`verify-staging`) is the guarantee that what will be served is what was attested.

Evidence upload (private):

```
python -m prod.ledger export $EVID/$RELEASE/ledger.sqlite $EVID/$RELEASE/ledger_export
az storage blob upload-batch --account-name $ILR_DATA_ACCOUNT --destination evidence/$RELEASE --source $EVID/$RELEASE --auth-mode login
```

---

## Phase F — publication index, two-person approval, activation, live check

**F1. Move the publisher role.** Before the first activation, the `$web` write role is taken away from the VM's identity and given to the publisher (a named person's account or a second managed identity), so that a build cannot publish itself:

```
az role assignment delete --assignee <vm principal id> --role "Storage Blob Data Contributor" --scope "<web account id>/blobServices/default/containers/\$web"
az role assignment create --assignee <publisher> --role "Storage Blob Data Contributor" --scope "<web account id>/blobServices/default/containers/\$web"
```

The publisher then runs F2–F4 (`az login` as themselves, or on a machine with the second identity).

**F2. The publication index.** Only reports whose ledger status is `verified` go in; a dev-mode report is refused unless a signed waiver from the report owner is supplied (rule 9 — until the translator's remaining values and the owner's D69 are in the framework, every build is a dev build, so this is the decision point):

```
python -m prod.publish index --release $RELEASE --evidence $EVID --approver "<name 1>" --approver2 "<name 2>" [--waiver /data/ilr/private/waiver_$RELEASE.txt]
```

The index (`publication_index.json`) carries its own sha256, the two approvers and the waiver's hash. Both approvers read the refused list and the count before F4.

**F3. The distribution list.** The CMS / email list of links, one per school (bearer links — confidential; the file is written mode 0600):

```
python -m prod.checks link-export --evidence $EVID --release $RELEASE --base-url https://reports.schoolsportsurvey2026.co.uk \
   --register /data/ilr/private/register/register.json --out /data/ilr/private/links_$RELEASE.csv
```

The list contains every school in the register, including the below-threshold and held schools with an empty URL and their status, so that no school is an unexplained gap (review P0.10). The join to the schools' contact details happens in Industryline's own systems on `school_id`; one row per school, exact.

**F4. Activation.** Server-side copy of the release tree, then the entry pages, then the edge purge:

```
python -m prod.publish promote --release $RELEASE --evidence $EVID --account stsss2026ilrweb \
   --profile afd-sss2026-ilr --rg rg-sss2026-ilr --endpoint sss2026-reports
```

**F5. The live check, immediately, on every route:**

```
python -m prod.checks served-gate --evidence $EVID --release $RELEASE --site https://reports.schoolsportsurvey2026.co.uk --sample 40
```

This fetches every entry page (headers, bytes, identity) and every chunk of a stratified sample of 40 reports. Any problem: withdraw the affected report at once (`prod.publish withdraw …`), or roll the whole release back (`prod.publish rollback --to <previous>`), before any link is sent. Record the result in the compliance record with the tag, the dataset hash, the index sha256 and the date.

Only after F5 passes are the links sent to schools.

---

## Afterwards

Run the live check weekly for the life of the publication (`served-gate … --sample 40`), and after any change to Front Door or the storage account. Any change to the content — a lexicon row, a wording — is a new tag and a return to Phase B; the previous release's tree stays in `staging` and its evidence in the `evidence` container for the record. When the publication period ends, the plan's decommission step is: delete the entry pages (all links return 404), purge, then remove the release tree; keep the evidence.

Token compromise: create `sss2026-link-key-v2` in Key Vault, run the full run under a new tag with `--link-secret sss2026-link-key-v2` (nothing in a report changes, only the paths), activate, send the new links, delete the old entry pages. The rehearsal of this procedure on the pilot set, on the staging container, is part of Phase C.

---

## What stays with humans (and blocks a release-mode publication)

The translator: the sixteen frames pending since V4.16/V4.17 (fourteen artwork alt texts, the accessibility switch description, the glossary heading), the three loading-mask frames added in V6.0, the four sheet-22 qualifier rows from V5.0, the Welsh of the gap-year variant (`ui.overview_note_gap`), and — option A, decided 22 Sep 2026 — the four local-authority rows on sheet 53 in the dataset's spelling (Carmarthenshire, Conwy, Rhondda Cynon Taf, The Vale of Glamorgan): 207 eligible schools stay held until they exist. The report owner: the signed D69; EN-08 (one-pupil forms); a wording for schools whose responded year groups have a gap (the gap-year schools take EN-11 — decided 22 Sep 2026); confirmation of the three English loading-mask strings; the profile-matrix decision on the 16 special schools (built under the family their years imply, flagged `special`). Decided on 22 Sep 2026: schools with 5–13 responses receive a report. Sport Wales: the partial-response base-line wording, the artwork credit line, the regional sport partnership names (derived from the survey region), the FSM band and teacher-survey fields (still "To be confirmed"), and the O09/O10 disclosure sign-off the reports have carried since Prototype 3.
