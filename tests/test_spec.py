from scenharnist.spec import validate, EXAMPLE_SPEC

SURF = {
    "Augusta": {"bones": ["Arm.R", "Head"], "morphs": ["Anger"], "hint": ""},
    "Baizhi": {"bones": ["Arm.L"], "morphs": [], "hint": ""},
}

def _good():
    return {
        "fps": 24, "duration": 2.0,
        "characters": [
            {"name": "Augusta", "gltf": "a.gltf",
             "root": {"translation": [-0.5, 0, 0], "yaw_deg": 90},
             "bone_tracks": {"Arm.R": [{"t": 0.0, "euler_deg": [0, 0, -70]}]},
             "morph_tracks": {"Anger": [{"t": 0.0, "weight": 1.0}]}},
        ],
        "camera": [{"t": 0.0, "position": [0, 1.2, 3], "look_at": [0, 1, 0]}],
    }

def test_valid_spec_has_no_errors():
    assert validate(_good(), SURF) == []

def test_unknown_bone_flagged():
    s = _good()
    s["characters"][0]["bone_tracks"]["Tail.L"] = [{"t": 0, "euler_deg": [0, 0, 0]}]
    errs = validate(s, SURF)
    assert any("Tail.L" in e for e in errs)

def test_unknown_character_flagged():
    s = _good()
    s["characters"][0]["name"] = "Nobody"
    assert any("Nobody" in e for e in validate(s, SURF))

def test_time_out_of_range_flagged():
    s = _good()
    s["characters"][0]["bone_tracks"]["Arm.R"][0]["t"] = 9.0
    assert any("t=" in e for e in validate(s, SURF))

def test_example_spec_is_self_consistent():
    # EXAMPLE_SPEC must validate against surfaces derived from its own tracks.
    surf = {c["name"]: {
        "bones": list(c["bone_tracks"]), "morphs": list(c["morph_tracks"]), "hint": ""
    } for c in EXAMPLE_SPEC["characters"]}
    assert validate(EXAMPLE_SPEC, surf) == []
