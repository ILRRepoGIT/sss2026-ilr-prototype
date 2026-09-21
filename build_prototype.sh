#!/usr/bin/env bash
# One-command prototype build (brief section 26).
#
#   ./build_prototype.sh <responses.xlsx> <assets_dir> <fonts_dir> <sw_logo.svg>
#
# Runs: synthetic fixture -> test suite -> report package (+QA outputs)
#       -> single-file interactive report.
set -euo pipefail

XLSX="${1:?usage: build_prototype.sh <responses.xlsx> <yac_assets_dir> <fonts_dir> <cover_media_dir>}"
ASSETS="${2:?yac assets dir required}"
FONTS="${3:?fonts dir required}"
COVER="${4:?cover media dir required (extracted from the title-page docx: word/media)}"

cd "$(dirname "$0")"

echo "== 1/4 synthetic edge-case fixture =="
python3 -m tests.make_synthetic_fixture tests/fixtures/synthetic.xlsx

echo "== 2/4 automated tests =="
SSS_REAL_XLSX="$XLSX" python3 -m pytest tests/ -q

echo "== 3/4 report package + QA outputs =="
python3 -m pipeline.build_report_package "$XLSX"

echo "== 4/4 single-file interactive report =="
python3 -m pipeline.build_html \
    generated/ysgol-penrhyn-dewi.report.json "$ASSETS" "$FONTS" "$COVER"

echo "done: generated/report.html"
