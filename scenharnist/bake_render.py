"""Runs inside Blender: blender -b -P bake_render.py -- spec resmaps out mode gltf_root."""
import bpy, json, math, os, sys

argv = sys.argv[sys.argv.index("--") + 1:]
SPEC_PATH, RESMAPS_PATH, OUT_DIR, MODE, GLTF_ROOT = argv[:5]

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

spec = load(SPEC_PATH)
resmaps = load(RESMAPS_PATH)
fps = int(spec["fps"])
dur = float(spec["duration"])

# Fresh scene.
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = fps
scene.frame_start = 1
scene.frame_end = max(2, int(round(dur * fps)))

def t_to_frame(t):
    return 1 + int(round(float(t) * fps))

def import_char(c):
    path = os.path.join(GLTF_ROOT, c["gltf"]) if not os.path.isabs(c["gltf"]) else c["gltf"]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next((o for o in new if o.type == "ARMATURE"), None)
    meshes = [o for o in new if o.type == "MESH"]
    # Root placement on the armature (or first new object).
    root = c.get("root", {})
    tx = root.get("translation", [0, 0, 0])
    holder = arm or (new[0] if new else None)
    if holder:
        holder.location = (tx[0], tx[1], tx[2])
        holder.rotation_mode = "XYZ"
        holder.rotation_euler = (0, 0, math.radians(root.get("yaw_deg", 0)))
    return arm, meshes

for c in spec["characters"]:
    rt = resmaps.get(c["name"], {"bones": {}, "morphs": {}})
    arm, meshes = import_char(c)
    # Bone tracks.
    if arm:
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="POSE")
        for en_bone, frames in (c.get("bone_tracks") or {}).items():
            cjk = rt["bones"].get(en_bone)
            pb = arm.pose.bones.get(cjk) if cjk else None
            if not pb:
                continue
            pb.rotation_mode = "XYZ"
            for fr in frames:
                e = fr["euler_deg"]
                pb.rotation_euler = (math.radians(e[0]), math.radians(e[1]), math.radians(e[2]))
                pb.keyframe_insert("rotation_euler", frame=t_to_frame(fr["t"]))
        bpy.ops.object.mode_set(mode="OBJECT")
    # Morph tracks.
    for en_morph, frames in (c.get("morph_tracks") or {}).items():
        cjk = rt["morphs"].get(en_morph)
        for m in meshes:
            sk = m.data.shape_keys
            kb = sk.key_blocks.get(cjk) if (sk and cjk) else None
            if not kb:
                continue
            for fr in frames:
                kb.value = float(fr["weight"])
                kb.keyframe_insert("value", frame=t_to_frame(fr["t"]))

# Camera + light.
cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
target = bpy.data.objects.new("CamTarget", None)
scene.collection.objects.link(target)
con = cam.constraints.new("TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
for fr in spec.get("camera", [{"t": 0, "position": [0, 1.2, 3], "look_at": [0, 1, 0]}]):
    f = t_to_frame(fr["t"])
    cam.location = tuple(fr["position"]); cam.keyframe_insert("location", frame=f)
    target.location = tuple(fr["look_at"]); target.keyframe_insert("location", frame=f)
light_data = bpy.data.lights.new("Sun", type="SUN"); light_data.energy = 3.0
light = bpy.data.objects.new("Sun", light_data); light.location = (2, -2, 4)
scene.collection.objects.link(light)
scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in \
    {i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"

produced = []
def render_still(frame, path):
    scene.frame_set(frame)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    produced.append(path)

if MODE == "grid":
    times = sorted({fr["t"] for c in spec["characters"]
                    for tr in list((c.get("bone_tracks") or {}).values())
                             + list((c.get("morph_tracks") or {}).values())
                    for fr in tr} | {0.0, dur})
    times = times[:9] if len(times) > 9 else times
    for i, t in enumerate(times):
        render_still(t_to_frame(t), os.path.join(OUT_DIR, f"frame_{i:02d}_t{t:.2f}.png"))
elif MODE == "video":
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    out = os.path.join(OUT_DIR, "preview.mp4")
    scene.render.filepath = out
    bpy.ops.render.render(animation=True)
    produced.append(out)
elif MODE == "glb":
    out = os.path.join(OUT_DIR, "scene.glb")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_animations=True)
    produced.append(out)

with open(os.path.join(OUT_DIR, f"_manifest_{MODE}.json"), "w", encoding="utf-8") as f:
    json.dump(produced, f)
