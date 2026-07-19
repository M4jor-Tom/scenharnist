# Prompting (eval) Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add opt-in, end-to-end "does this prompt produce the right video?" tests that run a predefined prompt through the real pipeline, have a vision model describe the result, and pass when the description contains ≥K of N keywords — plus a shared gltf-database resolver used by the CLI and the tests.

**Architecture:** A small product resolver (`resolve_gltf_root`) centralizes "where is the database" for CLI + tests. Prompting tests live under a deselected-by-default `prompting` pytest marker; when selected they run the real `run_loop`, render a grid of the final spec, describe it via LiteLLM vision, and assert keyword hits. The gltf database is wired in via a `waifus` flake input.

**Tech Stack:** Python 3.11+, pytest (markers), LiteLLM (vision), Blender headless, nix flake input.

## Global Constraints

- Package `scenharnist`; tests via `pytest`. There is no system python/blender; run tests with `bash .superpowers/sdd/pytest.sh <args>` (ad-hoc nix python+pytest). Blender-/agent-dependent behavior is verified separately as noted per task.
- The existing deterministic suite MUST stay green offline. A plain `pytest` run must NOT execute the prompting tests.
- Prompting tests carry `@pytest.mark.prompting`, deselected by default via `addopts = "-m 'not prompting'"`. When run with `-m prompting` and the agent is unavailable, they FAIL RED (via `pytest.fail`), never skip.
- gltf resolver precedence, used by CLI and tests: `explicit` (CLI `--gltf-root`) → `SCENHARNIST_GLTF_ROOT` env → default `~/.vault/repos/waifus.gltf`. First path whose `<root>/gltf` dir exists wins; else `FileNotFoundError` listing tried paths.
- Live tests run `run_loop(..., max_steps=2)`, then describe a **grid of the final spec** (no ffmpeg).
- The describe prompt is NEUTRAL and must not contain any case keyword (else the test is circular).
- Keyword match = case-insensitive substring; pass when `len(hits) >= min_hits`.
- Test module `tests/test_prompting.py` must be IMPORTABLE without litellm or an API key (import litellm only inside functions), so default collection works in the no-litellm env.
- flake input: `waifus.url = "github:M4jor-Tom/waifus.gltf"` with `flake = false`; a `test-prompting` app exports `SCENHARNIST_GLTF_ROOT=${waifus}`.

---

### Task 1: gltf-root resolver + CLI wiring

**Files:**
- Create: `scenharnist/paths.py`
- Modify: `scenharnist/cli.py`
- Test: `tests/test_paths.py`

**Interfaces:**
- Produces: `resolve_gltf_root(explicit: str | None = None) -> str`.
- Consumes: nothing from other tasks.

- [x] **Step 1: Write the failing test**

`tests/test_paths.py`:

```python
import pytest
from scenharnist.paths import resolve_gltf_root

def _mkroot(tmp_path):
    (tmp_path / "gltf").mkdir()
    return str(tmp_path)

def test_explicit_wins_over_env(tmp_path, monkeypatch):
    root = _mkroot(tmp_path)
    monkeypatch.setenv("SCENHARNIST_GLTF_ROOT", "/nonexistent/db")
    assert resolve_gltf_root(root) == root

def test_env_used_when_no_explicit(tmp_path, monkeypatch):
    root = _mkroot(tmp_path)
    monkeypatch.setenv("SCENHARNIST_GLTF_ROOT", root)
    assert resolve_gltf_root() == root

def test_skips_paths_without_gltf_subdir(tmp_path, monkeypatch):
    good = _mkroot(tmp_path / "good"); (tmp_path / "bare").mkdir()
    monkeypatch.setenv("SCENHARNIST_GLTF_ROOT", good)
    # explicit points at a dir with no gltf/ -> falls through to env
    assert resolve_gltf_root(str(tmp_path / "bare")) == good

def test_missing_everywhere_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENHARNIST_GLTF_ROOT", str(tmp_path / "nope"))
    monkeypatch.setattr("scenharnist.paths._DEFAULT", str(tmp_path / "alsonope"))
    with pytest.raises(FileNotFoundError):
        resolve_gltf_root()
```

Note: `_mkroot(tmp_path / "good")` needs the dir made first — adjust `_mkroot` to `mkdir(parents=True)`:

```python
def _mkroot(tmp_path):
    (tmp_path / "gltf").mkdir(parents=True)
    return str(tmp_path)
```

- [x] **Step 2: Run test to verify it fails**

Run: `bash .superpowers/sdd/pytest.sh tests/test_paths.py -q`
Expected: FAIL (module `scenharnist.paths` not found).

- [x] **Step 3: Write `scenharnist/paths.py`**

