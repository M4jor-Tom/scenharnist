import json
from functools import lru_cache
from .bonemap import translate_bone, strip_side, MORPH_MAP, CONTROL_BONES

_HINT = (
    "Bones are driven with local euler_deg rotations (degrees). Rest pose is "
    "T-ish/A-pose, character faces +Z. Positive rotations follow the bone's "
    "local axes — if a bend goes the wrong way, flip the axis or sign next "
    "iteration. Morphs take a weight 0..1. Only the names below exist."
)

@lru_cache(maxsize=None)
def _load(gltf_path):
    # ponytail: cache the multi-MB parse so digest() + resolution_table() on the
    # same path (as build_characters does per character) parse it once, not twice.
    with open(gltf_path, encoding="utf-8") as f:
        return json.load(f)

_D_CHAIN = {"Leg", "Knee", "Ankle"}  # MMD skin weights ride the D-siblings, not the FK controllers

def _d_sibling(cjk):
    """CJK D-sibling: 足.R -> 足D.R, 左ひざ -> 左ひざD. None if no side marker found."""
    for suf in (".L", ".R"):
        if cjk.endswith(suf):
            return cjk[:-len(suf)] + "D" + suf
    for pre in ("左", "右"):
        if cjk.startswith(pre):
            return cjk + "D"
    return None

def _bone_pairs(d):
    """Yield (english, cjk) for skin joints whose English base is a control bone.

    For Leg/Knee/Ankle, reroute the CJK target to the D-chain sibling (足D/ひざD/足首D)
    when present — the FK controllers (足/ひざ/足首) don't carry skin weights, so
    rotating them wouldn't deform the mesh.
    """
    if not d.get("skins"):
        return
    joints = d["skins"][0]["joints"]
    joint_names = {d["nodes"][ji].get("name", "") for ji in joints}
    for name in joint_names:
        en = translate_bone(name)
        base, _ = strip_side(en)
        if base not in CONTROL_BONES:
            continue
        cjk = name
        if base in _D_CHAIN:
            d_cjk = _d_sibling(name)
            if d_cjk and d_cjk in joint_names:
                cjk = d_cjk
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
