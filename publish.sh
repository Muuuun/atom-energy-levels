#!/bin/sh
# Recompute, redraw and publish the given species keys:  ./publish.sh "message" key1 key2 ...
set -e
msg="$1"; shift
python3 compute.py "$@" 2>&1 | grep -v "observed vs\|quantum defect\|ARC differs"
python3 plot.py "$@" 2>&1 | grep "docs/"
python3 build_site.py
python3 stats.py > /dev/null
git add -A
git commit -q -m "$msg

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -q origin main
git log --oneline | head -1