```python
import os

_DEFAULT = os.path.expanduser("~/.vault/repos/waifus.gltf")

def resolve_gltf_root(explicit=None):
    """Resolve the gltf database root (a dir containing a `gltf/` subdir).

    Precedence: explicit (CLI --gltf-root) -> $SCENHARNIST_GLTF_ROOT -> default.
    Returns the first candidate whose `<root>/gltf` exists; raises
    FileNotFoundError listing the tried candidates if none qualify.
    """
    tried = []
    for cand in (explicit, os.environ.get("SCENHARNIST_GLTF_ROOT"), _DEFAULT):
        if not cand:
            continue
        tried.append(cand)
        if os.path.isdir(os.path.join(cand, "gltf")):
            return cand
    raise FileNotFoundError(
        "no gltf database found (need <root>/gltf/); tried: " + ", ".join(tried or ["<none>"]))
```

- [x] **Step 4: Run test to verify it passes**

Run: `bash .superpowers/sdd/pytest.sh tests/test_paths.py -q`
Expected: PASS (4 passed).

- [x] **Step 5: Wire the resolver into `scenharnist/cli.py`**

In `scenharnist/cli.py`, add the import near the top (after the existing imports):

```python
from .paths import resolve_gltf_root
```

Change the `--gltf-root` argument default to `None`:

```python
    ap.add_argument("--gltf-root", default=None)
```

Replace the body of `main` from the `names = ...` line through the `run_loop` call so it resolves the root once:

```python
    gltf_root = resolve_gltf_root(a.gltf_root)
    names = a.chars or detect_characters(a.prompt, gltf_root)
    if not names:
        print("No characters detected; pass --chars.", file=sys.stderr)
        return 2
    print(f"Characters: {names}")
    chars = build_characters(names, gltf_root)
    spec = run_loop(a.prompt, chars, a.model, a.out, gltf_root, a.max_steps)
    print(f"Done. Outputs in {a.out}/ (scene.glb, preview.mp4, scene.json)")
    return 0
```

(Delete the old `os.path.expanduser("~/.vault/repos/waifus.gltf")` default and the old `a.gltf_root` usages.)

- [x] **Step 6: Run the full suite to confirm nothing broke**

Run: `bash .superpowers/sdd/pytest.sh -q`
Expected: all pass, 1 skipped (Blender smoke). `test_cli.py` still passes (it calls `detect_characters` with an explicit root, unaffected).

- [x] **Step 7: Commit**

```bash
cd /home/theta/.vault/repos/scenharnist
git add scenharnist/paths.py scenharnist/cli.py tests/test_paths.py
git commit -m "feat: central resolve_gltf_root() shared by CLI and tests"
```

---

### Task 2: prompting marker + cases + keyword logic (deterministic)

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/conftest.py`
- Create: `tests/prompting_cases.py`
- Test: `tests/test_prompting_cases.py`

**Interfaces:**
- Produces: `CASES: list[dict]` and `keyword_hits(description: str, keywords: list[str]) -> list[str]` in `tests/prompting_cases.py`.
- Consumes: nothing.

- [ ] **Step 1: Register the marker and deselect it by default in `pyproject.toml`**

Append to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "prompting: live end-to-end prompt->video->describe eval (opt-in; needs agent + blender + db)",
]
addopts = "-m 'not prompting'"
```

- [ ] **Step 2: Make `tests/` sibling modules importable — `tests/conftest.py`**

```python
import os, sys
# Let test modules import the flat helper module `prompting_cases`.
sys.path.insert(0, os.path.dirname(__file__))
```

- [ ] **Step 3: Write the failing test**

`tests/test_prompting_cases.py`:

```python
from prompting_cases import CASES, keyword_hits

def test_keyword_hits_case_insensitive_substrings():
    desc = "Two characters face each other and throw PUNCHES with raised arms."
    hits = keyword_hits(desc, ["two", "punch", "arms", "salsa"])
    assert set(hits) == {"two", "punch", "arms"}

def test_cases_well_formed_and_complete():
    names = set()
    for c in CASES:
        assert {"name", "prompt", "chars", "keywords", "min_hits"} <= set(c)
        assert c["chars"], "each case names its characters"
        assert 1 <= c["min_hits"] <= len(c["keywords"])
        assert c["name"] not in names
        names.add(c["name"])
    assert {"boxing", "running", "walking", "burpees", "salsa"} <= names
```

- [ ] **Step 4: Run test to verify it fails**

Run: `bash .superpowers/sdd/pytest.sh tests/test_prompting_cases.py -q`
Expected: FAIL (module `prompting_cases` not found).

- [ ] **Step 5: Write `tests/prompting_cases.py`**

