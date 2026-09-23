# Instructions for the agent with GitHub push access — v6.0-rc13 (incremental, on top of the pushed rc12)

Purpose: bring `ILRRepoGIT/sss2026-ilr-prototype` from the pushed `v6.0-rc12` (c8c35d5) to `v6.0-rc13`. Same branch (`production/v6.0`), two more commits, one more annotated tag. `main` is not touched. The bundle is *incremental*: it contains only what rc12 lacks, and can only be applied to a clone that already has `v6.0-rc12` from GitHub.

What rc13 is: the resolution of the rc12 reconciliation stop (St Julian's: 228 responses in the dataset, 226 in the report — two with no usable year group; 98 such responses at 83 schools). No report-generating file changes: `prod/register.py` counts what the report accepts (rows with a resolved year; the dataset's count kept beside it) and `prod/checks.py` reconciles the report's accepted rows, the export rows and the register separately. Framework v2.20, pipeline 0.32.3 unchanged. The register is rebuilt at rc13 and the whole set is built under rc13 (the rc12 review builds are not reused).

## Inputs

In `Data_Report_Outputs\SSS2026_V6.0_Production_Deployment\`:

- `sss2026-ilr-prototype_V6.0-rc13_incremental.gitbundle` and its `.sha256`. Check the sha256 first.

## Steps

```
# 1. a clone that has rc12 (a fresh clone is simplest)
git clone https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git
cd sss2026-ilr-prototype
git checkout main                                                        # stay on main: git refuses to fetch into a branch that is checked out
git fetch origin --tags
git rev-parse v6.0-rc12^{commit}                                         # expect c8c35d575ba6b432d536bc965dd7e784c7caeaa9

# 2. verify the bundle against this clone, then bring in the branch and the tag
git bundle verify ../sss2026-ilr-prototype_V6.0-rc13_incremental.gitbundle   # lists prerequisite c8c35d5 — which this clone has
git fetch ../sss2026-ilr-prototype_V6.0-rc13_incremental.gitbundle production/v6.0:production/v6.0
git fetch ../sss2026-ilr-prototype_V6.0-rc13_incremental.gitbundle tag v6.0-rc13

# 3. sanity checks
git merge-base --is-ancestor origin/production/v6.0 production/v6.0 && echo "fast-forward from the pushed rc12: OK"
git log --oneline origin/production/v6.0..production/v6.0                # expect two commits; the last "Release v6.0-rc13 … (release manifest)"
git describe --tags --exact-match production/v6.0                        # expect v6.0-rc13
git rev-parse v6.0-rc13^{commit}                                         # expect the hash named in the deployment folder's copy of these instructions and in README_V6.0.md
git diff --stat origin/production/v6.0 production/v6.0 | tail -1         # about 12 files: prod/register.py, prod/checks.py, docs/, README, the compliance record, the flags, the manifest
git diff --stat origin/production/v6.0 production/v6.0 -- pipeline web config prod tests | tail -1   # rc13 changes prod/ only — expected
git ls-tree -r --name-only production/v6.0 | grep -iE "\.parquet$|cleansed_export|response_export|register\.(csv|json)$"   # must print nothing

# 4. push (fast-forward of the branch, plus the tag; no force, nothing to main)
git push origin production/v6.0
git push origin v6.0-rc13

# 5. confirm
git ls-remote origin | grep -E "production/v6.0|v6.0-rc"
```

## What to report back

The `ls-remote` lines (branch and every `v6.0-rc*` tag with their hashes), the output of step 3, and the bundle sha256 you verified. If `git bundle verify` says a prerequisite is missing, the clone does not have rc12 — run `git fetch origin --tags` and try again; if it still fails, report the message rather than working around it.

## What NOT to do

No rebase, squash, amend or force-push: each tag names the exact commit whose files its release manifest hashes, and the runner's rule-1 check requires HEAD to carry the tag. Do not push the dataset, the register or the pilot evidence. Do not delete or move the earlier tags.
