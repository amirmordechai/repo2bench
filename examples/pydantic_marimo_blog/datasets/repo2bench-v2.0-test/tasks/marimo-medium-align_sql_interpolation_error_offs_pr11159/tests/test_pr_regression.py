from pathlib import Path

def _load_offset_calc():
    p = Path("/workspace/marimo/_sql/parse.py")
    if not p.is_file():
        p = Path("marimo/_sql/parse.py")
    src = p.read_text(encoding="utf-8")
    assert "sanitized_idx" in src and "preceding_offset" in src, "Must compute sanitized_idx = idx + preceding_offset"
    return src

def test_sanitized_idx_used_in_parse_sql_duckdb():
    src = _load_offset_calc()
    assert "sanitized_idx = idx + preceding_offset" in src
    assert "preceding_offset += offset" in src
    assert "error_line_start <= sanitized_idx < position" in src

def test_multiple_interpolations_on_previous_line_offset():
    _load_offset_calc()
    # Verify coordinate math with preceding replacements before newline
    # Query: "SELECT {a}, {b}, {c}, {d}, {e};\nSELECT {value} FRM users"
    idx_to_offset_dict = {7: 2, 12: 2, 17: 2, 22: 2, 27: 2, 39: 2}
    error_line_start = 42  # sanitized newline + 1
    position = 59          # sanitized FRM position
    cumulative_offset = 0
    preceding_offset = 0
    for idx, offset in idx_to_offset_dict.items():
        sanitized_idx = idx + preceding_offset
        preceding_offset += offset
        if error_line_start <= sanitized_idx < position:
            cumulative_offset += offset
    assert cumulative_offset == 2

def test_multiple_interpolations_on_same_line_offset():
    _load_offset_calc()
    idx_to_offset_dict = {7: 2, 12: 2, 17: 2, 22: 2, 27: 2, 43: 2}
    error_line_start = 0
    position = 43
    cumulative_offset = 0
    preceding_offset = 0
    for idx, offset in idx_to_offset_dict.items():
        sanitized_idx = idx + preceding_offset
        preceding_offset += offset
        if error_line_start <= sanitized_idx < position:
            cumulative_offset += offset
    assert cumulative_offset == 10