```python
"""Case data + keyword-match logic for the live prompting eval tests."""

CASES = [
    {"name": "boxing", "prompt": "Augusta and Baizhi are boxing",
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
    {"name": "salsa", "prompt": "Augusta and Baizhi are dancing salsa together",
     "chars": ["Augusta", "Baizhi"],
     "keywords": ["two", "dancing", "dance", "salsa", "partner", "arms"],
     "min_hits": 3},
]

def keyword_hits(description, keywords):
    """Case-insensitive substring hits of `keywords` within `description`."""
    d = (description or "").lower()
    return [k for k in keywords if k.lower() in d]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `bash .superpowers/sdd/pytest.sh tests/test_prompting_cases.py -q`
Expected: PASS (2 passed).

- [ ] **Step 7: Confirm the default suite is unchanged and green**

Run: `bash .superpowers/sdd/pytest.sh -q`
Expected: all pass, 1 skipped. (No prompting-marked test exists yet, so `addopts` is inert here.)

- [ ] **Step 8: Commit**

```bash
cd /home/theta/.vault/repos/scenharnist
git add pyproject.toml tests/conftest.py tests/prompting_cases.py tests/test_prompting_cases.py
git commit -m "feat: prompting marker (deselected by default) + cases + keyword_hits"
```

---

### Task 3: the live prompting test

**Files:**
- Create: `tests/test_prompting.py`

**Interfaces:**
- Consumes: `resolve_gltf_root` (Task 1); `CASES`, `keyword_hits` (Task 2); `build_characters` (cli), `run_loop` (loop), `render`/`blender_available` (render).
- Produces: `describe_frames(frame_paths, model) -> str`; parametrized `test_prompt_produces_expected_video`.

- [ ] **Step 1: Write `tests/test_prompting.py`**

```python
import base64, os, pytest
from scenharnist.paths import resolve_gltf_root
from scenharnist.render import render, blender_available
from scenharnist.cli import build_characters
from scenharnist.loop import run_loop
from prompting_cases import CASES, keyword_hits

_KEY_ENVS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY")

def _agent_unavailable_reason():
    """Return a reason string if the live pipeline can't run, else None."""
    try:
        import litellm  # noqa: F401
    except Exception as e:
        return f"litellm not importable: {e}"
    if not any(os.environ.get(k) for k in _KEY_ENVS):
        return "no API key in env (" + ", ".join(_KEY_ENVS) + ")"
    if not blender_available():
        return "blender not on PATH"
    try:
        resolve_gltf_root()
    except Exception as e:
        return str(e)
    return None

def describe_frames(frame_paths, model):
    """Ask a vision model to describe the frames. NEUTRAL prompt — no case keywords."""
    import litellm
    content = [{"type": "text", "text": (
        "Describe what each character is doing and how they interact. "
        "Be concrete about body pose and motion. Answer in 1-3 sentences.")}]
    for p in frame_paths:
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"}})
    resp = litellm.completion(model=model, messages=[{"role": "user", "content": content}])
    return resp["choices"][0]["message"]["content"] or ""

@pytest.mark.prompting
@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_prompt_produces_expected_video(case, tmp_path):
    reason = _agent_unavailable_reason()
    if reason:
        pytest.fail(f"agent unavailable: {reason}")
    model = os.environ.get("SCENHARNIST_MODEL", "anthropic/claude-opus-4-8")
    describer = os.environ.get("SCENHARNIST_DESCRIBER_MODEL", model)
    root = resolve_gltf_root()
    chars = build_characters(case["chars"], root)
    out = str(tmp_path / case["name"])
    run_loop(case["prompt"], chars, model, out, root, max_steps=2)  # writes out/scene.json + video + glb
    # Representative stills of the final animation (same content as preview.mp4, no ffmpeg).
    resmaps = {c["name"]: c["resmap"] for c in chars}
    stills = render(os.path.join(out, "scene.json"), resmaps,
                    os.path.join(out, "describe"), "grid", root)
    desc = describe_frames(stills, describer)
    hits = keyword_hits(desc, case["keywords"])
    missed = [k for k in case["keywords"] if k not in hits]
    assert len(hits) >= case["min_hits"], (
        f"[{case['name']}] {len(hits)}/{case['min_hits']} keywords hit.\n"
        f"hits={hits} missed={missed}\ndescription: {desc}")
