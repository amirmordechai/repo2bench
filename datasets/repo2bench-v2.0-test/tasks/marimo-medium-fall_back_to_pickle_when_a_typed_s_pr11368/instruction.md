# Goal: Fall back to `pickle` serialization in `LazyLoader` when a typed blob serializer fails

## Context & Goal
In `LazyLoader.save_cache`, `_put_or_mark_unserializable` currently takes a single `serialize` callable and immediately marks a cached variable as unserializable if its primary typed serializer (such as Arrow/Parquet on a mixed-dtype Pandas column) raises an exception, instead of falling back to `pickle.dumps`.

## Acceptance Criteria
1. Change `_put_or_mark_unserializable`'s third parameter to `loader: str` and try `serializers = {loader: BLOB_SERIALIZERS.get(loader, pickle.dumps), "pickle": pickle.dumps}` in order.
2. When a fallback `suffix != loader` succeeds, update `key = Path(key).with_suffix(f".{suffix}").as_posix()` and update `item.reference = key` for `item in items` before storing `store.put(key, data)`, and update callers in `LazyLoader` to pass loader name strings (`return_loader`, `"pickle"`, `loader`).
