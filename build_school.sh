#!/usr/bin/env bash
# One real school, end to end (real-school rounds V5.0 → V5.1; pipeline 0.28.0 → 0.29.1).
#
#   ./build_school.sh <slug> <school_id> <stage2.parquet> <private_inputs_dir> <yac_assets_dir> <fonts_dir> [<work_root>]
#
# The pupil-level export this writes under <private_inputs_dir>/<slug>/ is
# INPUT DATA: it never enters generated/, a kit or the repository.
#
#   1. the school's rows in the prototype's SmartSurvey layout (free text withheld)
#   2. the report package, staged, with the school's own profile
#      (SSS_SCHOOL_PROFILE) and output tree (SSS_GENERATED_DIR)
#   3. QA + the vendored gate pack v8; the school's corpus lock is EMITTED from
#      this build (SSS_PREVIOUS_LOCK=none on a first build — there is nothing
#      to assert yet; a rebuild asserts against the emitted lock)
#   4. the single-file bilingual report
set -euo pipefail
SLUG="${1:?slug}"; SID="${2:?school id}"; PARQ="${3:?stage2 parquet}"; PRIV="${4:?private inputs dir}"
YAC="${5:?yac assets dir}"; FONTS="${6:?fonts dir}"; WROOT="${7:-/home/claude/work/tmp/schools}"
cd "$(dirname "$0")"
export SSS_SCHOOL_PROFILE="config/schools/$SLUG.json"
export SSS_GENERATED_DIR="$WROOT/$SLUG/generated"
WD="$WROOT/$SLUG/wd"; X="$PRIV/$SLUG/SSS2026_cleansed_export_$SID.xlsx"
rm -rf "$WD" "$SSS_GENERATED_DIR"; mkdir -p "$WD" "$SSS_GENERATED_DIR"
python3 -m pipeline.cleansed_to_export "$PARQ" "$SID" "$X"                         | tee "$WD/s0.log"
python3 -m pipeline.staged_build states   "$X" "$WD" 0 4                            > "$WD/s1.log" 2>&1
python3 -m pipeline.staged_build states   "$X" "$WD" 4 8                            > "$WD/s2.log" 2>&1
python3 -m pipeline.staged_build states   "$X" "$WD" 8 12                           > "$WD/s3.log" 2>&1
python3 -m pipeline.staged_build assemble "$X" "$WD"                                > "$WD/s4.log" 2>&1
PREV="${SSS_PREVIOUS_LOCK:-none}"
# 0.29.1: the ruling the emitted lock records is the caller's (a rebuild
# names what moved the corpus); a first build keeps the first-emission text
FW=$(python3 -c 'from pipeline.common import latest_framework; print(latest_framework().stem.split("_")[-1])')
PV=$(python3 -c 'from pipeline.build_report_package import PIPELINE_VERSION_V2 as v; print(v)')
DEFAULT_RULING="first emission for $SLUG: the corpus lock of this school, Framework $FW, pipeline $PV"
RULING="${SSS_EMIT_LOCK_RULING:-$DEFAULT_RULING}"
SSS_PREVIOUS_LOCK="$PREV" SSS_EMIT_LOCK="$SSS_GENERATED_DIR/lock_${SLUG}_v8.json" \
SSS_EMIT_LOCK_RULING="$RULING" \
python3 -m pipeline.staged_build qa       "$X" "$WD"                                > "$WD/s5.log" 2>&1
python3 -m pipeline.staged_build write    "$X" "$WD"                                > "$WD/s6.log" 2>&1
python3 -m pipeline.build_html "$SSS_GENERATED_DIR/$SLUG.report.json" "$YAC" "$FONTS" config/cover_media \
        "$SSS_GENERATED_DIR/report.html"                                            > "$WD/s7.log" 2>&1
cat "$WD"/s[1-7].log
touch "$WD/done.flag"
