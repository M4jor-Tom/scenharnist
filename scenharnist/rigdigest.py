import json
from .bonemap import translate_bone, MORPH_MAP, CONTROL_BONES

_HINT = (
    "Bones are driven with local euler_deg rotations (degrees). Rest pose is "
    "T-ish/A-pose, character faces +Z. Positive rotations follow the bone's "
    "local axes — if a bend goes the wrong way, flip the axis or sign next "
    "iteration. Morphs take a weight 0..1. Only the names below exist."
)

def _load(gltf_path):
    with open(gltf_path, encoding="utf-8") as f:
        return json.load(f)

def _bone_pairs(d):
    """Yield (english, cjk) for skin joints whose English base is a control bone."""
    if not d.get("skins"):
        return
    joints = d["skins"][0]["joints"]
    for ji in joints:
        cjk = d["nodes"][ji].get("name", "")
        en = translate_bone(cjk)
        base = en[:-2] if en.endswith((".L", ".R")) else en
        if base in CONTROL_BONES:
            yield en, cjk

def _morph_pairs(d):
    """Yield (english, cjk) for named morph targets present in MORPH_MAP."""
    for m in d.get("meshes", []):
        names = (m.get("extras") or {}).get("targetNames") or []
        for cjk in names:
            if cjk in MORPH_MAP:
                yield MORPH_MAP[cjk], cjk

def digest(gltf_path):
    d = _load(gltf_path)
    bones = sorted({en for en, _ in _bone_pairs(d)})
    morphs = sorted({en for en, _ in _morph_pairs(d)})
    return {"bones": bones, "morphs": morphs, "hint": _HINT}

def resolution_table(gltf_path):
    d = _load(gltf_path)
    return {
        "bones": {en: cjk for en, cjk in _bone_pairs(d)},
        "morphs": {en: cjk for en, cjk in _morph_pairs(d)},
    }
