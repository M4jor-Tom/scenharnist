# scenharnist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Python CLI that turns a prompt (e.g. "Augusta and Baizhi are boxing") into an animated glTF + preview video by letting any LiteLLM model iteratively author a compact scene spec while watching rendered previews, steering only rig rotations, root translation, and morphs.

**Architecture:** Four decoupled units — `rigdigest` (glTF → small English control surface, no Blender), `spec` (JSON scene schema + validation), `bake_render` (Blender-headless spec → frames/video/glb), `loop` (LiteLLM agent loop) — wired by a `cli`. Blender owns all glTF/quaternion/binary math; our Python never touches the `.bin`.

**Tech Stack:** Python 3.11+, LiteLLM (provider-agnostic vision+tools), Blender headless (Eevee), nix flake for packaging.

## Global Constraints

- Source models use the `waifus.gltf` layout: `<gltf-root>/gltf/<Char>.gltf/<Char>.gltf` (+ `.bin` + textures). Default `--gltf-root` = `../waifus.gltf`.
- The model sees **only** bones + morphs from the control surface — never mesh/vertex data.
- Provider + model chosen entirely by the `--model` string (LiteLLM format, e.g. `anthropic/claude-opus-4-8`). Requires a vision + tool-call capable model.
- Scene spec uses **full-replace** (model re-emits whole spec each step); no patch protocol.
- Rotations authored as local `euler_deg` (degrees); Blender converts to bone-local quaternions.
- v1 scope: 1–2 characters, keyframed camera, max 5 iterations. Physics bones (hair/skirt) not exposed.
- Python package name: `scenharnist`. Tests via `pytest`.

---

### Task 1: Project scaffolding + bone/morph maps

**Files:**
- Create: `pyproject.toml`
- Create: `scenharnist/__init__.py`
- Create: `scenharnist/bonemap.py`
- Test: `tests/test_bonemap.py`

**Interfaces:**
- Produces: `BONE_MAP: dict[str,str]`, `MORPH_MAP: dict[str,str]`, `translate_bone(cjk: str) -> str`, `CONTROL_BONES: set[str]` (whitelist of English base names exposed to the model).

- [x] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "scenharnist"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["litellm>=1.40"]

[project.scripts]
scenharnist = "scenharnist.cli:main"

