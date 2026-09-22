# Instructions for the agent with GitHub push access — SSS2026 ILR V6.0 production branch

Purpose: put the V6.0 production infrastructure into `ILRRepoGIT/sss2026-ilr-prototype` on GitHub so the repository carries everything the production run needs. The work is delivered as a git bundle because the session that built it could read the repository but its git proxy refused to push.

What you are pushing: one branch, `production/v6.0`, that sits directly on top of the current `main` (commit `4f624eb`, V5.3 — "the three real-school reports rebuilt with the fourteen Welsh alt texts"), plus one annotated tag, `v6.0-rc2`, on the branch's head. `main` is not modified. Nothing in a standard report changed on this branch; it adds `prod/`, `infra/`, `docs/production/`, Framework v2.13–v2.14, pipeline 0.31.0, the chunked client and the release manifest.

## Inputs

In `Data_Report_Outputs\SSS2026_V6.0_Production_Deployment`:

- `sss2026-ilr-prototype_V6.0-rc2.gitbundle` (reassembled) and `sss2026-ilr-prototype_V6.0-rc2.gitbundle.sha256`. If only `gitbundle_parts/` is present, reassemble first: `copy /b <part00>+<part01>+… sss2026-ilr-prototype_V6.0-rc2.gitbundle` (Windows cmd) or `cat gitbundle_parts/*.part0* > sss2026-ilr-prototype_V6.0-rc2.gitbundle` (bash), then check the sha256 against the `.sha256` file.

## Steps

```
# 1. a fresh clone of the GitHub repository (or an existing clone that is clean and on main)
git clone https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git
cd sss2026-ilr-prototype
git fetch origin --tags

# 2. verify the bundle and bring in the branch and the tag
git bundle verify ../sss2026-ilr-prototype_V6.0-rc2.gitbundle        # must say the bundle is valid, and list refs it needs — all must exist in this clone
git fetch ../sss2026-ilr-prototype_V6.0-rc2.gitbundle production/v6.0:production/v6.0
git fetch ../sss2026-ilr-prototype_V6.0-rc2.gitbundle tag v6.0-rc2

# 3. sanity checks before pushing
git merge-base --is-ancestor origin/main production/v6.0 && echo "branch is on top of main: OK"
git log --oneline origin/main..production/v6.0                         # expect exactly: the V6.0 commit(s) and the "Release v6.0-rc2 … (release manifest)" commit
git describe --tags --exact-match production/v6.0                      # expect v6.0-rc2
git diff --stat origin/main production/v6.0 | tail -3
# nothing pupil-level: these must print nothing
git ls-tree -r --name-only production/v6.0 | grep -iE "\.parquet$|cleansed_export|response_export" 

# 4. push (branch and tag; do NOT push to main, do NOT force)
git push origin production/v6.0
git push origin v6.0-rc2

# 5. confirm on GitHub
git ls-remote origin | grep -E "production/v6.0|v6.0-rc2"
```

Optional, only if asked: open a pull request from `production/v6.0` into `main` titled "V6.0 — production infrastructure (prod/, infra/, docs/production/; Framework v2.14; pipeline 0.31.0)". Do not merge it; the owner reviews first.

## What to report back

The two `ls-remote` lines (branch and tag with their commit hashes), the output of step 3, and the bundle sha256 you verified. If `git bundle verify` reports a missing prerequisite, stop: the clone is behind the bundle's base (fetch `origin/main` again) or the bundle was made against a different history — report the message rather than working around it.

## What NOT to do

Do not rebase, squash or amend; the tag `v6.0-rc2` names the exact commit whose files the release manifest (`prod/release_manifest.json`) hashes — rewriting the commit does not change the hashes, but the runner's rule-1 check requires HEAD to carry the tag, so the tag must point at the pushed commit. Do not push any file from `Data_Report_Outputs` other than through the bundle. Do not add the dataset, the register or the pilot evidence to the repository.
