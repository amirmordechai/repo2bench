from pathlib import Path

def _get_lazy_src() -> str:
    p = Path("/workspace/marimo/_save/loaders/lazy.py")
    if not p.is_file():
        p = Path("marimo/_save/loaders/lazy.py")
    return p.read_text(encoding="utf-8")

def test_put_or_mark_unserializable_accepts_loader_name():
    src = _get_lazy_src()
    fn_part = src.split("def _put_or_mark_unserializable(", 1)[1].split("def ", 1)[0]
    assert "loader: str" in fn_part
    assert '"pickle": pickle.dumps' in fn_part

def test_fallback_updates_key_suffix_and_item_references():
    src = _get_lazy_src()
    fn_part = src.split("def _put_or_mark_unserializable(", 1)[1].split("def ", 1)[0]
    assert '.with_suffix(f".{suffix}").as_posix()' in fn_part
    assert "item.reference = key" in fn_part

def test_callers_pass_loader_strings():
    src = _get_lazy_src()
    after = src.split("def _put_or_mark_unserializable(", 1)[1]
    assert "return_loader," in after
    assert '"pickle",' in after
