#!/bin/bash
# V5.3 real-school round: pipeline 0.30.0, Framework v2.12 (the fourteen Welsh alt texts, owner-supplied 22 Sep 2026),
# the V4.18 template — no English changed: every school asserts against its V5.2 lock (0 states expected to move).
cd /home/claude/work/sss2026-ilr-prototype
P=/home/claude/work/data/SSS2026_pupil_cleansing_handover_v2.3_2026-09-09/01_cleaned_files/SSS2026_pupil_stage2_full_cleaned.parquet
YAC="/home/claude/work/yca/yac images V4.16"; FONTS=/home/claude/work/git/sss2026-ilr-prototype/inputs/fonts
W=/home/claude/work/tmp/schools53; V52=/home/claude/work/tmp/schools52
for s in "new-inn-primary-school 6782320" "castell-alun-high-school 6644017" "ysgol-bro-pedr 6675500"; do
  set -- $s
  export SSS_PREVIOUS_LOCK=$V52/$1/generated/lock_$1_v8.json
  export SSS_EMIT_LOCK_RULING="V5.3 re-emission for $1: Framework v2.12 (Welsh for the fourteen Young Artists Competition alt frames, supplied by the owner 22 Sep 2026), pipeline 0.30.0, the V4.18 template — no state moved (asserted against the V5.2 lock)"
  ./build_school.sh $1 $2 $P /home/claude/work/data/inputs "$YAC" $FONTS $W > $W/$1.build.out 2>&1 || { echo "BUILD FAILED $1"; continue; }
  SSS_GENERATED_DIR=$W/$1/generated SSS_SCHOOL_PROFILE=config/schools/$1.json python3 -m pipeline.make_school_bundle $1 V5.3 > $W/$1.bundle.out 2>&1 || echo "BUNDLE FAILED $1"
  python3 -m pipeline.verify_school $P config/schools/$1.json $W/$1/generated/$1.report.json $W/$1/verify_figures.json > $W/$1.verify.out 2>&1 || echo "VERIFY FAILED $1"
  WD=$W/$1/wd
  REPORT=$W/$1/generated/$1.report.json python3 -m tests.jsdom.make_mini $WD > $WD/mini.log 2>&1
  JSDOM=/home/claude/work/tmp/jsdomenv/node_modules/jsdom WD=$WD node tests/jsdom/jsdom_school.js > $WD/jsdom_school.log 2>&1 || echo "JSDOM FAILED $1"
  JSDOM=/home/claude/work/tmp/jsdomenv/node_modules/jsdom WD=$WD OUT=browser_gate_jsdom.json node tests/jsdom/jsdom_provenance.js > $WD/jsdom_provenance.log 2>&1 || echo "PROVENANCE FAILED $1"
  python3 -m tests.browser.render_probe $WD $W/$1/probe > $WD/probe.log 2>&1 || echo "PROBE FAILED $1"
  echo "DONE $1"
done
touch $W/all.done
