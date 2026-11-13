#!/bin/bash
# Interleaved frame-cost measurement for two or more racer builds.
#
# Runs the normal 1080p benchmark workload alternately per build (so a busy
# host affects every build equally) and prints CPU time per measured frame,
# which stays comparable when vsync caps the frame rate or another process
# steals the CPU. CPU time includes the render thread, so texture upload and
# command recording are counted.
#
#   scripts/measure_frame_cost.sh baseline=/tmp/racer-base/build/racer candidate=./build/racer
#   REPETITIONS=6 SECONDS=12 scripts/measure_frame_cost.sh a=./build/racer b=./build/racer
#
# Options (environment): REPETITIONS (default 5), SECONDS_RUN (default 12),
# EXTRA_ARGS (default "--benchmark --autodrive").
set -u
repetitions=${REPETITIONS:-5}
run_seconds=${SECONDS_RUN:-12}
extra=${EXTRA_ARGS:---benchmark --autodrive}
if [ $# -lt 1 ]; then
  echo "usage: $0 [label=binary ...]" >&2
  exit 2
fi
for spec in "$@"; do
  binary=${spec#*=}
  if [ ! -x "$binary" ]; then
    echo "not executable: $binary" >&2
    exit 2
  fi
done
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
echo "label,rep,fps,frames,longest_ms,over_16.67ms,user_s,sys_s,cpu_ms_per_frame" | tee "$tmp/results.csv"
for rep in $(seq 1 "$repetitions"); do
  for spec in "$@"; do
    label=${spec%%=*}
    binary=${spec#*=}
    # shellcheck disable=SC2086
    out=$(/usr/bin/time -l "$binary" --smoke "$run_seconds" --background \
          --no-diagnostics --profile "$tmp/$label-$rep/profile.txt" $extra 2>&1)
    fps=$(sed -n 's/.*FPS=\([0-9.]*\).*/\1/p' <<<"$out" | head -1)
    frames=$(sed -n 's/.*Measured frames=\([0-9]*\).*/\1/p' <<<"$out" | head -1)
    longest=$(sed -n 's/.*longest_ms=\([0-9.]*\).*/\1/p' <<<"$out" | head -1)
    over=$(sed -n 's/.*over_16.67ms=\([0-9]*\).*/\1/p' <<<"$out" | head -1)
    if [ -z "${frames:-}" ]; then
      echo "$label,$rep,,,,,,," >&2
      echo "$label run $rep produced no measurement:" >&2
      tail -5 <<<"$out" >&2
      exit 1
    fi
    read -r user sys < <(awk '{for(i=1;i<=NF;i++){if($i=="user")u=$(i-1);if($i=="sys")s=$(i-1)}} END{printf "%.2f %.2f",u,s}' <<<"$out")
    cpu=$(awk -v u="$user" -v s="$sys" -v f="$frames" 'BEGIN{printf "%.2f",(u+s)/f*1000}')
    echo "$label,$rep,$fps,$frames,$longest,$over,$user,$sys,$cpu" | tee -a "$tmp/results.csv"
  done
done
echo
echo "median per label (CPU per measured frame):"
labels=$(awk -F, 'NR>1{print $1}' "$tmp/results.csv" | sort -u)
for label in $labels; do
  sorted=$(awk -F, -v l="$label" 'NR>1 && $1==l {print $9}' "$tmp/results.csv" | sort -n)
  awk -v l="$label" 'BEGIN{}{v[NR]=$1} END{
    n=NR;
    med=(n%2)?v[(n+1)/2]:(v[n/2]+v[n/2+1])/2;
    printf "  %-12s %8.2f ms  (n=%d, min %.2f, max %.2f)\n",l,med,n,v[1],v[n];
  }' <<<"$sorted"
done
