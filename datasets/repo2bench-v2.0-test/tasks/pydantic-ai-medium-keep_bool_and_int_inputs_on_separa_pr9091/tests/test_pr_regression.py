from pathlib import Path
from enum import IntEnum, StrEnum
from typing import Any, Literal, get_args, get_origin

def _load_branch_matcher():
    p = Path("/workspace/pydantic_graph/pydantic_graph/graph_builder.py")
    if not p.is_file():
        p = Path("pydantic_graph/pydantic_graph/graph_builder.py")
    src = p.read_text(encoding="utf-8")
    # Extract the exactelif get_origin(branch_source) is Literal block
    lines = src.splitlines()
    block = []
    in_block = False
    indent = 0
    for ln in lines:
        if "elif get_origin(branch_source) is Literal:" in ln:
            in_block = True
            indent = len(ln) - len(ln.lstrip())
            block.append("if get_origin(branch_source) is Literal:")
            continue
        if in_block:
            cur_indent = len(ln) - len(ln.lstrip()) if ln.strip() else indent + 4
            if ln.strip() and cur_indent <= indent:
                break
            block.append(ln[indent:])
    code = "\n".join(block)
    def match(inputs, branch_source):
        ns = {"inputs": inputs, "branch_source": branch_source, "Literal": Literal, "get_origin": get_origin, "get_args": get_args}
        exec(code, ns)
        return ns["inputs_match"]
    return match

def test_bool_does_not_match_int_literal():
    match = _load_branch_matcher()
    assert match(True, Literal[1]) is False
    assert match(False, Literal[0]) is False
    assert match(True, Literal[True]) is True

def test_int_does_not_match_bool_literal():
    match = _load_branch_matcher()
    assert match(1, Literal[True]) is False
    assert match(0, Literal[False]) is False
    assert match(1, Literal[1]) is True

def test_enums_still_match_literals():
    class Level(IntEnum):
        HIGH = 1
    match = _load_branch_matcher()
    assert match(Level.HIGH, Literal[True]) is False
    assert match(Level.HIGH, Literal[1]) is True
