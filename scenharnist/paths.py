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
