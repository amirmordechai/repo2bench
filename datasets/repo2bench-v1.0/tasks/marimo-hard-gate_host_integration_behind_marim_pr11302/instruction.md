# Task: Gate host integration behind `MARIMO_ENABLE_HOST`

## Problem Description
The experimental host API and lifespan integration in Marimo currently runs unconditionally in `EDIT` mode and attaches `HostApiMiddleware` to every Starlette app. It needs to be gated behind an opt-in `MARIMO_ENABLE_HOST` environment setting (`GLOBAL_SETTINGS.ENABLE_HOST`).

## Requirements
1. In `marimo/_config/settings.py`, add `ENABLE_HOST: bool = is_env_true("MARIMO_ENABLE_HOST")` to `GlobalSettings`.
2. In `marimo/_server/host/lifespan.py`, import `GLOBAL_SETTINGS` from `marimo._config.settings` and early-return (`yield; return`) in `async def host(app: Starlette)` when `not GLOBAL_SETTINGS.ENABLE_HOST or state.mode is not SessionMode.EDIT`.
3. In `marimo/_server/main.py`, inside `create_starlette_app`, only include `Middleware(HostApiMiddleware, base_url=base_url)` in `final_middlewares` when `GLOBAL_SETTINGS.ENABLE_HOST` is truthy.
