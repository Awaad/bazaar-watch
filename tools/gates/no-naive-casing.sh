#!/usr/bin/env bash
# Gate: locale-naive case conversion on text paths.
#
# Turkish casing is locale-dependent: `i` uppercases to `İ` in Turkish and `I`
# elsewhere, and `I` lowercases to `ı`. A lexicon key built with the wrong
# casing silently fails to match and nothing raises. See ADR-0025.
#
# Use core.text.turkish_fold() instead.
set -euo pipefail

files=("$@")
if [ ${#files[@]} -eq 0 ]; then
    mapfile -t files < <(git ls-files '*.py' '*.ts' '*.tsx' 2>/dev/null || true)
fi
[ ${#files[@]} -eq 0 ] && exit 0

pattern='\.(toUpperCase|toLowerCase)\(\)|\.upper\(\)|\.lower\(\)|\.casefold\(\)|\bupper\(|\blower\('

if hits=$(grep -nEH "$pattern" "${files[@]}" 2>/dev/null | grep -v 'noqa: naive-casing'); then
    echo "Locale-naive case conversion found. Use core.text.turkish_fold() (ADR-0025):"
    echo "$hits"
    echo
    echo "If genuinely locale-independent, append:  # noqa: naive-casing"
    exit 1
fi
exit 0