[project.optional-dependencies]
dev = ["pytest>=8"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [x] **Step 2: Write the failing test**

`tests/test_bonemap.py`:

```python
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
```

- [x] **Step 3: Run test to verify it fails**

Run: `cd /home/theta/.vault/repos/scenharnist && python -m pytest tests/test_bonemap.py -q`
Expected: FAIL (module `scenharnist.bonemap` not found).

- [x] **Step 4: Write `scenharnist/__init__.py`** (empty file)

```python
```

- [x] **Step 5: Write `scenharnist/bonemap.py`**

Copy the `BONE_MAP = { ... }` dict **verbatim** from `/home/theta/.vault/repos/waifus.gltf/scripts/pmx_bone_rename.py` (the dict literal, ~70 lines starting at `BONE_MAP = {`). Then append the code below:

```python
# BONE_MAP copied verbatim from waifus.gltf/scripts/pmx_bone_rename.py above.

# Curated CJK->English morph map: common MMD expression morphs only.
MORPH_MAP = {
    "まばたき": "Blink", "ウィンク": "WinkL", "ウィンク右": "WinkR",
    "笑い": "Smile", "にこり": "Smile2", "なごみ": "SoftEyes",
    "真面目": "Serious", "怒り": "Anger", "困る": "Troubled",
    "びっくり": "Surprise", "じと目": "Glare",
    "あ": "MouthA", "い": "MouthI", "う": "MouthU",
    "え": "MouthE", "お": "MouthO",
    "にやり": "Grin", "口角上げ": "MouthUp", "口角下げ": "MouthDown",
    "頬染め": "Blush",
}

# English base names the model may drive (limbs get .L/.R at digest time).
CONTROL_BONES = {
    "Center", "Waist", "LowerBody", "UpperBody", "UpperBody2",
    "Neck", "Head", "Chest",
    "Shoulder", "Arm", "Elbow", "Wrist",
    "Leg", "Knee", "Ankle", "Toe",
}

_SUFFIX = {".L": ".L", ".R": ".R"}
_PREFIX = {"左": ".L", "右": ".R"}

def translate_bone(cjk: str) -> str:
    """CJK MMD bone name -> English, preserving .L/.R side. Unknown -> unchanged."""
    side = ""
    base = cjk
    for suf, s in _SUFFIX.items():
        if base.endswith(suf):
            side, base = s, base[: -len(suf)]
            break
    else:
        for pre, s in _PREFIX.items():
            if base.startswith(pre):
                side, base = s, base[len(pre):]
                break
    if base in BONE_MAP:
        return BONE_MAP[base] + side
    return cjk
```

- [x] **Step 6: Run test to verify it passes**

Run: `cd /home/theta/.vault/repos/scenharnist && python -m pytest tests/test_bonemap.py -q`
Expected: PASS (6 passed).

- [x] **Step 7: Commit**

```bash
cd /home/theta/.vault/repos/scenharnist
git add pyproject.toml scenharnist/__init__.py scenharnist/bonemap.py tests/test_bonemap.py
git commit -m "feat: bone/morph maps + scaffolding"
```

---

### Task 2: rigdigest — control surface + resolution table

**Files:**
- Create: `scenharnist/rigdigest.py`
- Test: `tests/test_rigdigest.py`

**Interfaces:**
- Consumes: `translate_bone`, `MORPH_MAP`, `CONTROL_BONES` from `scenharnist.bonemap`.
- Produces:
  - `digest(gltf_path: str) -> dict` returning `{"bones": [str], "morphs": [str], "hint": str}` — English names the model may use.
  - `resolution_table(gltf_path: str) -> dict` returning `{"bones": {en: cjk}, "morphs": {en: cjk}}`.

- [x] **Step 1: Write the failing test**

`tests/test_rigdigest.py`:

```python
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
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /home/theta/.vault/repos/scenharnist && python -m pytest tests/test_rigdigest.py -q`
Expected: FAIL (module `scenharnist.rigdigest` not found).

- [x] **Step 3: Write `scenharnist/rigdigest.py`**

```python
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
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd /home/theta/.vault/repos/scenharnist && python -m pytest tests/test_rigdigest.py -q`
Expected: PASS (3 passed; or skipped if waifus.gltf absent — run where it exists).

- [x] **Step 5: Commit**

```bash
cd /home/theta/.vault/repos/scenharnist
git add scenharnist/rigdigest.py tests/test_rigdigest.py
git commit -m "feat: rigdigest control surface + resolution table"
```

---

### Task 3: Scene spec schema + validation

**Files:**
- Create: `scenharnist/spec.py`
- Test: `tests/test_spec.py`

**Interfaces:**
- Produces:
  - `validate(spec: dict, surfaces: dict) -> list[str]` — returns human-readable error strings (empty = valid). `surfaces` maps `char_name -> digest_dict` (from Task 2).
  - `EXAMPLE_SPEC: dict` — a minimal valid two-character spec used in prompts and tests.

- [x] **Step 1: Write the failing test**

`tests/test_spec.py`:

```python
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
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /home/theta/.vault/repos/scenharnist && python -m pytest tests/test_spec.py -q`
Expected: FAIL (module `scenharnist.spec` not found).

- [x] **Step 3: Write `scenharnist/spec.py`**

```python
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
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd /home/theta/.vault/repos/scenharnist && python -m pytest tests/test_spec.py -q`
Expected: PASS (5 passed).

- [x] **Step 5: Commit**

```bash
cd /home/theta/.vault/repos/scenharnist
git add scenharnist/spec.py tests/test_spec.py
git commit -m "feat: scene spec schema + validation"
```

---

### Task 4: bake_render — Blender headless spec → frames/video/glb

**Files:**
- Create: `scenharnist/bake_render.py`
- Create: `scenharnist/render.py` (thin subprocess wrapper, importable/testable)
- Test: `tests/test_render_smoke.py`

**Interfaces:**
- Consumes: `resolution_table` from Task 2 (called inside Blender).
- Produces:
  - `scenharnist/render.py`: `render(spec_path: str, resmaps: dict, out_dir: str, mode: str, gltf_root: str) -> list[str]` — runs Blender as a subprocess, returns paths of produced files. `mode` ∈ `{"grid","video","glb"}`. `resmaps` maps `char_name -> resolution_table dict`.
  - `scenharnist/bake_render.py`: Blender-python entrypoint, invoked as `blender -b -P bake_render.py -- <spec.json> <resmaps.json> <out_dir> <mode> <gltf_root>`.

**Note:** `bake_render.py` runs inside Blender's bundled Python (has `bpy`), so it is not unit-tested directly; the smoke test drives it through `render()` and is skipped when `blender` is absent.

- [x] **Step 1: Write `scenharnist/render.py`**

```python
import json, os, shutil, subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPT = os.path.join(_HERE, "bake_render.py")

def blender_available():
    return shutil.which("blender") is not None

def render(spec_path, resmaps, out_dir, mode, gltf_root):
    """Run Blender headless to bake+render. Returns list of output file paths."""
    os.makedirs(out_dir, exist_ok=True)
    resmaps_path = os.path.join(out_dir, "_resmaps.json")
    with open(resmaps_path, "w", encoding="utf-8") as f:
        json.dump(resmaps, f)
    cmd = ["blender", "-b", "-noaudio", "-P", _SCRIPT, "--",
           spec_path, resmaps_path, out_dir, mode, gltf_root]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"blender failed ({mode}):\n{proc.stdout}\n{proc.stderr}")
    manifest = os.path.join(out_dir, f"_manifest_{mode}.json")
    with open(manifest, encoding="utf-8") as f:
        return json.load(f)
```

- [x] **Step 2: Write `scenharnist/bake_render.py`** (Blender-python)

```python
"""Runs inside Blender: blender -b -P bake_render.py -- spec resmaps out mode gltf_root."""
import bpy, json, math, os, sys

argv = sys.argv[sys.argv.index("--") + 1:]
SPEC_PATH, RESMAPS_PATH, OUT_DIR, MODE, GLTF_ROOT = argv[:5]

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

spec = load(SPEC_PATH)
resmaps = load(RESMAPS_PATH)
fps = int(spec["fps"])
dur = float(spec["duration"])
scene = bpy.context.scene

# Fresh scene.
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = fps
scene.frame_start = 1
scene.frame_end = max(2, int(round(dur * fps)))

def t_to_frame(t):
    return 1 + int(round(float(t) * fps))

def import_char(c):
    path = os.path.join(GLTF_ROOT, c["gltf"]) if not os.path.isabs(c["gltf"]) else c["gltf"]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next((o for o in new if o.type == "ARMATURE"), None)
    meshes = [o for o in new if o.type == "MESH"]
    # Root placement on the armature (or first new object).
    root = c.get("root", {})
    tx = root.get("translation", [0, 0, 0])
    holder = arm or (new[0] if new else None)
    if holder:
        holder.location = (tx[0], tx[1], tx[2])
        holder.rotation_mode = "XYZ"
        holder.rotation_euler = (0, 0, math.radians(root.get("yaw_deg", 0)))
    return arm, meshes

for c in spec["characters"]:
    rt = resmaps.get(c["name"], {"bones": {}, "morphs": {}})
    arm, meshes = import_char(c)
    # Bone tracks.
    if arm:
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="POSE")
        for en_bone, frames in (c.get("bone_tracks") or {}).items():
            cjk = rt["bones"].get(en_bone)
            pb = arm.pose.bones.get(cjk) if cjk else None
            if not pb:
                continue
            pb.rotation_mode = "XYZ"
            for fr in frames:
                e = fr["euler_deg"]
                pb.rotation_euler = (math.radians(e[0]), math.radians(e[1]), math.radians(e[2]))
                pb.keyframe_insert("rotation_euler", frame=t_to_frame(fr["t"]))
        bpy.ops.object.mode_set(mode="OBJECT")
    # Morph tracks.
    for en_morph, frames in (c.get("morph_tracks") or {}).items():
        cjk = rt["morphs"].get(en_morph)
        for m in meshes:
            sk = m.data.shape_keys
            kb = sk.key_blocks.get(cjk) if (sk and cjk) else None
            if not kb:
                continue
            for fr in frames:
                kb.value = float(fr["weight"])
                kb.keyframe_insert("value", frame=t_to_frame(fr["t"]))

# Camera + light.
cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
target = bpy.data.objects.new("CamTarget", None)
scene.collection.objects.link(target)
con = cam.constraints.new("TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
for fr in spec.get("camera", [{"t": 0, "position": [0, 1.2, 3], "look_at": [0, 1, 0]}]):
    f = t_to_frame(fr["t"])
    cam.location = tuple(fr["position"]); cam.keyframe_insert("location", frame=f)
    target.location = tuple(fr["look_at"]); target.keyframe_insert("location", frame=f)
light_data = bpy.data.lights.new("Sun", type="SUN"); light_data.energy = 3.0
light = bpy.data.objects.new("Sun", light_data); light.location = (2, -2, 4)
scene.collection.objects.link(light)
scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in \
    {i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"

produced = []
def render_still(frame, path):
    scene.frame_set(frame)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    produced.append(path)

if MODE == "grid":
    times = sorted({fr["t"] for c in spec["characters"]
                    for tr in list((c.get("bone_tracks") or {}).values())
                             + list((c.get("morph_tracks") or {}).values())
                    for fr in tr} | {0.0, dur})
    times = times[:9] if len(times) > 9 else times
    for i, t in enumerate(times):
        render_still(t_to_frame(t), os.path.join(OUT_DIR, f"frame_{i:02d}_t{t:.2f}.png"))
elif MODE == "video":
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    out = os.path.join(OUT_DIR, "preview.mp4")
    scene.render.filepath = out
    bpy.ops.render.render(animation=True)
    produced.append(out)
elif MODE == "glb":
    out = os.path.join(OUT_DIR, "scene.glb")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_animations=True)
    produced.append(out)

with open(os.path.join(OUT_DIR, f"_manifest_{MODE}.json"), "w", encoding="utf-8") as f:
    json.dump(produced, f)
```

- [x] **Step 3: Write the smoke test**

`tests/test_render_smoke.py`:

```python
import json, os, pytest
from scenharnist.render import render, blender_available
from scenharnist.rigdigest import resolution_table
from scenharnist.spec import EXAMPLE_SPEC

GLTF_ROOT = os.path.expanduser("~/.vault/repos/waifus.gltf")
HAVE = blender_available() and os.path.exists(GLTF_ROOT)

@pytest.mark.skipif(not HAVE, reason="blender or waifus.gltf missing")
def test_grid_render_produces_frames(tmp_path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(EXAMPLE_SPEC))
    resmaps = {c["name"]: resolution_table(os.path.join(GLTF_ROOT, c["gltf"]))
               for c in EXAMPLE_SPEC["characters"]}
    out = render(str(spec_path), resmaps, str(tmp_path / "out"), "grid", GLTF_ROOT)
    assert out and all(os.path.exists(p) for p in out)
```

- [x] **Step 4: Run test**

Run: `cd /home/theta/.vault/repos/scenharnist && python -m pytest tests/test_render_smoke.py -q`
Expected: PASS if Blender present, else SKIPPED. Iterate on `bake_render.py` until frames render (this is where MMD bone-axis reality is confirmed).

- [x] **Step 5: Commit**

```bash
cd /home/theta/.vault/repos/scenharnist
git add scenharnist/render.py scenharnist/bake_render.py tests/test_render_smoke.py
git commit -m "feat: Blender bake+render (grid/video/glb)"
```

---

### Task 5: loop — LiteLLM agent loop

**Files:**
- Create: `scenharnist/loop.py`
- Test: `tests/test_loop.py`

**Interfaces:**
- Consumes: `validate` (Task 3), `render` (Task 4).
- Produces: `run_loop(prompt, characters, model, out_dir, gltf_root, max_steps=5, completion=None, render_fn=None) -> dict` where `characters` is a list of `{"name","gltf","digest","resmap"}`. Returns the final spec dict. `completion` and `render_fn` are injectable for testing (default to `litellm.completion` and `render.render`).

- [x] **Step 1: Write the failing test** (mocks LLM + renderer — no Blender, no network)

`tests/test_loop.py`:

```python
import json
from scenharnist.loop import run_loop

SURF_A = {"bones": ["Arm.R"], "morphs": ["Anger"], "hint": "h"}
CHARS = [{"name": "Augusta", "gltf": "a.gltf", "digest": SURF_A, "resmap": {}}]

def _spec():
    return {"fps": 24, "duration": 1.0, "characters": [
        {"name": "Augusta", "gltf": "a.gltf", "root": {"translation": [0,0,0], "yaw_deg": 0},
         "bone_tracks": {"Arm.R": [{"t": 0.0, "euler_deg": [0,0,-40]}]},
         "morph_tracks": {}}],
        "camera": [{"t": 0.0, "position": [0,1,3], "look_at": [0,1,0]}]}

def _tool_msg(tool, args):
    return {"choices": [{"message": {"role": "assistant", "content": None,
        "tool_calls": [{"id": "1", "type": "function",
            "function": {"name": tool, "arguments": json.dumps(args)}}]}}]}

def test_loop_sets_scene_then_finishes(tmp_path):
    calls = iter([_tool_msg("set_scene", {"spec": _spec()}),
                  _tool_msg("finish", {"summary": "done"})])
    def fake_completion(**kw):
        return next(calls)
    rendered = []
    def fake_render(spec_path, resmaps, out_dir, mode, gltf_root):
        rendered.append(mode)
        return [f"{out_dir}/{mode}.out"]
    final = run_loop("boxing", CHARS, "test/model", str(tmp_path),
                     gltf_root=".", max_steps=5,
                     completion=fake_completion, render_fn=fake_render)
    assert final["duration"] == 1.0
    assert "grid" in rendered and "video" in rendered and "glb" in rendered

def test_loop_feeds_validation_errors_back(tmp_path):
    bad = _spec(); bad["characters"][0]["bone_tracks"]["Tail"] = [{"t":0,"euler_deg":[0,0,0]}]
    seen = []
    calls = iter([_tool_msg("set_scene", {"spec": bad}),
                  _tool_msg("set_scene", {"spec": _spec()}),
                  _tool_msg("finish", {"summary": "ok"})])
    def fake_completion(**kw):
        seen.append(kw["messages"])
        return next(calls)
    def fake_render(*a, **k):
        return ["x"]
    run_loop("p", CHARS, "m", str(tmp_path), gltf_root=".", max_steps=5,
             completion=fake_completion, render_fn=fake_render)
    # After the bad spec, an error message mentioning the unknown bone is fed back.
    flat = json.dumps(seen[-1])
    assert "Tail" in flat
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /home/theta/.vault/repos/scenharnist && python -m pytest tests/test_loop.py -q`
Expected: FAIL (module `scenharnist.loop` not found).

- [x] **Step 3: Write `scenharnist/loop.py`**

```python
import base64, json, os
from .spec import validate, EXAMPLE_SPEC

TOOLS = [
    {"type": "function", "function": {
        "name": "set_scene",
        "description": "Replace the entire scene spec. Re-emit the whole spec each call.",
        "parameters": {"type": "object", "properties": {"spec": {"type": "object"}},
                       "required": ["spec"]}}},
    {"type": "function", "function": {
        "name": "finish",
        "description": "Stop iterating; the current scene is final.",
        "parameters": {"type": "object", "properties": {"summary": {"type": "string"}},
                       "required": ["summary"]}}},
]

def _system(prompt, characters):
    lines = [
        "You are a 3D animation director. Produce a scene spec that matches the prompt.",
        "Drive ONLY the listed bones (local euler_deg rotations) and morphs (weight 0..1).",
        "Never reference bones/morphs not listed. Re-emit the FULL spec via set_scene each step.",
        "After each attempt you will SEE rendered frames; fix pose/timing/axis and call set_scene again.",
        "Call finish when the frames match the prompt.",
        f"\nPROMPT: {prompt}\n",
        "CHARACTERS AND THEIR CONTROL SURFACE:",
    ]
    for c in characters:
        d = c["digest"]
        lines.append(f"- {c['name']} (gltf={c['gltf']})")
        lines.append(f"    bones: {d['bones']}")
        lines.append(f"    morphs: {d['morphs']}")
        lines.append(f"    hint: {d['hint']}")
    lines.append("\nEXAMPLE SPEC SHAPE (adapt names to the real characters):")
    lines.append(json.dumps(EXAMPLE_SPEC, ensure_ascii=False))
    return "\n".join(lines)

def _image_content(paths):
    out = []
    for p in paths:
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        out.append({"type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"}})
    return out

def run_loop(prompt, characters, model, out_dir, gltf_root,
             max_steps=5, completion=None, render_fn=None):
    if completion is None:
        import litellm
        completion = litellm.completion
    if render_fn is None:
        from .render import render as render_fn
    os.makedirs(out_dir, exist_ok=True)
    surfaces = {c["name"]: c["digest"] for c in characters}
    resmaps = {c["name"]: c["resmap"] for c in characters}

    messages = [{"role": "system", "content": _system(prompt, characters)},
                {"role": "user", "content": "Author the first version, then call set_scene."}]
    final_spec = None

    for step in range(max_steps):
        resp = completion(model=model, messages=messages, tools=TOOLS,
                          tool_choice="required")
        msg = resp["choices"][0]["message"]
        messages.append({"role": "assistant", "content": msg.get("content"),
                         "tool_calls": msg["tool_calls"]})
        call = msg["tool_calls"][0]
        args = json.loads(call["function"]["arguments"])
        name = call["function"]["name"]

        if name == "finish":
            break

        spec = args["spec"]
        errs = validate(spec, surfaces)
        if errs:
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": "Spec rejected:\n" + "\n".join(errs)})
            continue

        final_spec = spec
        spec_path = os.path.join(out_dir, "scene.json")
        with open(spec_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
        iter_dir = os.path.join(out_dir, "iterations", f"step_{step:02d}")
        frames = render_fn(spec_path, resmaps, iter_dir, "grid", gltf_root)
        content = [{"type": "text",
                    "text": f"Rendered frames (step {step}). Fix issues or finish."}]
        content += _image_content(frames)
        messages.append({"role": "tool", "tool_call_id": call["id"],
                         "content": "rendered"})
        messages.append({"role": "user", "content": content})

    if final_spec is None:
        raise RuntimeError("model never produced a valid spec")
    spec_path = os.path.join(out_dir, "scene.json")
    render_fn(spec_path, resmaps, out_dir, "video", gltf_root)
    render_fn(spec_path, resmaps, out_dir, "glb", gltf_root)
    return final_spec
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd /home/theta/.vault/repos/scenharnist && python -m pytest tests/test_loop.py -q`
Expected: PASS (2 passed).

- [x] **Step 5: Commit**

```bash
cd /home/theta/.vault/repos/scenharnist
git add scenharnist/loop.py tests/test_loop.py
git commit -m "feat: LiteLLM agent loop with vision feedback"
```

---

### Task 6: CLI — character detection + wiring

**Files:**
- Create: `scenharnist/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `digest`, `resolution_table` (Task 2); `run_loop` (Task 5).
- Produces:
  - `detect_characters(prompt: str, gltf_root: str) -> list[str]` — dir names under `<gltf_root>/gltf` (stripping `.gltf`) that appear in the prompt (case-insensitive), longest-first, deduped.
  - `build_characters(names, gltf_root) -> list[dict]` — `{"name","gltf","digest","resmap"}`.
  - `main(argv=None) -> int` — argparse entrypoint.

- [x] **Step 1: Write the failing test**

`tests/test_cli.py`:

```python
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
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd /home/theta/.vault/repos/scenharnist && python -m pytest tests/test_cli.py -q`
Expected: FAIL (module `scenharnist.cli` not found).

- [x] **Step 3: Write `scenharnist/cli.py`**

```python
import argparse, os, sys
from .rigdigest import digest, resolution_table
from .loop import run_loop

def detect_characters(prompt, gltf_root):
    gdir = os.path.join(gltf_root, "gltf")
    names = [d[:-5] for d in os.listdir(gdir)
             if d.endswith(".gltf") and os.path.isdir(os.path.join(gdir, d))]
    low = prompt.lower()
    hits = [n for n in names if n.lower() in low]
    hits.sort(key=len, reverse=True)
    seen, out = set(), []
    for n in hits:
        if n not in seen:
            seen.add(n); out.append(n)
    return out

def build_characters(names, gltf_root):
    chars = []
    for n in names:
        rel = os.path.join("gltf", f"{n}.gltf", f"{n}.gltf")
        full = os.path.join(gltf_root, rel)
        chars.append({"name": n, "gltf": rel,
                      "digest": digest(full), "resmap": resolution_table(full)})
    return chars

def main(argv=None):
    ap = argparse.ArgumentParser(prog="scenharnist")
    ap.add_argument("prompt")
    ap.add_argument("--model", default="anthropic/claude-opus-4-8")
    ap.add_argument("--out", required=True)
    ap.add_argument("--chars", nargs="*", default=None)
    ap.add_argument("--max-steps", type=int, default=5)
    ap.add_argument("--gltf-root", default=os.path.expanduser("~/.vault/repos/waifus.gltf"))
    a = ap.parse_args(argv)

    names = a.chars or detect_characters(a.prompt, a.gltf_root)
    if not names:
        print("No characters detected; pass --chars.", file=sys.stderr)
        return 2
    print(f"Characters: {names}")
    chars = build_characters(names, a.gltf_root)
    spec = run_loop(a.prompt, chars, a.model, a.out, a.gltf_root, a.max_steps)
    print(f"Done. Outputs in {a.out}/ (scene.glb, preview.mp4, scene.json)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd /home/theta/.vault/repos/scenharnist && python -m pytest tests/test_cli.py -q`
Expected: PASS (3 passed).

- [x] **Step 5: Run the full suite**

Run: `cd /home/theta/.vault/repos/scenharnist && python -m pytest -q`
Expected: all pass (Blender/waifus-gated tests may SKIP).

- [x] **Step 6: Commit**

```bash
cd /home/theta/.vault/repos/scenharnist
git add scenharnist/cli.py tests/test_cli.py
git commit -m "feat: CLI with character detection"
```

---

### Task 7: Packaging — flake.nix + README

**Files:**
- Create: `flake.nix`
- Create: `README.md`

**Interfaces:** none (packaging only).

- [x] **Step 1: Write `flake.nix`**

Provides a dev shell + `nix run` app with Python (litellm) and Blender on PATH. Mirror `waifus.gltf`'s platform matrix.

```nix
{
  description = "scenharnist — prompt -> animated glTF + video via any LLM";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachSystem [
      "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"
    ] (system:
      let
        pkgs = import nixpkgs { inherit system; config.allowUnfree = true; };
        py = pkgs.python311.withPackages (p: [ p.litellm p.pytest ]);
        deps = [ py pkgs.blender ];
      in {
        devShells.default = pkgs.mkShell { packages = deps; };
        apps.default = {
          type = "app";
          program = toString (pkgs.writeShellScript "scenharnist" ''
            export PATH=${pkgs.lib.makeBinPath deps}:$PATH
            cd ${self}
            exec ${py}/bin/python -m scenharnist.cli "$@"
          '');
        };
        apps.test = {
          type = "app";
          program = toString (pkgs.writeShellScript "scenharnist-test" ''
            export PATH=${pkgs.lib.makeBinPath deps}:$PATH
            cd ${self} && exec ${py}/bin/python -m pytest -q
          '');
        };
      });
}
```

- [x] **Step 2: Verify the flake evaluates** (if nix available)

Run: `cd /home/theta/.vault/repos/scenharnist && nix flake check 2>&1 | tail -5 || echo "nix not available — skip"`
Expected: no evaluation errors (or skip if `litellm` is not in the pinned nixpkgs — in that case fall back to documenting `pip install -e .` in the README and drop `p.litellm` from the flake, keeping Blender).

- [x] **Step 3: Write `README.md`**

````markdown
# scenharnist

Turn a prompt into an animated glTF + video. Any LiteLLM model (Claude, GPT, Gemini…)
iteratively poses characters from a `waifus.gltf`-layout database, driving only rig
rotations, root translation, and morphs — never meshes — while watching rendered previews.

## Usage

```bash
export ANTHROPIC_API_KEY=...           # or the key for your chosen provider
nix run . -- "Augusta and Baizhi are boxing" --out output/boxing
# or without nix:
pip install -e . && python -m scenharnist.cli "Augusta and Baizhi are boxing" --out output/boxing
```

Outputs land in `output/boxing/`: `scene.glb`, `preview.mp4`, `scene.json`, `iterations/`.

## Flags

| Flag | Default | Meaning |
|------|---------|---------|
| `--model` | `anthropic/claude-opus-4-8` | LiteLLM model string (must support vision + tools) |
| `--out` | (required) | output directory |
| `--chars` | auto-detected from prompt | explicit character names |
| `--max-steps` | 5 | max author→render iterations |
| `--gltf-root` | `~/.vault/repos/waifus.gltf` | root holding `gltf/<Char>.gltf/` |

## How it works

1. `rigdigest` builds a small English **control surface** (~25 bones + ~15 morphs) per character — no mesh data.
2. The model authors a **scene spec** (JSON) via `set_scene`; `spec.validate` rejects unknown names before rendering.
3. `bake_render` (Blender headless) bakes the spec and renders a pose-grid; the model sees it and revises.
4. On `finish` (or max steps): final `preview.mp4` + `scene.glb`.

## Requirements

Blender on PATH; a vision+tool-call capable model. Tests: `python -m pytest -q`
(Blender/database-dependent tests skip when unavailable).
````

- [x] **Step 4: Commit**

```bash
cd /home/theta/.vault/repos/scenharnist
git add flake.nix README.md
git commit -m "chore: nix flake + README"
```

---

## Notes for the implementer

- **Task 4 is the reality-check.** MMD bone rest orientations are quirky; the first grid render will reveal whether `euler_deg` axes bend limbs sensibly. Adjust `bake_render.py` (e.g. rotation order) until a hand-written `EXAMPLE_SPEC` produces a recognizable pose. The vision loop tolerates residual axis quirks — the model corrects them — but a totally broken mapping wastes iterations.
- **Blender engine identifier** differs across versions (`BLENDER_EEVEE` vs `BLENDER_EEVEE_NEXT`); the script probes for it.
- **Do not** add mesh manipulation, physics sim, or a patch protocol — explicitly out of scope (see spec).
- Run `python -m pytest -q` after each task; non-gated tests must stay green.
