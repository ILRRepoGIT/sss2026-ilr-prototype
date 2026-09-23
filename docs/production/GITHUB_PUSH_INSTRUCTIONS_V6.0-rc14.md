# Instructions for the agent with GitHub push access — v6.0-rc14 (incremental, on top of the pushed rc13)

Purpose: bring `ILRRepoGIT/sss2026-ilr-prototype` from the pushed `v6.0-rc13` (8bbc15f) to `v6.0-rc14`. Same branch (`production/v6.0`), two more commits, one more annotated tag. `main` is not touched. The bundle is *incremental*: it contains only what rc13 lacks, and can only be applied to a clone that already has `v6.0-rc13` from GitHub.

What rc14 is: the publication commands, rehearsed before the operator reaches them. `prod.publish stage` — the first Phase E command — could not run before this tag (its AzCopy sign-in's identity branch called itself without bound); rc14 corrects the sign-in, stages the entry pages with their headers, adds six unit tests, and the runbook now keeps the publisher's sign-in in its own Azure CLI configuration directory. No report-generating file changes (Framework v2.20, pipeline 0.32.3 unchanged); nothing is rebuilt — the production set is built at v6.0-rc12 and the VM checks out rc14 for the phases after the build. **This push is on the critical path: the operator needs rc14 on GitHub before Phase E.**

## Inputs

In `Data_Report_Outputs\SSS2026_V6.0_Production_Deployment\`:

- `sss2026-ilr-prototype_V6.0-rc14_incremental.gitbundle` and its `.sha256`. Check the sha256 first.

## Steps

```
# 1. a clone that has rc13 (a fresh clone is simplest)
git clone https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git
cd sss2026-ilr-prototype
git checkout main                                                        # stay on main: git refuses to fetch into a branch that is checked out
git fetch origin --tags
git rev-parse v6.0-rc13^{commit}                                         # expect 8bbc15fc1ce043810b5fb0b2c97c635028e77338

# 2. verify the bundle against this clone, then bring in the branch and the tag
git bundle verify ../sss2026-ilr-prototype_V6.0-rc14_incremental.gitbundle   # lists prerequisite 8bbc15f — which this clone has
git fetch ../sss2026-ilr-prototype_V6.0-rc14_incremental.gitbundle production/v6.0:production/v6.0
git fetch ../sss2026-ilr-prototype_V6.0-rc14_incremental.gitbundle tag v6.0-rc14

# 3. sanity checks
git merge-base --is-ancestor origin/production/v6.0 production/v6.0 && echo "fast-forward from the pushed rc13: OK"
git log --oneline origin/production/v6.0..production/v6.0                # expect two commits; the last "Release v6.0-rc14 … (release manifest)"
git describe --tags --exact-match production/v6.0                        # expect v6.0-rc14
git rev-parse v6.0-rc14^{commit}                                         # expect the hash named in the deployment folder's copy of these instructions and in README_V6.0.md
git diff --stat origin/production/v6.0 production/v6.0 | tail -1         # about 11 files: prod/publish.py, tests/test_publish.py, docs/, README, the compliance record, the flags, the manifest
git diff --stat origin/production/v6.0 production/v6.0 -- pipeline web config inputs | tail -1   # must print nothing — rc14 changes prod/ and tests/ only
git ls-tree -r --name-only production/v6.0 | grep -iE "\.parquet$|cleansed_export|response_export|register\.(csv|json)$"   # must print nothing

# 4. push (fast-forward of the branch, plus the tag; no force, nothing to main)
git push origin production/v6.0
git push origin v6.0-rc14

# 5. confirm
git ls-remote origin | grep -E "production/v6.0|v6.0-rc"
```

## What to report back

The `ls-remote` lines (branch and every `v6.0-rc*` tag with their hashes), the output of step 3, and the bundle sha256 you verified. If `git bundle verify` says a prerequisite is missing, the clone does not have rc13 — run `git fetch origin --tags` and try again; if it still fails, report the message rather than working around it.

## What NOT to do

No rebase, squash, amend or force-push: each tag names the exact commit whose files its release manifest hashes, and the runner's rule-1 check requires HEAD to carry the tag. Do not push the dataset, the register or the pilot evidence. Do not delete or move the earlier tags.
