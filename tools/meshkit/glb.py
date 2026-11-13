"""Minimal glTF 2.0 binary writer: named nodes, one mesh per node, one primitive per material."""
import json, struct
import numpy as np

def write_glb(path, nodes):
    """nodes: list of dict(name, prims=[dict(material, pos(N,3), nrm(N,3), uv(N,2), idx(M,))])"""
    bin_chunks = []
    offset = 0
    buffer_views, accessors, meshes, gnodes = [], [], [], []
    materials, mat_index = [], {}

    def add_view(arr, target):
        nonlocal offset
        data = arr.tobytes()
        pad = (-len(data)) % 4
        bin_chunks.append(data + b"\x00" * pad)
        buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), "target": target})
        offset += len(data) + pad
        return len(buffer_views) - 1

    def add_acc(arr, typ, comp, target, minmax=False):
        v = add_view(arr, target)
        acc = {"bufferView": v, "componentType": comp, "count": int(arr.shape[0]), "type": typ}
        if minmax:
            acc["min"] = arr.min(axis=0).tolist()
            acc["max"] = arr.max(axis=0).tolist()
        accessors.append(acc)
        return len(accessors) - 1

    for n in nodes:
        prims = []
        for p in n["prims"]:
            m = p["material"]
            if m not in mat_index:
                mat_index[m] = len(materials)
                col = p.get("color", (0.8, 0.8, 0.8))
                materials.append({"name": m, "pbrMetallicRoughness": {"baseColorFactor": [col[0], col[1], col[2], 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.9}})
            pos = np.asarray(p["pos"], np.float32)
            nrm = np.asarray(p["nrm"], np.float32)
            uv = np.asarray(p["uv"], np.float32)
            idx = np.asarray(p["idx"], np.uint32)
            a_pos = add_acc(pos, "VEC3", 5126, 34962, True)
            a_nrm = add_acc(nrm, "VEC3", 5126, 34962)
            a_uv = add_acc(uv, "VEC2", 5126, 34962)
            a_idx = add_acc(idx, "SCALAR", 5125, 34963)
            prims.append({"attributes": {"POSITION": a_pos, "NORMAL": a_nrm, "TEXCOORD_0": a_uv}, "indices": a_idx, "material": mat_index[m]})
        meshes.append({"name": n["name"], "primitives": prims})
        gnodes.append({"name": n["name"], "mesh": len(meshes) - 1, "translation": list(n.get("translation", (0, 0, 0)))})
    gltf = {
        "asset": {"version": "2.0", "generator": "ffa-meshkit"},
        "scene": 0, "scenes": [{"nodes": list(range(len(gnodes)))}],
        "nodes": gnodes, "meshes": meshes, "materials": materials,
        "accessors": accessors, "bufferViews": buffer_views,
        "buffers": [{"byteLength": offset}],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    binb = b"".join(bin_chunks)
    total = 12 + 8 + len(js) + 8 + len(binb)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(binb), 0x004E4942)); f.write(binb)
