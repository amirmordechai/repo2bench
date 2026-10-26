# Goal: Add `lockdown` support to the `GitHub` hosted MCP capability

## Context & Goal
GitHub's MCP server supports an `X-MCP-Lockdown: true` request header that asks GitHub to withhold issue, pull request, and comment content in public repositories written by users without push access. The `GitHub` capability class currently supports `read_only`, `toolsets`, `url`, and `client`, but does not expose a `lockdown: bool = False` option.

## Acceptance Criteria
1. Add `lockdown: bool = False` to the `GitHub` capability dataclass.
2. When `lockdown=True` is passed with a custom `client` (`self.client is not None`), raise `UserError` stating that `client` owns the connection and cannot be combined with `auth`, `url`, `toolsets`, or `lockdown`.
3. When building headers for the hosted MCP connection, include `'X-MCP-Lockdown': 'true'` whenever `self.lockdown` is truthy.
