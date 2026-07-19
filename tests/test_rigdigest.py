import os, pytest
from scenharnist.rigdigest import digest, resolution_table

AUG = os.path.expanduser("~/.vault/repos/waifus.gltf/gltf/Augusta.gltf/Augusta.gltf")

@pytest.mark.skipif(not os.path.exists(AUG), reason="waifus.gltf not present")
def test_digest_surfaces_humanoid_bones():
    d = digest(AUG)
    for b in ["Head", "Neck", "Arm.L", "Arm.R", "Leg.L", "Knee.R"]:
        assert b in d["bones"], b
    # no physics/dummy noise leaks in
    assert not any("dummy" in b.lower() or "_" in b for b in d["bones"])

@pytest.mark.skipif(not os.path.exists(AUG), reason="waifus.gltf not present")
def test_resolution_table_roundtrips_to_cjk():
    rt = resolution_table(AUG)
    assert rt["bones"]["Head"] == "頭"
    assert rt["bones"]["Leg.L"] == "足.L"

@pytest.mark.skipif(not os.path.exists(AUG), reason="waifus.gltf not present")
def test_digest_morphs_are_english():
    d = digest(AUG)
    assert "Blink" in d["morphs"] or "Serious" in d["morphs"]
