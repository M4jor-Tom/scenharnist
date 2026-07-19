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
        "The imported REST pose is a T-pose (arms straight out). Any limb you don't pose stays a",
        "T — so pose BOTH arms (and the torso), not one bone. Between actions return limbs to a",
        "plausible pose (e.g. a guard), never to the T/rest, and END the clip in a settled pose.",
        "Fill the WHOLE duration with continuous motion (keyframes spanning 0..duration, no dead",
        "time). Real actions move the whole upper body — pair each strike with an UpperBody lean.",
        "DEFAULT IS TO MOVE. Every bone in the control surface must either appear in bone_tracks",
        "OR carry a justification in `skipped_bones: {\"BoneName\": \"why it stays static\"}`. Use",
        "`skipped_bones: {\"*\": \"reason\"}` as a catch-all when many bones share the same reason.",
        "Not justifying a bone means the spec is REJECTED — say why you left it out.",
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
        # ponytail: render_fn is injectable for tests and may return paths
        # that don't exist on disk (fakes); skip those rather than erroring.
        if not os.path.isfile(p):
            continue
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

    scene_path = os.path.join(out_dir, "scene.json")
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
        with open(scene_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
        iter_dir = os.path.join(out_dir, "iterations", f"step_{step:02d}")
        frames = render_fn(scene_path, resmaps, iter_dir, "grid", gltf_root)
        content = [{"type": "text",
                    "text": f"Rendered frames (step {step}). Fix issues or finish."}]
        content += _image_content(frames)
        messages.append({"role": "tool", "tool_call_id": call["id"],
                         "content": "rendered"})
        messages.append({"role": "user", "content": content})

    if final_spec is None:
        raise RuntimeError("model never produced a valid spec")
    render_fn(scene_path, resmaps, out_dir, "video", gltf_root)
    render_fn(scene_path, resmaps, out_dir, "glb", gltf_root)
    return final_spec
