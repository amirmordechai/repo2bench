from pathlib import Path
import ast, re

def _load_markdown_converter():
    p = Path("/workspace/marimo/_utils/docs.py")
    if not p.is_file():
        p = Path("marimo/_utils/docs.py")
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    ns = {"re": re}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "MarkdownConverter":
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(p), "exec"), ns)
            return ns["MarkdownConverter"], src
    raise AssertionError("MarkdownConverter class not found in marimo/_utils/docs.py")

def test_markdown_converter_matches_backtick_spans():
    cls, _ = _load_markdown_converter()
    conv = cls()
    assert conv.priority == 0
    assert conv.can_convert("Note: `shout_factor` supports all natural numbers.") is True
    assert conv.can_convert("Use ``a`b_c`` to include a backtick.") is True
    assert conv.convert("Use `a_b`.") == "Use `a_b`."

def test_markdown_converter_rejects_escaped_or_unclosed_backticks():
    cls, _ = _load_markdown_converter()
    conv = cls()
    assert conv.can_convert("Plain text without code spans.") is False
    assert conv.can_convert("Unclosed `shout_factor.") is False
    assert conv.can_convert("Escaped " + chr(92) + "`shout_factor" + chr(92) + "`.") is False

def test_markdown_converter_priority_and_multiline_code_span():
    cls, _ = _load_markdown_converter()
    conv = cls()
    assert conv.priority == 0
    assert conv.can_convert("Multiline:\n`first_part\nsecond_part`") is True
