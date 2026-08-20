"""Interface locales.

One list, because `docs/11-i18n-localization.md` section 1 governs the app, the
category tree and anything else that carries translated text, and a second copy
would drift from it silently.

`users.locale` is still an unconstrained `VARCHAR(8)`. Constraining it is a
schema change and belongs in whatever slice touches identity next; this module
is where the vocabulary lives when it does.
"""

from __future__ import annotations

from bazaarwatch.core.enums import SqlStrEnum


class Locale(SqlStrEnum):
    TURKISH = "tr"
    ENGLISH = "en"
    RUSSIAN = "ru"
    GERMAN = "de"
    # Layout-ready, untranslated. Present so that right-to-left work is not a
    # schema change later, and excluded from completeness below.
    ARABIC = "ar"


# The locales a translation must cover to count as complete. Launch locales
# only: `ar` is layout-ready and deliberately not translated, so requiring it
# would block every taxonomy version forever.
LAUNCH_LOCALES = (Locale.TURKISH, Locale.ENGLISH, Locale.RUSSIAN, Locale.GERMAN)

# The one locale required at write time. Content language is Turkish, so a node
# with no Turkish name is not a node anyone can use (ADR-0032).
REQUIRED_AT_WRITE = Locale.TURKISH


__all__ = ["LAUNCH_LOCALES", "REQUIRED_AT_WRITE", "Locale"]
