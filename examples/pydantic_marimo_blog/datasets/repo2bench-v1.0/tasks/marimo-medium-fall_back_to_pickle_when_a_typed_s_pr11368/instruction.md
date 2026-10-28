# Task: Fall back to pickle when a typed serializer rejects a value in `LazyLoader`

## Problem Description
In `marimo/_save/loaders/lazy.py`, inside `LazyLoader.save_cache`, `_put_or_mark_unserializable` takes a single `serialize: Callable[[Any], bytes]` function and immediately marks a variable as unserializable if its typed serializer (such as Arrow/Parquet for a mixed-dtype Pandas column) raises an exception, instead of falling back to `pickle.dumps`.

## Requirements
1. In `marimo/_save/loaders/lazy.py`, change `_put_or_mark_unserializable`'s third parameter from `serialize: Callable[[Any], bytes]` to `loader: str`.
2. Inside `_put_or_mark_unserializable`, try `serializers = {loader: BLOB_SERIALIZERS.get(loader, pickle.dumps), "pickle": pickle.dumps}` in order. If a fallback `suffix != loader` succeeds, update `key = Path(key).with_suffix(f".{suffix}").as_posix()` and update `item.reference = key` for `item in items` before storing `store.put(key, data)`.
3. Update the callers of `_put_or_mark_unserializable` in `LazyLoader` to pass `return_loader`, `"pickle"`, and `loader` instead of pre-resolved `serialize` callables.
