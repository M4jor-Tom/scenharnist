# scenharnist

Turn a prompt into an animated glTF + video. Any LiteLLM model (Claude, GPT, Gemini…)
iteratively poses characters from a `waifus.gltf`-layout database, driving only rig
rotations, root translation, and morphs — never meshes — while watching rendered previews.

## Usage

```bash
export ANTHROPIC_API_KEY=...           # or the key for your chosen provider
pip install -e . && python -m scenharnist.cli "Augusta and Baizhi are boxing" --out output/boxing
# or, for Blender + pytest on PATH via nix (litellm still comes from pip, see below):
nix develop
pip install -e .
python -m scenharnist.cli "Augusta and Baizhi are boxing" --out output/boxing
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

`flake.nix` provides a dev shell/`nix run` app with Python, `pytest`, and Blender
on PATH for the pinned nixpkgs. `python311Packages.litellm` is currently broken in
that nixpkgs pin (it transitively pulls `sphinx-9.1.0`, which is disabled for
Python 3.11), so litellm is **not** included in the flake's Python — install it
with `pip install -e .` (declared in `pyproject.toml`) or `pip install litellm`
after entering the shell.
