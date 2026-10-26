# Goal: Prevent stale disconnect TTL timers from closing a session after a new main consumer reconnects

## Context & Goal
When a client disconnects from a Marimo session (`_on_disconnect`), a delayed `_close()` callback is scheduled via `call_later(ttl_seconds, _close)`. If a new main consumer reconnects to the same session and then disconnects again before the first consumer's TTL timer expires, the first consumer's stale `_close()` callback sees the session closed/disconnected and prematurely terminates the second consumer's session before its own TTL expires.

## Acceptance Criteria
- Track a monotonic connection generation counter on the session whenever a main consumer connects, and ensure delayed disconnect `_close()` callbacks become no-ops if a newer main consumer connection occurred since the timer was scheduled.
