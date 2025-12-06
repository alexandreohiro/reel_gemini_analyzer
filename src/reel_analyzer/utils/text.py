import re
from typing import Iterable, List

def normalize_text(s: str) -> str:
    s = s.replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def dedupe_lines(lines: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for ln in lines:
        key = normalize_text(ln).lower()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(normalize_text(ln))
    return out
