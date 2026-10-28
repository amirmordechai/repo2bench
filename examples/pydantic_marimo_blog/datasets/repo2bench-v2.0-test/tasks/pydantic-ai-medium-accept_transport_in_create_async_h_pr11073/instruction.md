# Goal: Expose `DEFAULT_HTTP_LIMITS`, accept `transport=` in `create_async_httpx2_client()`, and apply default connection limits to retry transports

## Context & Goal
HTTP client creation and tenacity retry transports in `pydantic_ai` have two gaps:
1. `create_async_httpx2_client()` does not accept a custom `transport` keyword argument and does not define or export a shared `DEFAULT_HTTP_LIMITS` constant (`httpx2.Limits(max_connections=DEFAULT_MAX_CONNECTIONS, max_keepalive_connections=DEFAULT_MAX_KEEPALIVE_CONNECTIONS)`) in `__all__`.
2. When `HTTPX2TenacityTransport` and `AsyncHTTPX2TenacityTransport` create their default `httpx2.HTTPTransport` / `httpx2.AsyncHTTPTransport` (when `wrapped` is `None`), they do not pass `limits=DEFAULT_HTTP_LIMITS`.

## Acceptance Criteria
1. Define and export `DEFAULT_HTTP_LIMITS` in `__all__`, and add `transport: httpx2.AsyncBaseTransport | None = None` to `create_async_httpx2_client()`, forwarding `transport=transport` to `httpx2.AsyncClient(...)`.
2. Update `HTTPX2TenacityTransport` and `AsyncHTTPX2TenacityTransport` to pass `limits=DEFAULT_HTTP_LIMITS` when constructing default `httpx2.HTTPTransport` and `httpx2.AsyncHTTPTransport` instances.
