# Goal: Skip hosted lockfile PEP 723 dependency pinning during offline WASM exports

## Context & Goal
When exporting a notebook to WASM (`export_wasm` and `_export_wasm_with_execution`), `pin_pep723_dependencies_for_wasm` currently pins inline PEP 723 script dependencies before calling `_prepare_wasm_export`. However, when `request.offline_export_dir` is provided (an offline / air-gapped WASM export), pinning against the hosted lockfile or host machine versions rewrites dependencies like `numpy` to versions Pyodide cannot install from the offline wheel mirror.

## Acceptance Criteria
1. Move the `pin_pep723_dependencies_for_wasm(code, request.path)` call into `_prepare_wasm_export(code, request)` and run it **only** when `request.offline_export_dir is None`.
2. Remove the unconditional `pin_pep723_dependencies_for_wasm` calls from `export_wasm` and `_export_wasm_with_execution`.
