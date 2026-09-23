# Instructions for the agent with GitHub push access — v6.0-rc7 (incremental, on top of the pushed rc6)

Purpose: bring `ILRRepoGIT/sss2026-ilr-prototype` from the pushed `v6.0-rc6` (760d85e) to `v6.0-rc7`. Same branch (`production/v6.0`), two more commits, one more annotated tag. `main` is not touched. The bundle is *incremental*: it contains only what rc5 lacks, and can only be applied to a clone that already has `v6.0-rc6` from GitHub.

What rc7 is: the corrections from the colleague's provisioning preflight at rc6 — the Front Door rule set split so that no rule carries more than Azure's five actions (all six headers kept), the VM bootstrap taking the GitHub token at a prompt through an in-memory credential helper instead of a token-in-URL clone that git would have saved in `.git/config`, and provider registration added to the guide. No file that takes part in a build changed: the release manifest's file hashes are identical to rc5's and rc6's.

## Inputs

In `Data_Report_Outputs\SSS2026_V6.0_Production_Deployment\`:

- `sss2026-ilr-prototype_V6.0-rc7_incremental.gitbundle` and its `.sha256`. Check the sha256 first.

## Steps

```
# 1. a clone that has rc5 (a fresh clone is simplest)
git clone https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git
cd sss2026-ilr-prototype
git checkout main                                                        # stay on main: git refuses to fetch into a branch that is checked out
git fetch origin --tags
git rev-parse v6.0-rc6^{commit}                                          # expect 760d85efd41aa6684d3d68e961a5b5a817a1754e

# 2. verify the bundle against this clone, then bring in the branch and the tag
git bundle verify ../sss2026-ilr-prototype_V6.0-rc7_incremental.gitbundle   # lists prerequisite 760d85e — which this clone has
git fetch ../sss2026-ilr-prototype_V6.0-rc7_incremental.gitbundle production/v6.0:production/v6.0
git fetch ../sss2026-ilr-prototype_V6.0-rc7_incremental.gitbundle tag v6.0-rc7

# 3. sanity checks
git merge-base --is-ancestor origin/production/v6.0 production/v6.0 && echo "fast-forward from the pushed rc6: OK"
git log --oneline origin/production/v6.0..production/v6.0                # expect two commits, the last "Release v6.0-rc7 … (release manifest)"
git describe --tags --exact-match production/v6.0                        # expect v6.0-rc7
git diff --stat origin/production/v6.0 production/v6.0 | tail -1         # about 8 files: infra/afd-ruleset.sh, infra/main.bicep, infra/vm-bootstrap.sh, docs/, README, the compliance record, the manifest
git diff origin/production/v6.0 production/v6.0 -- prod/release_manifest.json | grep '^[-+] ' | grep -v '"tag"\|"releasedAt"\|"manifestSha256"' ; echo "(nothing above this line = no build file changed)"
git ls-tree -r --name-only production/v6.0 | grep -iE "\.parquet$|cleansed_export|response_export|register\.(csv|json)$"   # must print nothing

# 4. push (fast-forward of the branch, plus the tag; no force, nothing to main)
git push origin production/v6.0
git push origin v6.0-rc7

# 5. confirm
git ls-remote origin | grep -E "production/v6.0|v6.0-rc"
```

## What to report back

The `ls-remote` lines (branch and every `v6.0-rc*` tag with their hashes), the output of step 3, and the bundle sha256 you verified. If `git bundle verify` says a prerequisite is missing, the clone does not have rc6 — run `git fetch origin --tags` and try again; if it still fails, report the message rather than working around it.

## What NOT to do

No rebase, squash, amend or force-push: each tag names the exact commit whose files its release manifest hashes, and the runner's rule-1 check requires HEAD to carry the tag. Do not push the dataset, the register or the pilot evidence. Do not delete or move the earlier tags.
