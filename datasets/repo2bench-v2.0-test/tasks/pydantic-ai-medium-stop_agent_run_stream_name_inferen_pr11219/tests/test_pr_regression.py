from pathlib import Path
import ast

def _get_run_stream_ast():
    p = Path("/workspace/pydantic_ai_slim/pydantic_ai/agent/abstract.py")
    if not p.is_file():
        p = Path("pydantic_ai_slim/pydantic_ai/agent/abstract.py")
    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run_stream":
            return node, ast.get_source_segment(src, node)
    raise AssertionError("run_stream not found")

def test_run_stream_deletes_frame_local():
    node, seg = _get_run_stream_ast()
    deleted_names = [
        t.id for n in ast.walk(node) if isinstance(n, ast.Delete)
        for t in n.targets if isinstance(t, ast.Name)
    ]
    assert "frame" in deleted_names, "run_stream must `del frame` to break the frame reference cycle"

def test_run_stream_infer_name_block_intact():
    node, seg = _get_run_stream_ast()
    assert "self._infer_name(frame.f_back)" in seg
    assert "del frame" in seg

def test_frame_deleted_before_yield():
    node, seg = _get_run_stream_ast()
    idx_infer = seg.index("self._infer_name(frame.f_back)")
    idx_del = seg.index("del frame")
    idx_yield = seg.index("yield ")
    assert idx_infer < idx_del < idx_yield
