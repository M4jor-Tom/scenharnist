# Prompting (eval) tests — design

**Status:** approved (brainstorming), pending implementation plan
**Date:** 2026-07-19

## One-liner

Opt-in, end-to-end "does this prompt produce the right video?" tests. Each case
runs a predefined prompt through the real pipeline (model authors → Blender
renders), then a vision model describes representative frames; the test passes
when the description contains at least K of N expected keywords.

## Relationship to existing tests

The current `tests/` are **deterministic** — they mock the LLM completion and
the renderer, so they need no network, API key, or Blender. Those stay exactly
as they are and remain the default suite. The prompting tests are a **separate,
opt-in, non-deterministic** layer that exercises the real agent + renderer.

## Gating

- Prompting tests carry a custom marker: `@pytest.mark.prompting`.
- The marker is **deselected by default** via pytest config
  (`addopts = -m "not prompting"` in `pyproject.toml`), so a plain `pytest`
  run executes only the deterministic suite — green offline, everywhere.
- `pytest -m prompting` runs them. When run, if the **agent is not available**
  (no API key, `litellm` not importable, Blender not on PATH, or the gltf
  database not resolvable) the test **fails red** with a clear message — it is
  NOT silently skipped. "Skipping" these tests = simply not selecting the
  marker.
- Individual cases are selectable: `pytest -m prompting -k salsa`.

Rationale: the user wants missing agents to surface as red when the prompting
suite is explicitly run, while keeping the everyday suite green without secrets.

## gltf database linking (flake input, shared by CLI + tests)

One mechanism answers "where is the database" for both the CLI and the tests.

- `flake.nix` gains an input:
  `waifus.url = "github:M4jor-Tom/waifus.gltf"` (pinned in `flake.lock`). Its
  store path root contains `gltf/<Char>.gltf/<Char>.gltf` (+ `.bin` + textures).
- A `test-prompting` flake app exports `SCENHARNIST_GLTF_ROOT=${waifus}`, puts
  Blender + Python on PATH, and runs `pytest -m prompting`.
- New central resolver `scenharnist/paths.py`:
  `resolve_gltf_root(explicit: str | None = None) -> str` with precedence:
  1. `explicit` (the CLI `--gltf-root` value, when given),
  2. `SCENHARNIST_GLTF_ROOT` environment variable,
  3. built-in default `~/.vault/repos/waifus.gltf`.
  Returns the first path that exists; raises `FileNotFoundError` with the tried
  locations if none exist.
- `scenharnist/cli.py` uses `resolve_gltf_root(a.gltf_root)` instead of a raw
  default, so CLI and tests share one source of truth.
- Local dev can set `SCENHARNIST_GLTF_ROOT` to a working checkout to avoid
  re-fetching the (large) flake input.

## Components

### 1. `scenharnist/paths.py` (new, product code)

`resolve_gltf_root(explicit=None) -> str` as specified above. Small, pure,
importable, unit-testable without network/Blender.

### 2. `scenharnist/cli.py` (modified)

`--gltf-root` default becomes `None`; `main` calls
`resolve_gltf_root(a.gltf_root)`. Behavior unchanged when the env/default
resolves to the same path; deterministic `detect_characters` tests are
unaffected (they pass an explicit root).

### 3. `tests/prompting_cases.py` (new, test data)

A list of case dicts:

```python
CASES = [
    {"name": "boxing",  "prompt": "Augusta and Baizhi are boxing",
     "chars": ["Augusta", "Baizhi"],
     "keywords": ["two", "fighting", "punch", "boxing", "arms", "fists", "facing"],
     "min_hits": 3},
    {"name": "running", "prompt": "Augusta and Baizhi are running next to each other",
     "chars": ["Augusta", "Baizhi"],
     "keywords": ["two", "running", "run", "legs", "forward", "side"],
     "min_hits": 3},
    {"name": "walking", "prompt": "Augusta and Baizhi are walking next to each other",
     "chars": ["Augusta", "Baizhi"],
     "keywords": ["two", "walking", "walk", "legs", "side", "together"],
     "min_hits": 3},
    {"name": "burpees", "prompt": "Augusta and Baizhi are making burpees",
     "chars": ["Augusta", "Baizhi"],
     "keywords": ["two", "squat", "jump", "down", "up", "exercise", "floor"],
     "min_hits": 3},
    {"name": "salsa",   "prompt": "Augusta and Baizhi are dancing salsa together",
     "chars": ["Augusta", "Baizhi"],
     "keywords": ["two", "dancing", "dance", "salsa", "partner", "arms"],
     "min_hits": 3},
]
```

