# Instructions for the agent with GitHub push access — v6.0-rc10 (incremental, on top of the pushed rc9)

Purpose: bring `ILRRepoGIT/sss2026-ilr-prototype` from the pushed `v6.0-rc9` (4be67a5) to `v6.0-rc10`. Same branch (`production/v6.0`), two more commits, one more annotated tag. `main` is not touched. The bundle is *incremental*: it contains only what rc9 lacks, and can only be applied to a clone that already has `v6.0-rc9` from GitHub.

What rc10 is: the two corrections from the rc9 pilot review (23 Sep 2026) — at the 23 schools whose whole-school view is suppressed (under five responses) the disclosure notices stacked on top of one another; they now flow in the page — and the one-response singular of the intro and FAQ sentences ("1 pupil response is included", EN-13, Framework v2.18; pipeline 0.32.1). **The tag changes files that take part in a build** (the page assets are per release), so the runbook's Phase B check is repeated at rc10; the Welsh corpus is unchanged, so the expected counts are the rc9 ones against the V5.3 locks.

## Inputs

In `Data_Report_Outputs\SSS2026_V6.0_Production_Deployment\`:

- `sss2026-ilr-prototype_V6.0-rc10_incremental.gitbundle` and its `.sha256`. Check the sha256 first.

## Steps

```
# 1. a clone that has rc9 (a fresh clone is simplest)
git clone https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git
cd sss2026-ilr-prototype
git checkout main                                                        # stay on main: git refuses to fetch into a branch that is checked out
git fetch origin --tags
git rev-parse v6.0-rc9^{commit}                                          # expect 4be67a57f27c5c42fc032ff9268abc1eafbbd099

# 2. verify the bundle against this clone, then bring in the branch and the tag
git bundle verify ../sss2026-ilr-prototype_V6.0-rc10_incremental.gitbundle   # lists prerequisite 4be67a5 — which this clone has
git fetch ../sss2026-ilr-prototype_V6.0-rc10_incremental.gitbundle production/v6.0:production/v6.0
git fetch ../sss2026-ilr-prototype_V6.0-rc10_incremental.gitbundle tag v6.0-rc10

# 3. sanity checks
git merge-base --is-ancestor origin/production/v6.0 production/v6.0 && echo "fast-forward from the pushed rc9: OK"
git log --oneline origin/production/v6.0..production/v6.0                # expect two commits, the last "Release v6.0-rc10 … (release manifest)"
git describe --tags --exact-match production/v6.0                        # expect v6.0-rc10
git diff --stat origin/production/v6.0 production/v6.0 | tail -1         # about 20 files: web/, pipeline/, prod/, tests/, config/01_Framework_v2.18.xlsx, config/welsh_lexicon.json, docs/, README, the compliance record, the manifest
git diff --stat origin/production/v6.0 production/v6.0 -- pipeline web config prod tests | tail -1   # rc10 DOES change build files — expected
git ls-tree -r --name-only production/v6.0 | grep -iE "\.parquet$|cleansed_export|response_export|register\.(csv|json)$"   # must print nothing

# 4. push (fast-forward of the branch, plus the tag; no force, nothing to main)
git push origin production/v6.0
git push origin v6.0-rc10

# 5. confirm
git ls-remote origin | grep -E "production/v6.0|v6.0-rc"
```

## What to report back

The `ls-remote` lines (branch and every `v6.0-rc*` tag with their hashes), the output of step 3, and the bundle sha256 you verified. If `git bundle verify` says a prerequisite is missing, the clone does not have rc9 — run `git fetch origin --tags` and try again; if it still fails, report the message rather than working around it.

## What NOT to do

No rebase, squash, amend or force-push: each tag names the exact commit whose files its release manifest hashes, and the runner's rule-1 check requires HEAD to carry the tag. Do not push the dataset, the register or the pilot evidence. Do not delete or move the earlier tags.
