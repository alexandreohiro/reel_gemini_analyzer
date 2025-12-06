from reel_analyzer.utils.text import normalize_text, dedupe_lines

def test_normalize_text():
    assert normalize_text(" a  b\n\n\n c ") == "a b\n\nc"

def test_dedupe_lines():
    lines = ["Oi", "oi ", "  ", "Olá"]
    assert dedupe_lines(lines) == ["Oi", "Olá"]