Keyword matching is case-insensitive substring; listing synonyms as separate
keywords makes the `min_hits` threshold tolerant of the describer's wording.

### 4. `tests/test_prompting.py` (new)

- `describe_frames(frame_paths, model) -> str` — sends the frames as images to a
  vision model through the app's LiteLLM layer with a **neutral** prompt
  ("Describe what each character is doing and how they interact"). The prompt
  must NOT mention any case keyword — otherwise the test is circular.
- `_agent_available() -> str | None` — returns None if runnable, else a reason
  string (missing API key, litellm import error, Blender absent, database
  unresolvable). When a case runs and this returns a reason, the test
  `pytest.fail(reason)` (red, not skip).
- Parametrized over `CASES`:
  1. `root = resolve_gltf_root()`; `chars = build_characters(case["chars"], root)`
  2. `run_loop(case["prompt"], chars, model, out_dir, root, max_steps=2)`
  3. `stills = render(scene_json, resmaps, out_dir, "grid", root)` on the
     returned final spec — representative frames, same content as `preview.mp4`,
     no ffmpeg dependency.
  4. `desc = describe_frames(stills, describer_model)`
  5. `hits = [k for k in case["keywords"] if k.lower() in desc.lower()]`
  6. `assert len(hits) >= case["min_hits"]`, message includes the full
     description and the missed keywords.

### 5. `flake.nix` (modified)

Add the `waifus` input and a `test-prompting` app (see gltf linking above).

### 6. `pyproject.toml` (modified)

Register the marker and deselect it by default:

```toml
[tool.pytest.ini_options]
markers = ["prompting: live end-to-end prompt->video->describe eval (opt-in)"]
addopts = "-m 'not prompting'"
```

## Data flow

```
pytest -m prompting
  → resolve_gltf_root()  (env from flake input, or default)
  → run_loop(prompt, ...) : real model authors + Blender renders (max_steps=2)
  → render(final_spec, "grid") : representative stills
  → describe_frames(stills, describer_model) : neutral vision description
  → keyword hits >= min_hits ? green : red (prints description + misses)
```

## Configuration (env)

- `SCENHARNIST_MODEL` — authoring model (LiteLLM string; default
  `anthropic/claude-opus-4-8`).
- `SCENHARNIST_DESCRIBER_MODEL` — describer model (default = authoring model).
- `SCENHARNIST_GLTF_ROOT` — database root (set by the flake app; overridable).

## Non-determinism

Authoring and describing are both fuzzy. The `min_hits` threshold absorbs
wording variation; the neutral describe prompt prevents circularity. These
tests are opt-in and NOT part of the blocking green suite. v1 does one describe
call per case (no retries).

## Testing the harness itself

The describer and keyword logic have a deterministic seam worth a unit test
(in the default suite): a `keyword_hits(description, keywords)` helper
extracted from the test body, unit-tested with a canned description string, so
the matching logic is verified without any agent. `resolve_gltf_root` also gets
a deterministic unit test (env precedence, missing-path error) using tmp dirs
and monkeypatched env.

## Out of scope (follow-ups)

- **Leg calibration.** running / walking / burpees / salsa depend on leg motion
  (Leg/Knee/Ankle), which is not yet calibrated (only arms are). The model may
  author these but they may fail the keyword check until legs are calibrated or
  the model improves. This is the eval surfacing a real gap, not a harness bug.
  Tracked as a separate follow-up.
- Literal mp4-frame extraction (would add an ffmpeg dependency); v1 describes a
  grid of the final spec instead — identical animation content.
- Describe-call retries / multi-run averaging.

## Reuse

Leans on existing `build_characters`, `run_loop`, `render`, and the LiteLLM
layer. New product code is only the small `resolve_gltf_root`; everything else
is test-scoped.
