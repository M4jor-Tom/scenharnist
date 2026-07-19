from scenharnist.bonemap import translate_bone, BONE_MAP, MORPH_MAP, CONTROL_BONES

def test_translate_plain_bone():
    assert translate_bone("頭") == "Head"

def test_translate_side_suffix():
    assert translate_bone("足.L") == "Leg.L"
    assert translate_bone("腕.R") == "Arm.R"

def test_translate_side_prefix():
    assert translate_bone("左ひざ") == "Knee.L"

def test_unknown_bone_passthrough():
    assert translate_bone("_dummy_足首D.L") == "_dummy_足首D.L"

def test_control_bones_are_subset_of_map_values():
    base_values = {v for v in BONE_MAP.values()}
    assert CONTROL_BONES <= base_values

def test_morph_map_has_blink():
    assert "まばたき" in MORPH_MAP and MORPH_MAP["まばたき"] == "Blink"
