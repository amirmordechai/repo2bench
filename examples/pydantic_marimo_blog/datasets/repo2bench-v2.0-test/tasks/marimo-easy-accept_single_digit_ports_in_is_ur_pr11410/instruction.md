# Goal: Accept single-digit port numbers in URL validation (`is_url`)

## Context & Goal
Local and custom HTTP/HTTPS URLs that use single-digit ports (such as `http://127.0.0.1:8/macros.tex` or `http://localhost:9/test`) are currently rejected by `is_url` because the port regular expression requires at least 2 digits.

## Acceptance Criteria
- Update URL validation in `is_url` so ports from 1 to 5 digits (`:1` through `:65535`) are accepted on valid URLs, while non-URLs and 6-digit ports remain rejected.
