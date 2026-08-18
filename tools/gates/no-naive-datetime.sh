#!/usr/bin/env bash
# Gate: naive datetime construction.
#
# Every timestamp in this system is timezone-aware and stored UTC. A naive
# datetime compared against a tz-aware one raises at runtime, and a naive one
# written to TIMESTAMPTZ is silently interpreted in the server timezone.
set -euo pipefail

# macOS ships bash 3.2, which has no `mapfile`. Everything below is bash 3.2
# compatible: no mapfile, no readarray, no associative arrays.

list=$(mktemp)
trap 'rm -f "$list"' EXIT

if [ "$#" -gt 0 ]; then
    printf '%s\n' "$@" > "$list"
else
    git ls-files '*.py' > "$list" 2>/dev/null || true
fi

# Nothing to scan is not a failure.
[ -s "$list" ] || exit 0

pattern='datetime\.(now|utcnow)\(\s*\)|datetime\.utcnow'

hits=$(tr '\n' '\0' < "$list" \
    | xargs -0 grep -nEH "$pattern" 2>/dev/null \
    | grep -v 'gate-ignore: naive-datetime' || true)

if [ -n "$hits" ]; then
    echo "Naive datetime construction. Use datetime.now(tz=UTC):"
    echo "$hits"
    exit 1
fi
exit 0
