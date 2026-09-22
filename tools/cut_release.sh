#!/usr/bin/env bash
# Cut a production release tag (deployment plan rule 1 / rule 8).
#
#   tools/cut_release.sh v6.0 "one-line description"
#
# Writes prod/release_manifest.json for the tag (the sha256 of every file that
# takes part in a build), commits it, and tags that commit. The runner's rule-1
# check verifies, at the start of every run, that HEAD carries the tag, that the
# working copy is clean and that every listed file still has its hash. Any change
# after this — a lexicon row, a template fix — is a new tag and a full regeneration.
set -euo pipefail
TAG="${1:?tag, e.g. v6.0}"; MSG="${2:-release $TAG}"
cd "$(dirname "$0")/.."
if [ -n "$(git status --porcelain)" ]; then echo "working copy is not clean — commit or discard first"; exit 1; fi
if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then echo "tag $TAG already exists"; exit 1; fi
python3 -m prod.release build --tag "$TAG"
git add prod/release_manifest.json
git commit -q -m "Release $TAG — $MSG (release manifest)"
git tag -a "$TAG" -m "$MSG"
python3 -m prod.release verify --tag "$TAG"
echo "tagged $TAG at $(git rev-parse --short HEAD); push with: git push origin HEAD --tags"
