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
