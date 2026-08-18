#!/usr/bin/env bash
# Gate: naive datetime construction.
#
# Every timestamp in this system is timezone-aware and stored UTC. A naive
# datetime compared against a tz-aware one raises at runtime, and a naive one
# written to TIMESTAMPTZ is silently interpreted in the server timezone.
set -euo pipefail

files=("$@")
if [ ${#files[@]} -eq 0 ]; then
    mapfile -t files < <(git ls-files '*.py' 2>/dev/null || true)
fi
[ ${#files[@]} -eq 0 ] && exit 0

pattern='datetime\.(now|utcnow)\(\s*\)|datetime\.utcnow'

if hits=$(grep -nEH "$pattern" "${files[@]}" 2>/dev/null | grep -v 'gate-ignore: naive-datetime'); then
    echo "Naive datetime construction. Use datetime.now(tz=UTC):"
    echo "$hits"
    exit 1
fi
exit 0
