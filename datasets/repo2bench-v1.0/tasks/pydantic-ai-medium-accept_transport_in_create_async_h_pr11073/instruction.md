# Task: Accept `transport=` in `create_async_httpx2_client()` and use `DEFAULT_HTTP_LIMITS` in `httpx2` retry transports

## Problem Description
In `pydantic_ai_slim/pydantic_ai/_http.py` and `pydantic_ai_slim/pydantic_ai/retries.py`:
1. `create_async_httpx2_client()` does not accept a custom `transport: httpx2.AsyncBaseTransport | None = None` parameter and does not export `DEFAULT_HTTP_LIMITS` in `__all__`.
2. `HTTPX2TenacityTransport` and `AsyncHTTPX2TenacityTransport` in `pydantic_ai/retries.py` construct `httpx2.HTTPTransport()` and `httpx2.AsyncHTTPTransport()` without passing `limits=DEFAULT_HTTP_LIMITS` when `wrapped` is not provided.

## Requirements
1. In `pydantic_ai_slim/pydantic_ai/_http.py`:
   - Define `DEFAULT_HTTP_LIMITS = httpx2.Limits(max_connections=DEFAULT_MAX_CONNECTIONS, max_keepalive_connections=DEFAULT_MAX_KEEPALIVE_CONNECTIONS)` and export `'DEFAULT_HTTP_LIMITS'` in `__all__`.
   - Add `transport: httpx2.AsyncBaseTransport | None = None` (with default `limits: httpx2.Limits = DEFAULT_HTTP_LIMITS`) to `create_async_httpx2_client()` and forward `transport=transport` to `httpx2.AsyncClient(...)`.
2. In `pydantic_ai_slim/pydantic_ai/retries.py`:
   - Import `DEFAULT_HTTP_LIMITS` from `._http` and use `httpx2.HTTPTransport(limits=DEFAULT_HTTP_LIMITS)` / `httpx2.AsyncHTTPTransport(limits=DEFAULT_HTTP_LIMITS)` as the default when `wrapped` is None in `HTTPX2TenacityTransport.__init__` and `AsyncHTTPX2TenacityTransport.__init__`.
