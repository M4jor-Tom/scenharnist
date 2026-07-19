import pytest
from scenharnist.paths import resolve_gltf_root

def _mkroot(tmp_path):
    (tmp_path / "gltf").mkdir(parents=True)
    return str(tmp_path)

def test_explicit_wins_over_env(tmp_path, monkeypatch):
    root = _mkroot(tmp_path)
    monkeypatch.setenv("SCENHARNIST_GLTF_ROOT", "/nonexistent/db")
    assert resolve_gltf_root(root) == root

def test_env_used_when_no_explicit(tmp_path, monkeypatch):
    root = _mkroot(tmp_path)
    monkeypatch.setenv("SCENHARNIST_GLTF_ROOT", root)
    assert resolve_gltf_root() == root

def test_skips_paths_without_gltf_subdir(tmp_path, monkeypatch):
    good = _mkroot(tmp_path / "good"); (tmp_path / "bare").mkdir()
    monkeypatch.setenv("SCENHARNIST_GLTF_ROOT", good)
    # explicit points at a dir with no gltf/ -> falls through to env
    assert resolve_gltf_root(str(tmp_path / "bare")) == good

def test_missing_everywhere_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENHARNIST_GLTF_ROOT", str(tmp_path / "nope"))
    monkeypatch.setattr("scenharnist.paths._DEFAULT", str(tmp_path / "alsonope"))
    with pytest.raises(FileNotFoundError):
        resolve_gltf_root()
