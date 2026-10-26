from pathlib import Path
from decimal import Decimal

def _read(rel: str) -> str:
    p = Path("/workspace") / rel
    if not p.is_file():
        p = Path(rel)
    return p.read_text(encoding="utf-8")

def test_decision_bounds_accept_float_tolerance():
    src = _read("pydantic_ai_slim/pydantic_ai/models/decision.py")
    assert "float_tolerance: Decimal = Decimal(0)" in src
    assert "max(" in src and "float_tolerance" in src

def test_system_one_passes_float_tolerance():
    src = _read("pydantic_ai_slim/pydantic_ai/models/system_one.py")
    assert "_FLOAT_TOLERANCE" in src
    assert "float_tolerance=_FLOAT_TOLERANCE" in src
