-- Turkish fold, mirrored from bazaarwatch.core.text.turkish_fold.
--
-- These two implementations MUST agree byte for byte. The lexicon is exact
-- match on folded text, so a divergence between the value written by the
-- application and the value an index expression computes means resolution
-- silently fails to match and nothing raises. Their parity is asserted by test.
--
-- IMMUTABLE is required for use in an index expression. It is also true: the
-- function depends on nothing outside its argument, and deliberately does not
-- call lower() before translating, because Postgres lower() maps I to i
-- regardless of locale, which is wrong for Turkish.
--
-- See ADR-0025 and docs/11-i18n-localization.md section 3.

CREATE OR REPLACE FUNCTION turkish_fold(input text)
RETURNS text
LANGUAGE sql
IMMUTABLE
STRICT
PARALLEL SAFE
AS $$
    SELECT
        -- 4. collapse internal whitespace runs and trim the ends
        btrim(
            regexp_replace(
                -- 3. remaining characters use Unicode default casing, which is
                --    now correct because the Turkish-specific pairs are gone
                lower(
                    -- 2. dotted and dotless i, and the other Turkish letters,
                    --    mapped explicitly to their ASCII counterparts
                    translate(
                        -- 1. normalise Unicode so composed and decomposed forms
                        --    of the same letter fold identically
                        normalize(input, NFC),
                        'İIıŞşĞğÇçÖöÜü',
                        'IIiSsGgCcOoUu'
                    )
                ),
                '\s+', ' ', 'g'
            )
        );
$$;

COMMENT ON FUNCTION turkish_fold(text) IS
    'Lossy fold for lexicon keys and trigram matching only. Never applied to '
    'embedding input: stripping diacritics degrades a model trained on natural '
    'text. Mirrored from bazaarwatch.core.text.turkish_fold; parity asserted by test.';
