# Goal: Gate the experimental host lifespan and `HostApiMiddleware` behind `MARIMO_ENABLE_HOST`

## Context & Goal
Marimo's experimental host integration (`host` server lifespan and `HostApiMiddleware`) currently runs unconditionally in `EDIT` mode on every Starlette server instance. It should be disabled by default and only enabled when the `MARIMO_ENABLE_HOST` environment setting (`ENABLE_HOST` on `GLOBAL_SETTINGS`) is truthy.

## Acceptance Criteria
- Gate both the `host` lifespan and `HostApiMiddleware` registration in `create_starlette_app` behind `GLOBAL_SETTINGS.ENABLE_HOST` (`MARIMO_ENABLE_HOST`).
