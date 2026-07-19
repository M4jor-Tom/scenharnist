import json, os, pytest
from scenharnist.render import render, blender_available
from scenharnist.rigdigest import resolution_table
from scenharnist.spec import EXAMPLE_SPEC

GLTF_ROOT = os.path.expanduser("~/.vault/repos/waifus.gltf")
HAVE = blender_available() and os.path.exists(GLTF_ROOT)

@pytest.mark.skipif(not HAVE, reason="blender or waifus.gltf missing")
def test_grid_render_produces_frames(tmp_path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(EXAMPLE_SPEC))
    resmaps = {c["name"]: resolution_table(os.path.join(GLTF_ROOT, c["gltf"]))
               for c in EXAMPLE_SPEC["characters"]}
    out = render(str(spec_path), resmaps, str(tmp_path / "out"), "grid", GLTF_ROOT)
    assert out and all(os.path.exists(p) for p in out)
