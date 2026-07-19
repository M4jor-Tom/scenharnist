# scenharnist — design

**Status:** approved (brainstorming), pending implementation plan
**Date:** 2026-07-19

## One-liner

A Python CLI that turns a natural-language prompt (e.g. *"Augusta and Baizhi are
doing boxing"*) into an **animated glTF + a preview video**, by letting any
[LiteLLM](https://docs.litellm.ai/)-supported model (Claude as a first-class
target) iteratively author a compact **scene spec** while watching rendered
previews. The model steers **rig rotations, root translation, and morph weights
only — never mesh vertices** — to keep token cost low.

## Inputs / outputs

- **Input:** a prompt + one or more source models from a glTF database with the
  `waifus.gltf` directory layout: `gltf/<Char>.gltf/<Char>.gltf` (+ `.bin` +
  textures). Characters are auto-detected by matching directory names appearing
  in the prompt, overridable with `--chars`.
- **Output** (per run, under `--out <dir>/`):
  - `scene.glb` — combined, animated glTF the user can open in any viewer.
  - `preview.mp4` — rendered video of the animation.
  - `scene.json` — the final scene spec (source of truth, human-editable).
  - `iterations/` — the per-step pose-grid contact sheets (debug/history).

## Provider layer

- **LiteLLM unified.** Provider + model selected entirely by the `--model`
  string, e.g. `anthropic/claude-opus-4-8`, `gpt-5`, `gemini/...`.
- Requires a model with **vision** (to read pose grids) and **tool/function
  calls** (to emit the scene spec). Documented as a hard requirement; Claude is
  the reference target.
- API keys via standard LiteLLM environment variables.

## Architecture — 4 units + CLI

Each unit has one purpose, a defined interface, and can be tested on its own.

### 1. `rigdigest.py` (no Blender)

Reads a source `.gltf` and produces the **control surface** — the only view of
the rig the model ever sees.

- Applies the reused CJK→English **`BONE_MAP`** (copied/adapted from
  `waifus.gltf/scripts/pmx_bone_rename.py`, which already covers the full
  standard MMD humanoid set with `.L/.R` side handling) to the skin's joint
  node names.
- Applies a **new curated morph map** (CJK→English) covering ~15 common MMD
  expression morphs (blink, smile, anger, open-mouth `あ/い/う/え/お`, etc.);
  morphs with no mapping are omitted from the control surface.
- Emits:
  - the shortlist of ~25 drivable humanoid bones + ~15 morphs (English names,
    with rest-pose / rotation-axis hints),
  - an **English→CJK resolution table** (bone and morph) consumed at bake time.
- Contains **no vertex/mesh data** — that is the whole point.

**Interface:** `digest(gltf_path) -> ControlSurface` and
`resolution_table(gltf_path) -> {bones: {en: cjk}, morphs: {en: cjk}}`.

### 2. Scene spec (JSON) — single source of truth

The one artifact the model edits. Full-replace protocol: the model re-emits the
whole spec each step (specs are a few KB thanks to the curated rig, so no patch
engine — YAGNI). Shape:

```json
{
  "fps": 24,
  "duration": 3.0,
  "characters": [
    {
      "name": "Augusta",
      "gltf": "gltf/Augusta.gltf/Augusta.gltf",
      "root": { "translation": [-0.5, 0, 0], "yaw_deg": 90 },
      "bone_tracks": {
        "Arm.R": [ { "t": 0.0, "euler_deg": [0, 0, -70] },
                   { "t": 0.5, "euler_deg": [0, 0, -10] } ]
      },
      "morph_tracks": {
        "Anger": [ { "t": 0.0, "weight": 0.0 }, { "t": 0.5, "weight": 1.0 } ]
      }
    }
  ],
  "camera": [ { "t": 0.0, "position": [0, 1.2, 3], "look_at": [0, 1, 0] } ]
}
```

- `euler_deg` = local bone rotation in degrees (intuitive to author; Blender
  converts to the correct quaternion relative to the bone's rest pose).
- `pos` (optional per bone keyframe) for translation channels; used mainly on
  the root.
- A JSON-schema + `validate(spec)` rejects unknown bone/morph names (must exist
  in that character's control surface), out-of-range times, etc., **before**
  Blender runs — validation errors are fed back to the model as text.

### 3. `bake_render.py` (Blender headless)

Input = a scene spec + output dir + mode. Blender owns **all** glTF /
quaternion / morph / binary math — our Python never touches the `.bin`.

- Imports each character `.gltf`.
- Remaps English track names → the real CJK pose-bone / shape-key names via the
  resolution table.
- Inserts keyframes: pose-bone rotations (euler_deg → bone-local quaternion),
  shape-key values (morph weights), root placement (translation + yaw).
- Sets camera keyframes + lights (matching the `waifus.gltf` Eevee look).
- Renders one of three **modes**:
  - `grid` — a 6–9 still **contact sheet** sampled at keyframe times → the
    per-iteration feedback image. Cheap and fast.
  - `video` — the final `preview.mp4`.
  - `glb` — exports the combined animated `scene.glb`.
- Invoked as a subprocess: `blender -b -P bake_render.py -- spec.json outdir mode`.

Physics bones (hair, skirt, ribbon) are **not** exposed to the model; they are
left to Blender defaults (static in v1).

### 4. `loop.py` (LiteLLM agent loop)

- Builds initial context: the prompt + each character's control surface (from
  `rigdigest`).
- Exposes two tools to the model:
  - `set_scene(spec)` — replace the whole scene spec.
  - `finish(summary)` — stop iterating.
- Per `set_scene`: `validate` → render `grid` → feed the contact sheet back as
  image(s) (+ any validation errors as text).
- Terminates on `finish` or `--max-steps` (default 5).
- On termination: render `video` + `glb`, write final `scene.json`.

### CLI

```
scenharnist "Augusta and Baizhi are boxing" \
  --model anthropic/claude-opus-4-8 \
  --out output/boxing \
  [--chars Augusta Baizhi] [--max-steps 5] [--gltf-root ../waifus.gltf]
```

## Data flow

```
prompt + rig digests
  → [ model set_scene → validate → Blender grid render → images back ] × N
  → finish / max-steps
  → Blender video + glb
  → output/<slug>/{scene.glb, preview.mp4, scene.json, iterations/}
```

## Key risk — the calibration knob

MMD bones have quirky local rest orientations, so "rotate the elbow 90°" may need
an unexpected axis or sign. **The iterative vision loop is the correction
mechanism**: the model sees the wrong bend in the pose grid and flips the
axis/sign next step. Mitigations:

- rest-pose / axis hints included in the control surface digest,
- physics bones left to Blender defaults rather than exposed,
- validation catches structural errors early so iterations spend on *motion*,
  not syntax.

MMD leg IK bones (`足ＩＫ`) carry no IK constraints once in glTF, so exposing FK
`Leg/Knee/Ankle` rotations is sufficient and correct.

## Scope

**v1 (this spec):**
- 1–2 characters, static-or-simple (keyframed) camera.
- Pose-grid feedback, max 5 iterations.
- Outputs `scene.glb` + `preview.mp4` + `scene.json`.
- Full-replace scene spec (no patch protocol).

**Deferred (YAGNI) — each slots in without reworking the spec:**
- hair/skirt physics simulation,
- multi-shot / camera cuts, audio,
- more than 2 characters,
- a preset-pose / motion-clip library,
- incremental patch protocol for large specs.

## Packaging & testing

- **Python.** Deps: `litellm`, Blender (headless). Packaged with a `flake.nix`
  mirroring `waifus.gltf` so `nix run` works; Blender pulled the same way the
  sibling repo's `gltf_to_webm` input does.
- **Tests (minimal, runnable):**
  - no-Blender: `rigdigest` on `Augusta` asserts it surfaces `Head`, `Arm.L`,
    `Leg.R`, etc.; `validate()` rejects an unknown bone name.
  - Blender-gated: a tiny hand-written spec bakes + renders a single frame
    (skipped when Blender is unavailable).

## Reuse from `waifus.gltf`

- `BONE_MAP` (CJK→English bones) from `scripts/pmx_bone_rename.py`.
- Blender headless render conventions (Eevee, camera/lighting) from the
  `gltf_to_png` / `gltf_to_webm` flake inputs.
- `flake.nix` structure and platform matrix.
