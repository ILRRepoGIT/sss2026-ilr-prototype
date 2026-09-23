# Instructions for the agent with GitHub push access — v6.0-rc9 (incremental, on top of the pushed rc7)

Purpose: bring `ILRRepoGIT/sss2026-ilr-prototype` from the pushed `v6.0-rc7` (94b66a8) to `v6.0-rc9`. Same branch (`production/v6.0`), four more commits, two more annotated tags (`v6.0-rc8`, which was cut but never pushed, and `v6.0-rc9` on top of it). `main` is not touched. The bundle is *incremental*: it contains only what rc7 lacks, and can only be applied to a clone that already has `v6.0-rc7` from GitHub. The earlier `…_V6.0-rc8_incremental.gitbundle` is superseded and must not be used.

What rc8 is: the corrections for the production pilot's three findings at the small and special schools (23 Sep 2026) — the one-pupil narrative hold in every module (EN-08 extended), the figure check made aware of the profile charts' blanked bars, the overview note without its largest/smallest sentence when a year bar is blank (EN-12; Framework v2.16; pipeline 0.31.1).

What rc9 is: the corrections for the linguist/tester review of the seven rc7 pilot reports (23 Sep 2026) — four rules of the Welsh engine brought into line with the Framework's own rulings (immutable sport names on every path, the runner-up sentence's adjective, the conjunction after "a", the object of "dewisodd"), the guide's answers opened for printing, the printed footer moved into the page margin, the gender-exempt appendix table with an All column only, and untranslated profile data values marked pending (Framework v2.17; pipeline 0.32.0). **Both tags change files that take part in a build**, so the release manifest differs from rc7's; the runbook's Phase B check is repeated at rc9 — with the Welsh corpus expected to MOVE by the recorded ruling (the runbook gives the expected counts) and the English unchanged.

## Inputs

In `Data_Report_Outputs\SSS2026_V6.0_Production_Deployment\`:

- `sss2026-ilr-prototype_V6.0-rc9_incremental.gitbundle` and its `.sha256`. Check the sha256 first.

## Steps

```
# 1. a clone that has rc7 (a fresh clone is simplest)
git clone https://github.com/ILRRepoGIT/sss2026-ilr-prototype.git
cd sss2026-ilr-prototype
git checkout main                                                        # stay on main: git refuses to fetch into a branch that is checked out
git fetch origin --tags
git rev-parse v6.0-rc7^{commit}                                          # expect 94b66a85458d7b25fad8b756a3025bc9d3e46ab9

# 2. verify the bundle against this clone, then bring in the branch and the two tags
git bundle verify ../sss2026-ilr-prototype_V6.0-rc9_incremental.gitbundle   # lists prerequisite 94b66a8 — which this clone has
git fetch ../sss2026-ilr-prototype_V6.0-rc9_incremental.gitbundle production/v6.0:production/v6.0
git fetch ../sss2026-ilr-prototype_V6.0-rc9_incremental.gitbundle tag v6.0-rc8
git fetch ../sss2026-ilr-prototype_V6.0-rc9_incremental.gitbundle tag v6.0-rc9

# 3. sanity checks
git merge-base --is-ancestor origin/production/v6.0 production/v6.0 && echo "fast-forward from the pushed rc7: OK"
git log --oneline origin/production/v6.0..production/v6.0                # expect four commits, the last "Release v6.0-rc9 … (release manifest)"
git describe --tags --exact-match production/v6.0                        # expect v6.0-rc9
git rev-parse v6.0-rc8^{commit}                                          # expect e5b5869c… (rc8, an ancestor of rc9)
git diff --stat origin/production/v6.0 production/v6.0 | tail -1         # about 30 files: pipeline/, web/, tests/, config/01_Framework_v2.16/v2.17.xlsx, config/welsh_lexicon.json, prod/, docs/, README, the compliance record, the manifest
git diff --stat origin/production/v6.0 production/v6.0 -- pipeline web config prod tests | tail -1   # rc8 and rc9 DO change build files — expected
git ls-tree -r --name-only production/v6.0 | grep -iE "\.parquet$|cleansed_export|response_export|register\.(csv|json)$"   # must print nothing

# 4. push (fast-forward of the branch, plus the two tags; no force, nothing to main)
git push origin production/v6.0
git push origin v6.0-rc8
git push origin v6.0-rc9

# 5. confirm
git ls-remote origin | grep -E "production/v6.0|v6.0-rc"
```

## What to report back

The `ls-remote` lines (branch and every `v6.0-rc*` tag with their hashes), the output of step 3, and the bundle sha256 you verified. If `git bundle verify` says a prerequisite is missing, the clone does not have rc7 — run `git fetch origin --tags` and try again; if it still fails, report the message rather than working around it.

## What NOT to do

No rebase, squash, amend or force-push: each tag names the exact commit whose files its release manifest hashes, and the runner's rule-1 check requires HEAD to carry the tag. Do not push the dataset, the register or the pilot evidence. Do not delete or move the earlier tags.
