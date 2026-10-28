# Task: Preserve session TTL across reconnects (`connection_generation`)

## Problem Description
When a client disconnects from a Marimo session (`SessionHandler._on_disconnect`), a TTL timer callback `_close()` is scheduled via `call_later(ttl_seconds, _close)`. If a new consumer B reconnects to the same `session_id` and then disconnects again before consumer A's original TTL timer fires, consumer A's stale `_close()` callback sees `live.connection_state() != ConnectionState.OPEN` and prematurely kills consumer B's session before B's own TTL window expires!

## Requirements
1. In `marimo/_session/types.py`, add `connection_generation: int` to the `Session` protocol.
2. In `marimo/_session/session.py`, initialize `self.connection_generation = 0` in `SessionImpl.__init__`, and increment `self.connection_generation += 1` inside `SessionImpl.connect_consumer` whenever `main` is truthy (`if main:`).
3. In `marimo/_server/api/endpoints/ws/session_handler.py`, inside `_on_disconnect` when `should_ttl_close` is true:
   - Capture `connection_generation = session.connection_generation` when scheduling `_close`.
   - At the start of `_close()`, look up `live = self.manager.get_session(self.params.session_id)` and return immediately if `live is None or live is not session or live.connection_generation != connection_generation`.
