"""Scene spec: the single source of truth the model edits (full-replace)."""

EXAMPLE_SPEC = {
    "fps": 24,
    "duration": 3.0,
    "characters": [
        {
            "name": "Augusta",
            "gltf": "gltf/Augusta.gltf/Augusta.gltf",
            "root": {"translation": [-0.6, 0, 0], "yaw_deg": 90},
            "bone_tracks": {
                "Arm.R": [{"t": 0.0, "euler_deg": [0, 0, -70]},
                          {"t": 0.4, "euler_deg": [0, 0, -10]}],
            },
            "morph_tracks": {
                "Anger": [{"t": 0.0, "weight": 0.0}, {"t": 0.4, "weight": 1.0}],
            },
        },
        {
            "name": "Baizhi",
            "gltf": "gltf/Baizhi.gltf/Baizhi.gltf",
            "root": {"translation": [0.6, 0, 0], "yaw_deg": -90},
            "bone_tracks": {
                "Arm.L": [{"t": 0.0, "euler_deg": [0, 0, 70]},
                          {"t": 0.4, "euler_deg": [0, 0, 20]}],
            },
            "morph_tracks": {},
        },
    ],
    "camera": [{"t": 0.0, "position": [0, 1.2, 3.0], "look_at": [0, 1.0, 0]}],
}

def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)

def validate(spec, surfaces):
    """Return a list of error strings; empty means valid.

    surfaces: {char_name: {"bones": [...], "morphs": [...], ...}}.
    """
    errs = []
    fps = spec.get("fps")
    dur = spec.get("duration")
    if not _num(fps) or fps <= 0:
        errs.append("fps must be a positive number")
    if not _num(dur) or dur <= 0:
        errs.append("duration must be a positive number")
    dur = dur if _num(dur) else 0

    chars = spec.get("characters")
    if not isinstance(chars, list) or not chars:
        errs.append("characters must be a non-empty list")
        return errs

    def check_track(cname, kind, name, allowed, frames, val_key, val_ok):
        if name not in allowed:
            errs.append(f"{cname}: unknown {kind} '{name}' (not in control surface)")
        if not isinstance(frames, list) or not frames:
            errs.append(f"{cname}.{name}: track must be a non-empty list")
            return
        for fr in frames:
            t = fr.get("t")
            if not _num(t) or t < 0 or t > dur:
                errs.append(f"{cname}.{name}: t={fr.get('t')} outside [0,{dur}]")
            if not val_ok(fr.get(val_key)):
                errs.append(f"{cname}.{name}: bad {val_key} {fr.get(val_key)}")

    for c in chars:
        cname = c.get("name", "?")
        surf = surfaces.get(cname)
        if surf is None:
            errs.append(f"unknown character '{cname}' (available: {list(surfaces)})")
            continue
        for bone, frames in (c.get("bone_tracks") or {}).items():
            check_track(cname, "bone", bone, surf["bones"], frames, "euler_deg",
                        lambda v: isinstance(v, list) and len(v) == 3 and all(_num(x) for x in v))
        for morph, frames in (c.get("morph_tracks") or {}).items():
            check_track(cname, "morph", morph, surf["morphs"], frames, "weight",
                        lambda v: _num(v) and 0 <= v <= 1)
    return errs
