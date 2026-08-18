#!/usr/bin/env bash
# Gate: locale-naive case conversion on text paths.
#
# Turkish casing is locale-dependent: `i` uppercases to `İ` in Turkish and `I`
# elsewhere, and `I` lowercases to `ı`. A lexicon key built with the wrong
# casing silently fails to match and nothing raises. See ADR-0025.
#
# Use core.text.turkish_fold() instead.
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

# Method form only. In Python and TypeScript the hazard is always a method
# call on a string. A bare `lower(` in these files is prose or a string
# literal, and matching it produced false positives on the very tests that
# document the problem. Bare SQL lower() lives in .sql files, which this
# gate does not scan; the one place it appears is turkish_fold.sql, where
# it is correct and deliberate.
pattern='\.(toUpperCase|toLowerCase|toLocaleUpperCase|toLocaleLowerCase)\(|\.upper\(\)|\.lower\(\)|\.casefold\(\)'

hits=$(tr '\n' '\0' < "$list" \
    | xargs -0 grep -nEH "$pattern" 2>/dev/null \
    | grep -v 'gate-ignore: naive-casing' || true)

if [ -n "$hits" ]; then
    echo "Locale-naive case conversion found. Use core.text.turkish_fold() (ADR-0025):"
    echo "$hits"
    echo
    echo "If genuinely locale-independent, append:  # gate-ignore: naive-casing"
    exit 1
fi
exit 0
