import os, pytest
from scenharnist.cli import detect_characters

def _mkroot(tmp_path, names):
    g = tmp_path / "gltf"; g.mkdir()
    for n in names:
        d = g / f"{n}.gltf"; d.mkdir()
        (d / f"{n}.gltf").write_text("{}")
    return str(tmp_path)

def test_detect_two_characters(tmp_path):
    root = _mkroot(tmp_path, ["Augusta", "Baizhi", "Changli"])
    found = detect_characters("Augusta and Baizhi are boxing", root)
    assert set(found) == {"Augusta", "Baizhi"}

def test_detect_is_case_insensitive(tmp_path):
    root = _mkroot(tmp_path, ["Augusta"])
    assert detect_characters("augusta throws a punch", root) == ["Augusta"]

def test_detect_none_returns_empty(tmp_path):
    root = _mkroot(tmp_path, ["Augusta"])
    assert detect_characters("two robots fight", root) == []
