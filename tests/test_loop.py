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
