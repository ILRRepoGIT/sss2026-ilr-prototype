# Instructions for the agent with GitHub push access — v6.0-rc12 (incremental, on top of the pushed rc11)

Purpose: bring `ILRRepoGIT/sss2026-ilr-prototype` from the pushed `v6.0-rc11` (57f7878) to `v6.0-rc12`. Same branch (`production/v6.0`), two more commits, one more annotated tag. `main` is not touched. The bundle is *incremental*: it contains only what rc11 lacks, and can only be applied to a clone that already has `v6.0-rc11` from GitHub.

What rc12 is: the corrections from the full production run of 23 Sep 2026, in which 1,004 of the 1,016 schools built and 12 were refused by their own gates — the Welsh comparison sentence of e2 takes the D56 singleton form when the parent set is one pupil ("O gymharu, nid oedd yr unig ddisgybl ym Mlwyddyn 5.") and the parent audience's gender on its numerator ("dwy o'r 16 merch"); the register collapses whitespace in PLASC school names (six names carried a doubled space). Framework v2.20, pipeline 0.32.3. **The tag changes files that take part in a build**, so the runbook's Phase A3 (the register) and Phase B are repeated at rc12 and the whole set is regenerated under the one tag.

## Inputs

In `Data_Report_Outputs\SSS2026_V6.0_Production_Deployment\`:

- `sss2026-ilr-prototype_V6.0-rc12_incremental.gitbundle` and its `.sha256`. Check the sha256 first.

## Steps

```
# 1. a clone that has rc11 (a fresh clone is simplest)
git clone https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git
cd sss2026-ilr-prototype
git checkout main                                                        # stay on main: git refuses to fetch into a branch that is checked out
git fetch origin --tags
git rev-parse v6.0-rc11^{commit}                                         # expect 57f78784debdc61c76f806c5f83e4a4eb7f957c0

# 2. verify the bundle against this clone, then bring in the branch and the tag
git bundle verify ../sss2026-ilr-prototype_V6.0-rc12_incremental.gitbundle   # lists prerequisite 57f7878 — which this clone has
git fetch ../sss2026-ilr-prototype_V6.0-rc12_incremental.gitbundle production/v6.0:production/v6.0
git fetch ../sss2026-ilr-prototype_V6.0-rc12_incremental.gitbundle tag v6.0-rc12

# 3. sanity checks
git merge-base --is-ancestor origin/production/v6.0 production/v6.0 && echo "fast-forward from the pushed rc11: OK"
git log --oneline origin/production/v6.0..production/v6.0                # expect two commits; the last "Release v6.0-rc12 … (release manifest)"
git describe --tags --exact-match production/v6.0                        # expect v6.0-rc12
git rev-parse v6.0-rc12^{commit}                                         # expect the hash named in the deployment folder's copy of these instructions and in README_V6.0.md
git diff --stat origin/production/v6.0 production/v6.0 | tail -1         # about 16 files: pipeline/, prod/, tests/, config/01_Framework_v2.20.xlsx, config/welsh_lexicon.json, docs/, README, the compliance record, the manifest
git diff --stat origin/production/v6.0 production/v6.0 -- pipeline web config prod tests | tail -1   # rc12 DOES change build files — expected
git ls-tree -r --name-only production/v6.0 | grep -iE "\.parquet$|cleansed_export|response_export|register\.(csv|json)$"   # must print nothing

# 4. push (fast-forward of the branch, plus the tag; no force, nothing to main)
git push origin production/v6.0
git push origin v6.0-rc12

# 5. confirm
git ls-remote origin | grep -E "production/v6.0|v6.0-rc"
```

## What to report back

The `ls-remote` lines (branch and every `v6.0-rc*` tag with their hashes), the output of step 3, and the bundle sha256 you verified. If `git bundle verify` says a prerequisite is missing, the clone does not have rc11 — run `git fetch origin --tags` and try again; if it still fails, report the message rather than working around it.

## What NOT to do

No rebase, squash, amend or force-push: each tag names the exact commit whose files its release manifest hashes, and the runner's rule-1 check requires HEAD to carry the tag. Do not push the dataset, the register or the pilot evidence. Do not delete or move the earlier tags.
