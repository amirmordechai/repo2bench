# Task: Accept single-digit ports in `is_url`

## Problem Description
In `marimo/_utils/url.py`, the URL validation regular expression matches port numbers using `(?::\d{2,5})?`, which requires at least 2 digits and rejects valid URLs with single-digit ports such as `http://127.0.0.1:8/macros.tex`.

## Requirements
1. Update the port number group in `regex` in `marimo/_utils/url.py` from `(?::\d{2,5})?` to `(?::\d{1,5})?` so ports from 1 to 5 digits are accepted.
