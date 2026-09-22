# Instructions for the agent with GitHub push access — v6.0-rc4 (incremental, on top of the pushed rc2)

Purpose: bring `ILRRepoGIT/sss2026-ilr-prototype` from the pushed `v6.0-rc2` to `v6.0-rc4`. Same branch (`production/v6.0`), five more commits, two more annotated tags (`v6.0-rc3` — the handover-review corrections; `v6.0-rc4` — Framework v2.15, the four local-authority rows, every school in the full run). `main` is not touched. The bundle is *incremental*: it contains only what rc2 lacks, so it is small, and it can only be applied to a clone that already has `v6.0-rc2` from GitHub.

## Inputs

In `Data_Report_Outputs\SSS2026_V6.0_Production_Deployment\`:

- `sss2026-ilr-prototype_V6.0-rc4_incremental.gitbundle` and its `.sha256`. Check the sha256 first.

## Steps

```
# 1. a clone that has rc2 (a fresh clone is simplest)
git clone https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git
cd sss2026-ilr-prototype
git checkout main                                                        # stay on main: git refuses to fetch into a branch that is checked out
git fetch origin --tags
git rev-parse v6.0-rc2^{commit}                                          # expect 43bb4b8337d966efbf96caf75f12719c6918e25f

# 2. verify the bundle against this clone, then bring in the branch and the two tags
git bundle verify ../sss2026-ilr-prototype_V6.0-rc4_incremental.gitbundle   # lists prerequisite 43bb4b8 — which this clone has
git fetch ../sss2026-ilr-prototype_V6.0-rc4_incremental.gitbundle production/v6.0:production/v6.0
git fetch ../sss2026-ilr-prototype_V6.0-rc4_incremental.gitbundle tag v6.0-rc3
git fetch ../sss2026-ilr-prototype_V6.0-rc4_incremental.gitbundle tag v6.0-rc4

# 3. sanity checks
git merge-base --is-ancestor origin/production/v6.0 production/v6.0 && echo "fast-forward from the pushed rc2: OK"
git log --oneline origin/production/v6.0..production/v6.0                # expect five commits, the last "Release v6.0-rc4 … (release manifest)"
git describe --tags --exact-match production/v6.0                        # expect v6.0-rc4
git describe --tags --exact-match v6.0-rc3^{commit}                      # expect v6.0-rc3
git diff --stat origin/production/v6.0 production/v6.0 | tail -1         # about 15 files; nothing under web/ or pipeline/build_*
git ls-tree -r --name-only production/v6.0 | grep -iE "\.parquet$|cleansed_export|response_export|register\.(csv|json)$"   # must print nothing

# 4. push (fast-forward of the branch, plus the tags; no force, nothing to main)
git push origin production/v6.0
git push origin v6.0-rc3 v6.0-rc4

# 5. confirm
git ls-remote origin | grep -E "production/v6.0|v6.0-rc"
```

## What to report back

The `ls-remote` lines (branch, `v6.0-rc2`, `v6.0-rc3`, `v6.0-rc4` with their hashes), the output of step 3, and the bundle sha256 you verified. If `git bundle verify` says a prerequisite is missing, the clone does not have rc2 — run `git fetch origin --tags` and try again; if it still fails, report the message rather than working around it.

## What NOT to do

No rebase, squash, amend or force-push: each tag names the exact commit whose files its release manifest hashes, and the runner's rule-1 check requires HEAD to carry the tag. Do not push the dataset, the register or the pilot evidence. Do not delete or move `v6.0-rc2`; it stays as the record of what was first pushed.
