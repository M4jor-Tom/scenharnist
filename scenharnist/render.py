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
