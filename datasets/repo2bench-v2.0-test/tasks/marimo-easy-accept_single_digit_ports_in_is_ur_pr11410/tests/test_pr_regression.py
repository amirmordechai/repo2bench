from pathlib import Path
import importlib.util

def _load_is_url():
    p = Path("/workspace/marimo/_utils/url.py")
    if not p.is_file():
        p = Path("marimo/_utils/url.py")
    spec = importlib.util.spec_from_file_location("url_mod", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.is_url

def test_single_digit_port_accepted():
    is_url = _load_is_url()
    assert is_url("http://127.0.0.1:8/macros.tex") is True
    assert is_url("http://localhost:9/test") is True

def test_multi_digit_and_single_digit_ports_accepted():
    is_url = _load_is_url()
    assert is_url("https://example.com:1/api") is True
    assert is_url("http://127.0.0.1:80/macros.tex") is True
    assert is_url("http://127.0.0.1:8000/macros.tex") is True
    assert is_url("http://127.0.0.1:65535/macros.tex") is True

def test_non_urls_rejected_while_single_digit_port_valid():
    is_url = _load_is_url()
    assert is_url("http://127.0.0.1:5/") is True
    assert is_url("not_a_url") is False
    assert is_url("http://127.0.0.1:123456/too_long") is False
