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
