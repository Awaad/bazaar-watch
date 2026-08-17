#!/usr/bin/env bash
# Gate: floating point arithmetic near money.
#
# All monetary values are integer minor units with an explicit currency.
# Float accumulates error and produces comparisons that are wrong without
# ever raising. See ADR-0004.
set -euo pipefail

files=("$@")
if [ ${#files[@]} -eq 0 ]; then
    mapfile -t files < <(git ls-files '*.py' '*.ts' '*.tsx' 2>/dev/null || true)
fi
[ ${#files[@]} -eq 0 ] && exit 0

# float()/parseFloat() applied to something money-shaped, or a float-typed
# declaration whose name contains price/amount/total/cost.
pattern='(float|parseFloat)\([^)]*(price|amount|total|cost|minor)|(price|amount|total|cost)[a-zA-Z_]*\s*:\s*float\b'

if hits=$(grep -nEHi "$pattern" "${files[@]}" 2>/dev/null | grep -v 'noqa: float-money'); then
    echo "Floating point used on a monetary value. Use integer minor units (ADR-0004):"
    echo "$hits"
    echo
    echo "If this is not money, append:  # noqa: float-money"
    exit 1
fi
exit 0