```

- [ ] **Step 2: Verify default collection excludes prompting AND the module imports cleanly (no litellm/key)**

Run: `bash .superpowers/sdd/pytest.sh -q`
Expected: all pass, 1 skipped. The prompting tests are deselected (they appear as deselected, not run). Crucially, `test_prompting.py` imports without error even though litellm is absent (litellm is imported only inside functions).

- [ ] **Step 3: Verify the prompting marker selects exactly the 5 cases**

Run: `bash .superpowers/sdd/pytest.sh -m prompting --collect-only -q`
Expected: 5 items listed: `...::test_prompt_produces_expected_video[boxing]` … `[salsa]`.

- [ ] **Step 4: Verify red-not-skip when the agent is unavailable**

Run: `bash .superpowers/sdd/pytest.sh -m prompting -k boxing -q`
Expected: 1 FAILED (not skipped), failing fast with `agent unavailable: ...`. In the pytest.sh env the reason is `litellm not importable` (litellm isn't in that env); on a machine with litellm but no key it would be `no API key ...`. Either reason is a RED fail — that is the behavior being verified (red, not skip).

- [ ] **Step 5: Commit**

```bash
cd /home/theta/.vault/repos/scenharnist
git add tests/test_prompting.py
git commit -m "feat: live prompting eval test (describe grid, keyword threshold, red-not-skip)"
```

---

### Task 4: flake wiring — `waifus` input + `test-prompting` app

**Files:**
- Modify: `flake.nix`

**Interfaces:** none (packaging only).

- [ ] **Step 1: Add the `waifus` input and the `test-prompting` app to `flake.nix`**

Add the input alongside the existing `inputs`:

```nix
  inputs.waifus = { url = "github:M4jor-Tom/waifus.gltf"; flake = false; };
```

Thread it into the outputs function arguments (add `waifus`):

```nix
  outputs = { self, nixpkgs, flake-utils, waifus }:
```

Inside the per-system attrset (next to `apps.default` / `apps.test`), add:

```nix
        apps.test-prompting = {
          type = "app";
          program = toString (pkgs.writeShellScript "scenharnist-test-prompting" ''
            export PATH=${pkgs.lib.makeBinPath deps}:$PATH
            export SCENHARNIST_GLTF_ROOT=${waifus}
            cd ${self}
            exec ${py}/bin/python -m pytest -m prompting "$@"
          '');
        };
```

(`deps` and `py` are the existing let-bindings from the current flake: `py` is the python env with pytest, `deps = [ py pkgs.blender ]`. The prompting run needs `litellm` + an API key too; if litellm is not importable or no key is set, the tests fail red by design — document this in Step 3.)

- [ ] **Step 2: Verify the flake evaluates**

Run: `cd /home/theta/.vault/repos/scenharnist && nix flake lock 2>&1 | tail -5 && nix flake check --no-build 2>&1 | tail -5`
Expected: the `waifus` input locks in `flake.lock` and evaluation passes.

Note: fetching `waifus` (a large asset repo) may be heavy. If the fetch is prohibitive in this environment, instead confirm the flake expression parses with `nix flake metadata 2>&1 | tail -20` (which still resolves the input reference) and record in the report that the first real `nix run .#test-prompting` performs the DB fetch; local runs can set `SCENHARNIST_GLTF_ROOT` to skip it.

- [ ] **Step 3: Document the prompting run in `README.md`**

Add a short section to `README.md`:

````markdown
## Prompting (eval) tests

Live, opt-in tests that run a prompt end-to-end and have a vision model check the result.

```bash
# database wired via the waifus flake input; needs an API key + litellm:
export ANTHROPIC_API_KEY=...
nix run .#test-prompting            # runs all 5 cases (boxing, running, walking, burpees, salsa)
nix run .#test-prompting -- -k salsa   # one case
```

They are deselected from the normal `pytest` run and FAIL RED (not skip) if the agent, Blender, or database is unavailable. `litellm` must be importable (`pip install litellm`). Point `SCENHARNIST_GLTF_ROOT` at a local checkout to skip re-fetching the large flake input.
````

- [ ] **Step 4: Commit**

```bash
cd /home/theta/.vault/repos/scenharnist
git add flake.nix flake.lock README.md
git commit -m "chore: waifus flake input + test-prompting app + docs"
```

---

## Notes for the implementer

- The prompting tests cannot be made to PASS in this environment (no API key). Their deterministic verification is: (a) deselected from the default run, (b) `-m prompting` collects exactly 5, (c) running one fails RED with "agent unavailable". Do not try to obtain a key or make them green.
- Do NOT import `litellm` at module top-level in `tests/test_prompting.py` — default collection runs in a python env without litellm.
- `running` / `walking` / `burpees` / `salsa` depend on leg motion that is not yet calibrated; they may legitimately fail the keyword check when run live. That is an out-of-scope follow-up (leg calibration), not a harness bug — do not "fix" it here.
- Run `bash .superpowers/sdd/pytest.sh -q` after each task; the default suite must stay green (all pass, 1 Blender skip).
