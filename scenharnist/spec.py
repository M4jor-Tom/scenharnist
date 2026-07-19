"""Scene spec: the single source of truth the model edits (full-replace).

EXAMPLE_SPEC is the few-shot the model sees, so it demonstrates the whole
discipline of a good clip, not just syntax:

- The imported rest pose is a T-pose (arms straight out). EVERY limb that
  should not be a T must be posed. Here both arms are held in a boxing guard
  (Arm down+forward via -Z/-Y, Elbow raised via -X) for the entire clip.
- Motion fills the FULL duration — keyframes run 0.0 .. 3.0 with no dead time.
- Between actions the fighters return to guard, never to the rest/T-pose, and
  the clip ENDS in guard.
- Punches move the whole upper body: the striking Arm/Elbow plus an UpperBody
  lean, not one bone in isolation.
- Angles are local euler_deg; world coords (camera, root translation) are
  Y-up with the character facing +Z.
"""

# Reusable calibrated poses (local euler_deg on the standard MMD rig).
_GUARD = {"Arm.R": [0, -18, -72], "Elbow.R": [-115, 0, 0],
          "Arm.L": [0, 18, 72], "Elbow.L": [-115, 0, 0]}
_JAB_R = {"Arm.R": [0, -80, -12], "Elbow.R": [0, 0, -8]}   # right straight, toward opponent
_HOOK_R = {"Arm.R": [0, -52, -46], "Elbow.R": [-70, 0, -35]}

def _k(*pairs):
    return [{"t": t, "euler_deg": e} for t, e in pairs]

EXAMPLE_SPEC = {
    "fps": 24,
    "duration": 3.0,
    "characters": [
        {
            "name": "Augusta",
            "gltf": "gltf/Augusta.gltf/Augusta.gltf",
            "root": {"translation": [-0.52, 0, 0], "yaw_deg": 90},
            "bone_tracks": {
                # jab, jab, hook — always snapping back to guard.
                "Arm.R": _k((0.0, [0, 0, 0]), (0.3, _GUARD["Arm.R"]), (0.6, _JAB_R["Arm.R"]),
                            (0.9, _GUARD["Arm.R"]), (1.5, _JAB_R["Arm.R"]), (1.8, _GUARD["Arm.R"]),
                            (2.3, _HOOK_R["Arm.R"]), (2.7, _GUARD["Arm.R"]), (3.0, _GUARD["Arm.R"])),
                "Elbow.R": _k((0.0, [0, 0, 0]), (0.3, _GUARD["Elbow.R"]), (0.6, _JAB_R["Elbow.R"]),
                              (0.9, _GUARD["Elbow.R"]), (1.5, _JAB_R["Elbow.R"]), (1.8, _GUARD["Elbow.R"]),
                              (2.3, _HOOK_R["Elbow.R"]), (2.7, _GUARD["Elbow.R"]), (3.0, _GUARD["Elbow.R"])),
                "Arm.L": _k((0.0, [0, 0, 0]), (0.3, _GUARD["Arm.L"]), (3.0, _GUARD["Arm.L"])),
                "Elbow.L": _k((0.0, [0, 0, 0]), (0.3, _GUARD["Elbow.L"]), (3.0, _GUARD["Elbow.L"])),
                "UpperBody": _k((0.0, [0, 0, 0]), (0.3, [6, 0, 0]), (0.6, [10, -6, 0]), (0.9, [6, 0, 0]),
                                (1.5, [10, -6, 0]), (1.8, [6, 0, 0]), (2.3, [9, -10, 0]), (2.7, [6, 0, 0]),
                                (3.0, [6, 0, 0])),
            },
            "morph_tracks": {"Anger": [{"t": 0.0, "weight": 0.2}, {"t": 3.0, "weight": 0.5}]},
        },
        {
            "name": "Baizhi",
            "gltf": "gltf/Baizhi.gltf/Baizhi.gltf",
            "root": {"translation": [0.52, 0, 0], "yaw_deg": -90},
            "bone_tracks": {
                "Arm.R": _k((0.0, [0, 0, 0]), (0.3, _GUARD["Arm.R"]), (1.2, _JAB_R["Arm.R"]),
                            (1.5, _GUARD["Arm.R"]), (3.0, _GUARD["Arm.R"])),
                "Elbow.R": _k((0.0, [0, 0, 0]), (0.3, _GUARD["Elbow.R"]), (1.2, _JAB_R["Elbow.R"]),
                              (1.5, _GUARD["Elbow.R"]), (3.0, _GUARD["Elbow.R"])),
                "Arm.L": _k((0.0, [0, 0, 0]), (0.3, _GUARD["Arm.L"]), (3.0, _GUARD["Arm.L"])),
                "Elbow.L": _k((0.0, [0, 0, 0]), (0.3, _GUARD["Elbow.L"]), (3.0, _GUARD["Elbow.L"])),
                "UpperBody": _k((0.0, [0, 0, 0]), (0.3, [6, 0, 0]), (0.6, [-6, 0, 0]), (0.9, [6, 0, 0]),
                                (1.2, [10, 6, 0]), (1.5, [6, 0, 0]), (3.0, [6, 0, 0])),
            },
            "morph_tracks": {},
        },
    ],
    "camera": [{"t": 0.0, "position": [0, 1.2, 3.7], "look_at": [0, 1.02, 0]}],
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
