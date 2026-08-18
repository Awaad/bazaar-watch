#!/usr/bin/env bash
# Gate: floating point arithmetic near money.
#
# All monetary values are integer minor units with an explicit currency.
# Float accumulates error and produces comparisons that are wrong without
# ever raising. See ADR-0004.
set -euo pipefail

# macOS ships bash 3.2, which has no `mapfile`. Everything below is bash 3.2
# compatible: no mapfile, no readarray, no associative arrays.

list=$(mktemp)
trap 'rm -f "$list"' EXIT

if [ "$#" -gt 0 ]; then
    printf '%s\n' "$@" > "$list"
else
    git ls-files '*.py' '*.ts' '*.tsx' > "$list" 2>/dev/null || true
fi

# Nothing to scan is not a failure.
[ -s "$list" ] || exit 0

pattern='(float|parseFloat)\([^)]*(price|amount|total|cost|minor)|(price|amount|total|cost)[a-zA-Z_]*\s*:\s*float\b'

hits=$(tr '\n' '\0' < "$list" \
    | xargs -0 grep -nEHi "$pattern" 2>/dev/null \
    | grep -v 'gate-ignore: float-money' || true)

if [ -n "$hits" ]; then
    echo "Floating point used on a monetary value. Use integer minor units (ADR-0004):"
    echo "$hits"
    echo
    echo "If this is not money, append:  # gate-ignore: float-money"
    exit 1
fi
exit 0
