from __future__ import annotations

import re

from conftest import ROOT


def test_published_docs_do_not_expose_development_goals() -> None:
    text = "\n".join(path.read_text() for path in (ROOT / "docs").rglob("*.md"))
    assert not re.search(r"\bgoal[ -]?\d+\b", text, re.I)
    assert "ChatGPT" not in text
    assert "approval candidate" not in text.lower()


def test_docs_pass_humanizer_punctuation_gate() -> None:
    paths = list((ROOT / "docs").rglob("*.md"))
    text = "\n".join(path.read_text() for path in paths)
    assert "—" not in text
    assert "–" not in text
    assert " -- " not in text
