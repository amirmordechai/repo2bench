# Goal: Redact `quote_plus`-encoded BrowserUse secrets and prevent encoded secret placeholders from overwriting raw secrets

## Context & Goal
When the BrowserUse integration redacts `sensitive_data` secrets in `browse_web` outputs (`_secret_placeholders`), two leaks can occur:
1. Blocked search navigation URLs format query parameters using `urllib.parse.quote_plus(value, errors='surrogatepass')` (turning spaces into `+` and special characters into `%XX`), which currently bypasses secret redaction.
2. If secret `b`'s raw value equals secret `a`'s JSON-escaped or URL-encoded form, populating raw and encoded forms in a single pass allows `a`'s encoded placeholder to overwrite `b`'s raw value mapping.

## Acceptance Criteria
- Ensure `_secret_placeholders` registers all `<secret>{key}</secret>` self-mappings and raw secret values in a first pass, and then registers both JSON-escaped (`json.dumps(value, ensure_ascii=False)[1:-1]`) and `quote_plus(value, errors='surrogatepass')` forms in a second pass using `setdefault` so raw secret mappings always take precedence.
