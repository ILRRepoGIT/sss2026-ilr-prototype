# Instructions for the agent with GitHub push access — v6.0-rc8 (incremental, on top of the pushed rc7)

Purpose: bring `ILRRepoGIT/sss2026-ilr-prototype` from the pushed `v6.0-rc7` (94b66a8) to `v6.0-rc8`. Same branch (`production/v6.0`), two more commits, one more annotated tag. `main` is not touched. The bundle is *incremental*: it contains only what rc5 lacks, and can only be applied to a clone that already has `v6.0-rc7` from GitHub.

What rc8 is: the corrections for the production pilot's three findings at the small and special schools (23 Sep 2026) — the one-pupil narrative hold applied in every module (EN-08 extended), the independent figure check made aware of the profile charts' blanked bars, and the overview note without its largest/smallest sentence when a year bar is blank (EN-12, Framework v2.16; pipeline 0.31.1). **This tag changes files that take part in a build**, so its release manifest differs from rc7's; the runbook's Phase B reproduction check is repeated at rc8 before the pilot resumes.

## Inputs

In `Data_Report_Outputs\SSS2026_V6.0_Production_Deployment\`:

- `sss2026-ilr-prototype_V6.0-rc8_incremental.gitbundle` and its `.sha256`. Check the sha256 first.

## Steps

```
# 1. a clone that has rc5 (a fresh clone is simplest)
git clone https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git
cd sss2026-ilr-prototype
git checkout main                                                        # stay on main: git refuses to fetch into a branch that is checked out
git fetch origin --tags
git rev-parse v6.0-rc7^{commit}                                          # expect 94b66a85458d7b25fad8b756a3025bc9d3e46ab9

# 2. verify the bundle against this clone, then bring in the branch and the tag
git bundle verify ../sss2026-ilr-prototype_V6.0-rc8_incremental.gitbundle   # lists prerequisite 94b66a8 — which this clone has
git fetch ../sss2026-ilr-prototype_V6.0-rc8_incremental.gitbundle production/v6.0:production/v6.0
git fetch ../sss2026-ilr-prototype_V6.0-rc8_incremental.gitbundle tag v6.0-rc8

# 3. sanity checks
git merge-base --is-ancestor origin/production/v6.0 production/v6.0 && echo "fast-forward from the pushed rc7: OK"
git log --oneline origin/production/v6.0..production/v6.0                # expect two commits, the last "Release v6.0-rc8 … (release manifest)"
git describe --tags --exact-match production/v6.0                        # expect v6.0-rc8
git diff --stat origin/production/v6.0 production/v6.0 | tail -1         # about 20 files: pipeline/, web/app.js, tests/, config/01_Framework_v2.16.xlsx, config/welsh_lexicon.json, prod/, docs/, README, the compliance record, the manifest
git diff --stat origin/production/v6.0 production/v6.0 -- pipeline web config prod tests | tail -1   # rc8 DOES change build files — expected
git ls-tree -r --name-only production/v6.0 | grep -iE "\.parquet$|cleansed_export|response_export|register\.(csv|json)$"   # must print nothing

# 4. push (fast-forward of the branch, plus the tag; no force, nothing to main)
git push origin production/v6.0
git push origin v6.0-rc8

# 5. confirm
git ls-remote origin | grep -E "production/v6.0|v6.0-rc"
```

## What to report back

The `ls-remote` lines (branch and every `v6.0-rc*` tag with their hashes), the output of step 3, and the bundle sha256 you verified. If `git bundle verify` says a prerequisite is missing, the clone does not have rc7 — run `git fetch origin --tags` and try again; if it still fails, report the message rather than working around it.

## What NOT to do

No rebase, squash, amend or force-push: each tag names the exact commit whose files its release manifest hashes, and the runner's rule-1 check requires HEAD to carry the tag. Do not push the dataset, the register or the pilot evidence. Do not delete or move the earlier tags.
