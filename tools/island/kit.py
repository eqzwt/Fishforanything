"""Procedural mesh kit for Fish For Anything's island map.
Authoring space == Roblox space (studs, Y up, fronts face -Z). The GLB writer converts to glTF.
Every (prop, material) pair becomes its own node "<Prop>__<Mat>" so Studio knows which texture to use.
UVs are world-projected (1 texture repeat = TILE studs) so tileable textures line up across props."""
import math
import numpy as np
from glb import write_glb

rng = np.random.default_rng(7)
TILE = {"Plank": 6.0, "Beam": 5.0, "Roof": 6.0, "RoofDark": 6.0, "Stone": 6.0, "Plaster": 8.0, "Bark": 4.0, "Frond": 8.0,
        "Leaf": 10.0, "Rock": 14.0, "Fabric": 5.0, "Rope": 2.0, "Iron": 4.0, "Glow": 4.0, "Coral": 6.0, "Kelp": 10.0, "Sail": 8.0}


def norm(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-9)


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


class Prop:
    def __init__(self, name):
        self.name = name
        self.geo = {}  # mat -> [pos list, nrm list, uv list, idx list]

    def _g(self, mat):
        if mat not in self.geo:
            self.geo[mat] = [[], [], [], []]
        return self.geo[mat]

    def tri_soup(self, mat, tris, smooth_normals=None, uvmode="world", uvs=None):
        """tris: (T,3,3) array. Flat shaded unless smooth_normals (T,3,3) given."""
        g = self._g(mat)
        tris = np.asarray(tris, float)
        if smooth_normals is None:
            fn = norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]))
            nrm = np.repeat(fn[:, None, :], 3, axis=1)
        else:
            nrm = np.asarray(smooth_normals, float)
        if uvs is None:
            uv = world_uv(tris.reshape(-1, 3), nrm.reshape(-1, 3), TILE.get(mat, 6.0)).reshape(-1, 3, 2)
        else:
            uv = np.asarray(uvs, float)
        base = sum(len(p) for p in g[0])
        g[0].append(tris.reshape(-1, 3))
        g[1].append(nrm.reshape(-1, 3))
        g[2].append(uv.reshape(-1, 2))
        g[3].append(np.arange(base, base + tris.shape[0] * 3))

    def tris(self):
        return sum(len(np.concatenate(g[3])) // 3 for g in self.geo.values())

    def nodes(self, offset=(0, 0, 0)):
        out = []
        for mat, g in self.geo.items():
            pos = np.concatenate(g[0]) + np.array(offset)
            nrm = np.concatenate(g[1])
            uv = np.concatenate(g[2])
            idx = np.concatenate(g[3])
            # Roblox imports glTF turned 180 deg about Y: pre-turn so authored coords survive
            pos = pos * np.array([-1, 1, -1])
            nrm = nrm * np.array([-1, 1, -1])
            out.append(dict(name=f"{self.name}__{mat}", prims=[dict(material=mat, pos=pos, nrm=nrm, uv=uv, idx=idx)]))
        return out


def world_uv(p, n, tile):
    """tri-planar style projection on the dominant normal axis"""
    a = np.abs(n)
    uv = np.zeros((len(p), 2))
    mx = (a[:, 0] >= a[:, 1]) & (a[:, 0] >= a[:, 2])
    my = (a[:, 1] > a[:, 0]) & (a[:, 1] >= a[:, 2])
    mz = ~(mx | my)
    uv[mx] = np.stack([p[mx, 2], p[mx, 1]], 1)
    uv[my] = np.stack([p[my, 0], p[my, 2]], 1)
    uv[mz] = np.stack([p[mz, 0], p[mz, 1]], 1)
    return uv / tile


# ------------------------------------------------------------------ primitives (all return triangle arrays)
def box_tris(center, size, R=None):
    c = np.asarray(center, float)
    s = np.asarray(size, float) / 2
    R = np.eye(3) if R is None else R
    corners = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float) * s
    corners = corners @ R.T + c
    # index helper (x,y,z bits)
    def C(x, y, z): return corners[x * 4 + y * 2 + z]
    quads = [
        (C(1, 0, 0), C(1, 1, 0), C(1, 1, 1), C(1, 0, 1)),  # +x
        (C(0, 0, 1), C(0, 1, 1), C(0, 1, 0), C(0, 0, 0)),  # -x
        (C(0, 1, 0), C(0, 1, 1), C(1, 1, 1), C(1, 1, 0)),  # +y
        (C(0, 0, 0), C(1, 0, 0), C(1, 0, 1), C(0, 0, 1)),  # -y
        (C(0, 0, 1), C(1, 0, 1), C(1, 1, 1), C(0, 1, 1)),  # +z
        (C(1, 0, 0), C(0, 0, 0), C(0, 1, 0), C(1, 1, 0)),  # -z
    ]
    t = []
    for a, b, cc, d in quads:
        t += [[a, b, cc], [a, cc, d]]
    return np.array(t)


def fix_winding(tris, center):
    """make every triangle face away from `center` (for convex-ish closed shapes)"""
    tris = np.array(tris, float)
    fn = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    cen = tris.mean(1)
    flip = np.einsum("ij,ij->i", fn, cen - np.asarray(center)) < 0
    tris[flip] = tris[flip][:, ::-1]
    return tris


def frame_along(p0, p1):
    d = norm(np.asarray(p1, float) - np.asarray(p0, float))
    up = np.array([0, 1, 0]) if abs(d[1]) < 0.95 else np.array([1, 0, 0])
    x = norm(np.cross(up, d))
    y = np.cross(d, x)
    return x, y, d


def tube(path, radii, seg=10, cap=True, jitter=0.0, flat=False):
    """swept circle along a polyline. Returns (tris, normals, uvs) for smooth shading."""
    path = np.asarray(path, float)
    n = len(path)
    radii = np.broadcast_to(np.asarray(radii, float), (n,))
    # parallel transport frames
    tangents = np.zeros((n, 3))
    for i in range(n):
        a = path[max(i - 1, 0)]
        b = path[min(i + 1, n - 1)]
        tangents[i] = norm(b - a)
    x, y, _ = frame_along(path[0], path[1])
    rings, rnorm = [], []
    for i in range(n):
        t = tangents[i]
        x = norm(x - np.dot(x, t) * t)
        y = np.cross(t, x)
        ring, rn = [], []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            dirv = math.cos(a) * x + math.sin(a) * y
            r = radii[i] * (1 + (rng.uniform(-jitter, jitter) if jitter else 0))
            ring.append(path[i] + dirv * r)
            rn.append(dirv)
        rings.append(ring)
        rnorm.append(rn)
    rings = np.array(rings)
    rnorm = np.array(rnorm)
    length = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    T, N, U = [], [], []
    for i in range(n - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            a, b, c, d = rings[i, k], rings[i, k2], rings[i + 1, k2], rings[i + 1, k]
            na, nb, nc, nd = rnorm[i, k], rnorm[i, k2], rnorm[i + 1, k2], rnorm[i + 1, k]
            ua, ub = k / seg, (k + 1) / seg
            va, vb = length[i], length[i + 1]
            T += [[a, c, b], [a, d, c]]
            N += [[na, nc, nb], [na, nd, nc]]
            U += [[(ua, va), (ub, vb), (ub, va)], [(ua, va), (ua, vb), (ub, vb)]]
    if cap:
        for i, sgn in ((0, -1), (n - 1, 1)):
            c = path[i]
            tn = tangents[i] * sgn
            for k in range(seg):
                k2 = (k + 1) % seg
                a, b = rings[i, k], rings[i, k2]
                tri = [c, a, b] if sgn > 0 else [c, b, a]
                T.append(tri)
                N.append([tn, tn, tn])
                U.append([(0.5, 0.5), (0.5 + 0.5 * math.cos(2 * math.pi * k / seg), 0.5), (0.5, 0.5)])
    T, N, U = np.array(T), np.array(N), np.array(U)
    if flat:
        N = None
    return T, N, U


def add_tube(prop, mat, path, radii, seg=10, cap=True, jitter=0.0, flat=False, uv_around=1.0, uv_len=None):
    T, N, U = tube(path, radii, seg, cap, jitter, flat)
    tile = TILE.get(mat, 6.0)
    U = U.copy()
    U[..., 0] *= uv_around
    U[..., 1] /= (uv_len or tile)
    prop.tri_soup(mat, T, N, uvs=U)


def icosphere(sub=2):
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    verts = [np.array(x, float) / np.linalg.norm(x) for x in v]
    for _ in range(sub):
        cache, nf = {}, []
        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                m = verts[a] + verts[b]
                verts.append(m / np.linalg.norm(m))
                cache[k] = len(verts) - 1
            return cache[k]
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    return np.array(verts), np.array(f)


def blob(center, radii, sub=2, rough=0.25, seed=0, squash_bottom=False):
    """displaced faceted sphere (rocks, foliage clumps)"""
    v, f = icosphere(sub)
    r = np.random.default_rng(abs(int(seed)))
    # low-frequency displacement from a few random directional waves
    disp = np.ones(len(v))
    for _ in range(6):
        d = norm(r.normal(size=3))
        disp += rough * 0.5 * np.sin(v @ d * r.uniform(2, 4.5) + r.uniform(0, 6.28))
    disp += r.uniform(-rough * 0.35, rough * 0.35, len(v))
    p = v * disp[:, None] * np.asarray(radii, float)
    if squash_bottom:
        p[:, 1] = np.where(p[:, 1] < 0, p[:, 1] * 0.25, p[:, 1])
    p = p + np.asarray(center, float)
    return p[f]


def quad(a, b, c, d):
    return [[a, b, c], [a, c, d]]


def double(tris):
    tris = np.asarray(tris, float)
    return np.concatenate([tris, tris[:, ::-1]])


# ------------------------------------------------------------------ reusable pieces
def planks_floor(prop, x0, x1, z0, z1, y, plank=1.0, gap=0.12, thick=0.35, along="z", mat="Plank", jitter=0.06, seed=1):
    r = np.random.default_rng(seed)
    if along == "z":
        x = x0
        while x < x1 - 0.05:
            w = min(plank, x1 - x)
            dy = r.uniform(-jitter, jitter)
            prop.tri_soup(mat, box_tris(((x + x + w - gap) / 2, y - thick / 2 + dy, (z0 + z1) / 2), (w - gap, thick, z1 - z0)))
            x += w
    else:
        z = z0
        while z < z1 - 0.05:
            w = min(plank, z1 - z)
            dy = r.uniform(-jitter, jitter)
            prop.tri_soup(mat, box_tris(((x0 + x1) / 2, y - thick / 2 + dy, (z + z + w - gap) / 2), (x1 - x0, thick, w - gap)))
            z += w


def wall_planks(prop, p0, p1, y0, y1, thick=0.5, plank=1.1, mat="Plank", seed=2):
    """horizontal clapboard wall from p0 to p1 (x,z), planks slightly overlapping outward"""
    r = np.random.default_rng(seed)
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L = np.linalg.norm(p1 - p0)
    ang = math.atan2(p1[0] - p0[0], p1[1] - p0[1])
    R = rot_y(ang)
    mid = (p0 + p1) / 2
    y = y0
    i = 0
    while y < y1 - 0.05:
        h = min(plank, y1 - y)
        out = (i % 2) * 0.06 + r.uniform(0, 0.04)
        local = np.array([out, 0, 0]) @ R.T
        prop.tri_soup(mat, box_tris((mid[0] + local[0], y + h / 2, mid[1] + local[2]), (thick, h - 0.04, L), R))
        y += h
        i += 1


def post(prop, x, z, y0, y1, r=0.45, mat="Beam", seg=8):
    add_tube(prop, mat, [(x, y0, z), (x, y1, z)], [r, r * 0.92], seg=seg, uv_around=1.0)


def gable_roof(prop, cx, cz, w, d, y_eave, h, over=1.2, mat="Roof", thick=0.5, ridge=True, rot=0.0):
    """two sloped slabs, ridge along X (width w along X, depth d along Z)"""
    R = rot_y(rot)
    half = d / 2 + over
    slope_len = math.hypot(half, h)
    ang = math.atan2(h, half)
    for s in (-1, 1):
        # slab centre
        c = np.array([0, y_eave + h / 2, s * half / 2])
        Rs = rot_x(s * ang)
        tris = box_tris((0, 0, 0), (w + 2 * over, thick, slope_len), Rs) + c
        # tile rows: small ledges every 1.5 studs down the slope
        prop.tri_soup(mat, (tris - [0, 0, 0]) @ R.T + [cx, 0, cz])
        n_rows = int(slope_len / 1.5)
        for k in range(1, n_rows):
            t = k / n_rows
            pz = s * half * t
            py = y_eave + h - h * t + thick * 0.55
            rt = box_tris((0, 0, 0), (w + 2 * over, 0.22, 0.35), Rs) + [0, py, pz]
            prop.tri_soup(mat, rt @ R.T + [cx, 0, cz])
    if ridge:
        add_tube_local = [(-w / 2 - over, y_eave + h + 0.15, 0), (w / 2 + over, y_eave + h + 0.15, 0)]
        pts = np.array(add_tube_local) @ R.T + [cx, 0, cz]
        add_tube(prop, mat, pts, 0.55, seg=6)


def gable_wall(prop, cx, cz, w, y_eave, h, z_face, mat="Plank", rot=0.0):
    """triangular gable infill at z = z_face (local), width w along X"""
    R = rot_y(rot)
    a = np.array([-w / 2, y_eave, z_face])
    b = np.array([w / 2, y_eave, z_face])
    c = np.array([0, y_eave + h, z_face])
    tris = double([[a, b, c]])
    prop.tri_soup(mat, tris @ R.T + [cx, 0, cz])


def window(prop, cx, y, cz, w, h, facing, frame_mat="Beam"):
    """glowing window pane with a wooden frame + cross bars. facing: unit (x,z) outward"""
    fx, fz = facing
    ang = math.atan2(fx, fz)
    R = rot_y(ang)
    c = np.array([cx, y, cz])
    prop.tri_soup("Glow", box_tris(c, (w, h, 0.2), R))
    t = 0.28
    for dx, dy, sx, sy in ((0, h / 2, w + t, t), (0, -h / 2, w + t, t), (w / 2, 0, t, h), (-w / 2, 0, t, h), (0, 0, w, 0.14), (0, 0, 0.14, h)):
        off = np.array([dx, dy, 0.12]) @ R.T
        prop.tri_soup(frame_mat, box_tris(c + off, (sx, sy, 0.3), R))
    # sill
    off = np.array([0, -h / 2 - 0.25, 0.3]) @ R.T
    prop.tri_soup(frame_mat, box_tris(c + off, (w + 0.8, 0.25, 0.7), R))


def door(prop, cx, cz, w, h, facing, y0=0.0):
    fx, fz = facing
    R = rot_y(math.atan2(fx, fz))
    c = np.array([cx, y0 + h / 2, cz])
    prop.tri_soup("Beam", box_tris(c, (w, h, 0.3), R))
    for dx in (-w / 4, 0, w / 4):
        off = np.array([dx, 0, 0.16]) @ R.T
        prop.tri_soup("Plank", box_tris(c + off, (w / 4 - 0.12, h - 0.3, 0.12), R))
    off = np.array([w * 0.32, -0.1, 0.3]) @ R.T
    prop.tri_soup("Iron", box_tris(c + off, (0.25, 0.25, 0.3), R))
    for dy in (h / 2 + 0.2,):
        off = np.array([0, dy, 0.1]) @ R.T
        prop.tri_soup("Beam", box_tris(c + off, (w + 0.8, 0.4, 0.5), R))


# ------------------------------------------------------------------ buildings
def cabin():
    p = Prop("Cabin")
    W, D = 18.0, 13.0
    # stone foundation (slightly irregular blocks)
    p.tri_soup("Stone", box_tris((0, 0.9, 0), (W + 1.2, 1.8, D + 1.2)))
    for i in range(14):
        x = -W / 2 - 0.6 + (i + 0.5) * (W + 1.2) / 14
        p.tri_soup("Stone", box_tris((x, 0.9, -D / 2 - 0.75), ((W + 1.2) / 14 - 0.15, 1.6, 0.4)))
    # walls
    y0, y1 = 1.8, 10.0
    wall_planks(p, (-W / 2, -D / 2), (W / 2, -D / 2), y0, y1)
    wall_planks(p, (W / 2, D / 2), (-W / 2, D / 2), y0, y1, seed=3)
    wall_planks(p, (-W / 2, D / 2), (-W / 2, -D / 2), y0, y1, seed=4)
    wall_planks(p, (W / 2, -D / 2), (W / 2, D / 2), y0, y1, seed=5)
    for x, z in ((-W / 2, -D / 2), (W / 2, -D / 2), (-W / 2, D / 2), (W / 2, D / 2)):
        post(p, x, z, y0, y1 + 0.3, 0.55)
    # beam under the eaves
    for z in (-D / 2, D / 2):
        p.tri_soup("Beam", box_tris((0, y1, z), (W + 1, 0.6, 0.7)))
    # roof (ridge along X), gables on +-X
    gable_roof(p, 0, 0, W, D, y1 + 0.2, 6.5, over=1.4)
    for sx in (-1, 1):
        R = rot_y(math.pi / 2)
        a = np.array([sx * W / 2, y1 + 0.2, -D / 2 - 0.3])
        b = np.array([sx * W / 2, y1 + 0.2, D / 2 + 0.3])
        c = np.array([sx * W / 2, y1 + 6.6, 0])
        p.tri_soup("Plank", double([[a, b, c]]))
    # front: door + windows facing -Z
    door(p, 0, -D / 2 - 0.3, 3.2, 6.2, (0, -1), y0)
    window(p, -5.5, 6.2, -D / 2 - 0.35, 2.6, 2.4, (0, -1))
    window(p, 5.5, 6.2, -D / 2 - 0.35, 2.6, 2.4, (0, -1))
    window(p, W / 2 + 0.35, 6.2, 0, 2.6, 2.4, (1, 0))
    window(p, -W / 2 - 0.35, 6.2, 0, 2.6, 2.4, (-1, 0))
    window(p, 0, 13.0, W / 2 + 0.2 - 9 + 9, 0.01, 0.01, (1, 0)) if False else None
    # porch deck + steps + little porch roof posts
    planks_floor(p, -6.5, 6.5, -D / 2 - 4.2, -D / 2 - 0.6, 1.9, along="x", plank=0.9, seed=8)
    for x in (-6, 6):
        post(p, x, -D / 2 - 3.8, 0, 1.6, 0.4)
    for k, (dz, dy) in enumerate(((-5.0, 1.15), (-5.8, 0.45))):
        p.tri_soup("Plank", box_tris((0, dy, -D / 2 + dz), (4.2, 0.35, 0.8)))
    # chimney
    p.tri_soup("Stone", box_tris((W / 2 - 3.5, y1 + 6.0, 2.5), (2.2, 8.5, 2.2)))
    p.tri_soup("Stone", box_tris((W / 2 - 3.5, y1 + 10.4, 2.5), (2.7, 0.5, 2.7)))
    # flower box + barrel by the door
    p.tri_soup("Plank", box_tris((-5.5, 4.6, -D / 2 - 0.9), (3.0, 0.7, 0.8)))
    barrel(p, (3.3, 1.9, -D / 2 - 2.0), 0.9, 2.2)
    return p


def townhouse():
    p = Prop("Townhouse")
    W, D = 15.0, 12.0
    # stone ground floor
    p.tri_soup("Stone", box_tris((0, 4.2, 0), (W, 8.4, D)))
    p.tri_soup("Stone", box_tris((0, 0.4, 0), (W + 1.0, 0.8, D + 1.0)))
    # plaster upper floor, overhanging slightly, with timber frame
    y0, y1 = 8.4, 16.0
    p.tri_soup("Plaster", box_tris((0, (y0 + y1) / 2, 0), (W + 0.8, y1 - y0, D + 0.8)))
    hw, hd = (W + 0.8) / 2 + 0.12, (D + 0.8) / 2 + 0.12
    for x in np.linspace(-hw + 0.3, hw - 0.3, 5):
        for z in (-hd, hd):
            p.tri_soup("Beam", box_tris((x, (y0 + y1) / 2, z), (0.5, y1 - y0, 0.3)))
    for z in np.linspace(-hd + 0.3, hd - 0.3, 4):
        for x in (-hw, hw):
            p.tri_soup("Beam", box_tris((x, (y0 + y1) / 2, z), (0.3, y1 - y0, 0.5)))
    for y in (y0 + 0.25, y1 - 0.25):
        p.tri_soup("Beam", box_tris((0, y, -hd), (W + 1.2, 0.5, 0.35)))
        p.tri_soup("Beam", box_tris((0, y, hd), (W + 1.2, 0.5, 0.35)))
        p.tri_soup("Beam", box_tris((-hw, y, 0), (0.35, 0.5, D + 1.2)))
        p.tri_soup("Beam", box_tris((hw, y, 0), (0.35, 0.5, D + 1.2)))
    # roof: ridge along Z this time (gables face front/back)
    gable_roof(p, 0, 0, D + 0.8, W + 0.8, y1, 6.5, over=1.3, rot=math.pi / 2)
    for sz in (-1, 1):
        a = np.array([-(W + 0.8) / 2, y1, sz * (D + 0.8) / 2])
        b = np.array([(W + 0.8) / 2, y1, sz * (D + 0.8) / 2])
        c = np.array([0, y1 + 6.5, sz * (D + 0.8) / 2])
        p.tri_soup("Plaster", double([[a, b, c]]))
        window(p, 0, y1 + 2.2, sz * ((D + 0.8) / 2 + 0.2), 1.8, 1.8, (0, sz))
    # windows
    for x in (-4.2, 4.2):
        window(p, x, 12.2, -hd - 0.15, 2.2, 2.6, (0, -1))
        window(p, x, 12.2, hd + 0.15, 2.2, 2.6, (0, 1))
    window(p, -4.0, 4.8, -D / 2 - 0.2, 2.4, 2.2, (0, -1))
    for z in (-2.5, 2.5):
        window(p, W / 2 + 0.2, 4.8, z, 2.0, 2.0, (1, 0))
        window(p, -hw - 0.15, 12.2, z, 2.0, 2.4, (-1, 0))
    door(p, 3.5, -D / 2 - 0.25, 3.0, 6.0, (0, -1), 0.8)
    # balcony on the front of the upper floor
    planks_floor(p, -6.5, 1.0, -hd - 3.0, -hd, y0 + 0.2, along="x", plank=0.8, seed=11)
    for x in np.linspace(-6.3, 0.8, 7):
        post(p, x, -hd - 2.8, y0 + 0.2, y0 + 3.2, 0.16, mat="Beam", seg=6)
    p.tri_soup("Beam", box_tris((-2.75, y0 + 3.2, -hd - 2.8), (7.6, 0.35, 0.35)))
    for x in (-6.3, 0.8):
        p.tri_soup("Beam", box_tris((x, y0 - 1.0, -hd - 1.5), (0.4, 0.4, 3.0), rot_x(-0.5)))
    # chimney
    p.tri_soup("Stone", box_tris((-4.5, y1 + 6.0, 3.0), (2.0, 7.0, 2.0)))
    return p


def shop_stall():
    """Old Gill's bait & tackle stall. Counter faces -Z."""
    p = Prop("ShopStall")
    W, D = 14.0, 8.0
    planks_floor(p, -W / 2, W / 2, -D / 2, D / 2, 0.5, along="x", plank=1.0, seed=21)
    for x, z in ((-W / 2, -D / 2), (W / 2, -D / 2), (-W / 2, D / 2), (W / 2, D / 2)):
        post(p, x + (0.3 if x < 0 else -0.3), z + (0.3 if z < 0 else -0.3), 0, 9.5 if z > 0 else 8.2, 0.42)
    # counter with plank front
    p.tri_soup("Plank", box_tris((0, 2.0, -D / 2 + 1.2), (W - 1.5, 3.0, 1.0)))
    p.tri_soup("Beam", box_tris((0, 3.6, -D / 2 + 1.1), (W - 1.0, 0.35, 1.6)))
    # back wall + shelves
    wall_planks(p, (W / 2 - 0.3, D / 2 - 0.3), (-W / 2 + 0.3, D / 2 - 0.3), 0.5, 7.5, seed=22)
    for y in (3.2, 5.6):
        p.tri_soup("Beam", box_tris((0, y, D / 2 - 1.0), (W - 2, 0.3, 1.2)))
    for i, x in enumerate(np.linspace(-5, 5, 6)):
        crate(p, (x, 3.35, D / 2 - 1.0), 0.9, seed=i)
    for x in (-4.5, 4.5):
        barrel(p, (x, 0.5, D / 2 - 2.4), 1.0, 2.4)
    # striped fabric awning sloping toward the front
    for k in range(7):
        x0 = -W / 2 - 0.6 + k * (W + 1.2) / 7
        mat = "Fabric"
        R = rot_x(0.32)
        t = box_tris((x0 + (W + 1.2) / 14, 0, 0), ((W + 1.2) / 7, 0.18, D + 2.5), R) + [0, 8.85, -0.6]
        p.tri_soup(mat, t)
    # scalloped valance at the front edge
    for k in range(14):
        x = -W / 2 - 0.3 + (k + 0.5) * (W + 0.6) / 14
        p.tri_soup("Fabric", double([[(x - 0.5, 7.25, -D / 2 - 1.85), (x + 0.5, 7.25, -D / 2 - 1.85), (x, 6.55, -D / 2 - 1.85)]]))
    # sign board on top
    p.tri_soup("Beam", box_tris((0, 10.8, D / 2 - 0.3), (8.0, 2.2, 0.4)))
    p.tri_soup("Plank", box_tris((0, 10.8, D / 2 - 0.55), (7.2, 1.6, 0.2)))
    # fish hanging from the awning beam + rods leaning
    for x in (-5.2, -4.2, 4.6):
        add_tube(p, "Iron", [(x, 7.6, -D / 2 + 0.2), (x, 6.2, -D / 2 + 0.2)], 0.04, seg=4)
        p.tri_soup("Iron", blob((x, 5.6, -D / 2 + 0.2), (0.25, 0.6, 0.12), 1, 0.1, seed=int(x * 10)))
    for i, x in enumerate((-6.2, -5.7)):
        add_tube(p, "Beam", [(x, 0.6, D / 2 - 0.8), (x + 0.6, 8.5, D / 2 - 1.6)], [0.09, 0.05], seg=5)
    return p


def boathouse():
    p = Prop("Boathouse")
    W, D = 16.0, 20.0
    deck_y = 0.0
    # stilts down into the water (y < 0)
    for x in (-W / 2, 0, W / 2):
        for z in np.linspace(-D / 2, D / 2, 4):
            post(p, x, z, -14, deck_y + 0.2, 0.5)
    planks_floor(p, -W / 2 - 0.5, -2.5, -D / 2, D / 2, deck_y + 0.6, along="z", plank=1.0, seed=31)
    planks_floor(p, 2.5, W / 2 + 0.5, -D / 2, D / 2, deck_y + 0.6, along="z", plank=1.0, seed=32)
    planks_floor(p, -W / 2 - 0.5, W / 2 + 0.5, D / 2 - 3, D / 2, deck_y + 0.6, along="x", plank=1.0, seed=33)
    # three walls, open toward -Z (water side)
    wall_planks(p, (-W / 2, D / 2), (-W / 2, -D / 2), deck_y + 0.6, 9.5, mat="RoofDark", seed=34)
    wall_planks(p, (W / 2, -D / 2), (W / 2, D / 2), deck_y + 0.6, 9.5, mat="RoofDark", seed=35)
    wall_planks(p, (W / 2, D / 2), (-W / 2, D / 2), deck_y + 0.6, 9.5, mat="RoofDark", seed=36)
    for x in (-W / 2, W / 2):
        for z in (-D / 2, D / 2):
            post(p, x, z, deck_y, 9.8, 0.5)
    p.tri_soup("Beam", box_tris((0, 9.5, -D / 2), (W + 1, 0.8, 0.7)))
    gable_roof(p, 0, 0, D, W, 9.9, 5.5, over=1.2, mat="RoofDark", rot=math.pi / 2)
    a, b, c = np.array([-W / 2, 9.9, -D / 2]), np.array([W / 2, 9.9, -D / 2]), np.array([0, 15.4, -D / 2])
    p.tri_soup("Plank", double([[a, b, c]]))
    window(p, W / 2 + 0.3, 5.5, 3, 2.2, 2.0, (1, 0))
    window(p, -W / 2 - 0.3, 5.5, 3, 2.2, 2.0, (-1, 0))
    # coiled rope + buoys
    add_tube(p, "Rope", [(5.5 + 1.2 * math.cos(a), 0.9, 7 + 1.2 * math.sin(a)) for a in np.linspace(0, 12, 50)], 0.18, seg=5)
    for z in (-6, -2):
        p.tri_soup("Fabric", blob((W / 2 + 0.6, 4.0, z), (0.6, 0.8, 0.6), 1, 0.05, seed=z + 50))
    return p


# ------------------------------------------------------------------ small props
def crate(p, base, s=1.0, seed=0):
    x, y, z = base
    p.tri_soup("Plank", box_tris((x, y + s, z), (2 * s, 2 * s, 2 * s), rot_y(seed * 0.4)))
    R = rot_y(seed * 0.4)
    for dy in (0.15, 1.85):
        for dz in (-1, 1):
            off = np.array([0, (dy - 1) * s, dz * (s + 0.02)]) @ R.T
            p.tri_soup("Beam", box_tris(np.array([x, y + s, z]) + off, (2.05 * s, 0.3 * s, 0.1), R))


def barrel(p, base, r=1.0, h=2.4):
    x, y, z = base
    pts = [(x, y + h * t, z) for t in np.linspace(0, 1, 7)]
    radii = [r * (0.86 + 0.14 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 7)]
    add_tube(p, "Plank", pts, radii, seg=12, uv_around=3)
    for t in (0.18, 0.82):
        rr = r * (0.86 + 0.14 * math.sin(math.pi * t)) + 0.05
        add_tube(p, "Iron", [(x, y + h * t - 0.12, z), (x, y + h * t + 0.12, z)], rr, seg=12, cap=False)


def props_small():
    out = []
    p = Prop("Crate"); crate(p, (0, 0, 0), 1.2); out.append(p)
    p = Prop("Barrel"); barrel(p, (0, 0, 0), 1.1, 2.8); out.append(p)
    # crate stack
    p = Prop("CrateStack")
    crate(p, (0, 0, 0), 1.2, 0); crate(p, (2.6, 0, 0.3), 1.1, 1); crate(p, (1.2, 2.4, 0.1), 1.1, 2); barrel(p, (-2.4, 0, 0.6), 1.0, 2.5)
    out.append(p)
    return out


def lantern_post():
    p = Prop("LanternPost")
    add_tube(p, "Beam", [(0, 0, 0), (0, 9.5, 0)], [0.42, 0.34], seg=8)
    p.tri_soup("Beam", box_tris((0.9, 9.1, 0), (2.4, 0.35, 0.35)))
    p.tri_soup("Beam", box_tris((0.5, 8.5, 0), (0.25, 1.2, 0.25), rot_z(0.6)))
    lantern(p, (1.8, 7.5, 0))
    return p


def lantern(p, c, s=1.0):
    x, y, z = c
    add_tube(p, "Iron", [(x, y + 1.6 * s, z), (x, y + 1.05 * s, z)], 0.05 * s, seg=4)
    p.tri_soup("Glow", box_tris((x, y + 0.2 * s, z), (0.75 * s, 1.0 * s, 0.75 * s)))
    for dx in (-1, 1):
        for dz in (-1, 1):
            p.tri_soup("Iron", box_tris((x + dx * 0.4 * s, y + 0.2 * s, z + dz * 0.4 * s), (0.12 * s, 1.1 * s, 0.12 * s)))
    p.tri_soup("Iron", box_tris((x, y - 0.38 * s, z), (1.0 * s, 0.18 * s, 1.0 * s)))
    cap = np.array([[x - 0.55 * s, y + 0.75 * s, z - 0.55 * s], [x + 0.55 * s, y + 0.75 * s, z - 0.55 * s], [x + 0.55 * s, y + 0.75 * s, z + 0.55 * s], [x - 0.55 * s, y + 0.75 * s, z + 0.55 * s]])
    top = np.array([x, y + 1.15 * s, z])
    tris = [[cap[i], top, cap[(i + 1) % 4]] for i in range(4)]
    p.tri_soup("Iron", fix_winding(tris, (x, y + 0.75 * s, z)))


def hanging_lantern():
    p = Prop("HangingLantern")
    lantern(p, (0, 0, 0), 1.0)
    return p


def pier(length=24.0, width=8.0):
    """pier section: deck top at y=0, runs along Z from 0 to -length; posts sink to y=-16"""
    p = Prop("Pier")
    planks_floor(p, -width / 2, width / 2, -length, 0, 0.0, along="x", plank=0.95, gap=0.14, thick=0.4, seed=41, jitter=0.05)
    for x in (-width / 2 + 0.6, width / 2 - 0.6):
        p.tri_soup("Beam", box_tris((x, -0.65, -length / 2), (0.6, 0.6, length)))
    for z in np.arange(-2, -length - 0.1, -6):
        for x in (-width / 2 - 0.1, width / 2 + 0.1):
            add_tube(p, "Beam", [(x, -16, z), (x, 1.6, z)], [0.55, 0.5], seg=9, jitter=0.0)
            p.tri_soup("Beam", box_tris((x, 1.75, z), (0.95, 0.2, 0.95)))
        p.tri_soup("Beam", box_tris((0, -0.9, z), (width + 0.6, 0.5, 0.5)))
    # rope railing strung between the post tops
    for x in (-width / 2 - 0.1, width / 2 + 0.1):
        zs = np.arange(-2, -length - 0.1, -6)
        for z0, z1 in zip(zs[:-1], zs[1:]):
            pts = [(x, 1.4 - 0.45 * math.sin(math.pi * t), z0 + (z1 - z0) * t) for t in np.linspace(0, 1, 8)]
            add_tube(p, "Rope", pts, 0.09, seg=4, cap=False)
    return p


def pier_platform(size=16.0):
    p = Prop("PierPlatform")
    planks_floor(p, -size / 2, size / 2, -size / 2, size / 2, 0.0, along="z", plank=0.95, gap=0.14, thick=0.4, seed=51)
    for x in np.linspace(-size / 2, size / 2, 3):
        for z in np.linspace(-size / 2, size / 2, 3):
            add_tube(p, "Beam", [(x, -16, z), (x, 0.2 if abs(x) < size / 2 - 0.1 and abs(z) < size / 2 - 0.1 else 1.6, z)], [0.6, 0.55], seg=9)
    for z in np.linspace(-size / 2, size / 2, 3):
        p.tri_soup("Beam", box_tris((0, -0.75, z), (size, 0.6, 0.6)))
    # mooring bollards
    for x, z in ((-size / 2 + 1, -size / 2 + 1), (size / 2 - 1, -size / 2 + 1)):
        add_tube(p, "Iron", [(x, 0, z), (x, 1.0, z)], [0.4, 0.5], seg=8)
    return p


def rowboat():
    p = Prop("Rowboat")
    L, B, Hh = 13.0, 4.4, 1.9
    sections = []
    for t in np.linspace(-1, 1, 13):
        w = B / 2 * (1 - abs(t) ** 2.2) + 0.05
        bot = -Hh * (0.75 + 0.25 * abs(t) ** 2) + 0.35 * abs(t) ** 3 * Hh
        sec = []
        for k in np.linspace(0, 1, 7):
            ang = math.pi * k
            sec.append((math.cos(ang) * w, bot * math.sin(ang) + (Hh * 0.25 * abs(t) ** 3), t * L / 2))
        sections.append(sec)
    S = np.array(sections)
    T = []
    for i in range(len(S) - 1):
        for k in range(S.shape[1] - 1):
            a, b, c, d = S[i, k], S[i, k + 1], S[i + 1, k + 1], S[i + 1, k]
            T += [[a, b, c], [a, c, d]]
    T = np.array(T)
    p.tri_soup("Plank", double(T))
    # gunwale rim
    for side in (0, -1):
        add_tube(p, "Beam", [tuple(S[i, side]) for i in range(len(S))], 0.16, seg=5)
    for z in (-3.0, 0.5, 3.5):
        i = int((z / (L / 2) + 1) / 2 * 12)
        w = abs(S[i, 0, 0]) - 0.2
        p.tri_soup("Plank", box_tris((0, -0.55, z), (2 * w, 0.25, 1.0)))
    add_tube(p, "Beam", [(1.0, -0.3, -2), (2.6, 0.2, 4.5)], 0.11, seg=5)
    p.tri_soup("Plank", box_tris((2.75, 0.25, 5.2), (0.15, 0.7, 1.4), rot_y(0.25)))
    return p


def bench():
    p = Prop("Bench")
    planks_floor(p, -3.2, 3.2, -0.7, 0.7, 1.9, along="z", plank=0.7, thick=0.25, seed=61)
    for x in (-2.6, 2.6):
        p.tri_soup("Beam", box_tris((x, 0.85, 0), (0.35, 1.7, 1.3)))
        p.tri_soup("Beam", box_tris((x, 2.6, 0.75), (0.3, 1.6, 0.25), rot_x(-0.15)))
    for y in (2.55, 3.15):
        p.tri_soup("Plank", box_tris((0, y, 0.85), (6.6, 0.4, 0.15), rot_x(-0.15)))
    return p


def picnic_table():
    p = Prop("PicnicTable")
    planks_floor(p, -3.6, 3.6, -1.4, 1.4, 2.8, along="z", plank=0.7, thick=0.25, seed=71)
    for z in (-2.8, 2.8):
        planks_floor(p, -3.6, 3.6, z - 0.5, z + 0.5, 1.6, along="z", plank=0.5, thick=0.22, seed=72)
    for x in (-2.8, 2.8):
        for s in (-1, 1):
            p.tri_soup("Beam", box_tris((x, 1.35, s * 1.3), (0.3, 3.0, 0.3), rot_x(s * 0.55)))
        p.tri_soup("Beam", box_tris((x, 1.35, 0), (0.3, 0.3, 6.0)))
    return p


def campfire():
    p = Prop("Campfire")
    for i in range(10):
        a = i / 10 * 2 * math.pi
        p.tri_soup("Rock", blob((math.cos(a) * 2.6, 0.35, math.sin(a) * 2.6), (0.75, 0.55, 0.65), 1, 0.25, seed=80 + i, squash_bottom=True))
    for i in range(5):
        a = i / 5 * 2 * math.pi + 0.3
        add_tube(p, "Bark", [(math.cos(a) * 1.9, 0.25, math.sin(a) * 1.9), (math.cos(a) * 0.15, 1.3, math.sin(a) * 0.15)], [0.32, 0.22], seg=7)
    p.tri_soup("Rock", blob((0, 0.05, 0), (1.5, 0.15, 1.5), 1, 0.2, seed=99))
    # log seats around it
    for i, a in enumerate((0.4, 2.4, 4.3)):
        c = np.array([math.cos(a) * 6.3, 0.75, math.sin(a) * 6.3])
        d = np.array([-math.sin(a), 0, math.cos(a)]) * 2.8
        add_tube(p, "Bark", [c - d, c + d], 0.75, seg=10, uv_around=2)
    return p


# ------------------------------------------------------------------ nature
def palm(seed=0, height=28.0, lean=0.35):
    r = np.random.default_rng(seed)
    p = Prop(f"Palm{seed}")
    yaw = r.uniform(0, 2 * math.pi)
    pts = []
    n = 14
    for i in range(n + 1):
        t = i / n
        bend = lean * height * (t ** 1.8)
        pts.append((math.cos(yaw) * bend, height * t, math.sin(yaw) * bend))
    radii = [1.05 - 0.45 * (i / n) + (0.25 if i == 0 else 0) for i in range(n + 1)]
    add_tube(p, "Bark", pts, radii, seg=10, uv_around=1)
    # rings
    for i in range(1, n):
        add_tube(p, "Bark", [np.array(pts[i]) - [0, 0.12, 0], np.array(pts[i]) + [0, 0.12, 0]], radii[i] + 0.12, seg=10, cap=False)
    top = np.array(pts[-1])
    # coconuts
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        p.tri_soup("Beam", blob(top + [math.cos(a) * 0.8, -0.9, math.sin(a) * 0.8], (0.55, 0.6, 0.55), 1, 0.08, seed=seed * 10 + k))
    # fronds: arched spines with leaflets on both sides (double sided)
    nf = 9
    for k in range(nf):
        a = 2 * math.pi * k / nf + r.uniform(-0.2, 0.2)
        lift = r.uniform(0.25, 0.75)
        L = r.uniform(11, 14)
        spine = []
        NS = 17
        for t in np.linspace(0, 1, NS):
            hdist = L * t
            y = lift * 6 * t - 9 * t * t * (0.7 + 0.3 * (1 - lift))
            spine.append(top + [math.cos(a) * hdist, y + 0.3, math.sin(a) * hdist])
        spine = np.array(spine)
        add_tube(p, "Frond", spine, [0.2 * (1 - t) + 0.05 for t in np.linspace(0, 1, NS)], seg=4, cap=False)
        side = np.array([-math.sin(a), 0, math.cos(a)])
        T = []
        for i in range(1, NS - 1):
            t = i / (NS - 1)
            w = 3.4 * math.sin(math.pi * min(1, t * 1.1)) + 0.5
            dvec = norm(spine[i + 1] - spine[i])
            for s in (-1, 1):
                # long narrow drooping blade
                root = spine[i]
                out = side * s * w + dvec * w * 0.45 + np.array([0, -w * 0.75, 0])
                perp = dvec * 0.32
                tip = root + out
                midp = root + out * 0.5 + np.array([0, w * 0.12, 0])
                T += [[root - perp * 0.5, midp - perp, midp + perp], [root - perp * 0.5, midp + perp, root + perp * 0.5], [midp - perp, tip, midp + perp]]
        p.tri_soup("Frond", double(T))
    return p


def jungle_tree(seed=0, height=26.0):
    r = np.random.default_rng(seed + 100)
    p = Prop(f"Jungle{seed}")
    yaw = r.uniform(0, 6.28)
    trunk = [(0, 0, 0), (0.6 * math.cos(yaw), height * 0.35, 0.6 * math.sin(yaw)), (0, height * 0.7, 0)]
    add_tube(p, "Bark", trunk, [1.6, 1.15, 0.85], seg=9, uv_around=2)
    # buttress roots
    for k in range(5):
        a = k * 2 * math.pi / 5 + yaw
        add_tube(p, "Bark", [(math.cos(a) * 2.6, 0, math.sin(a) * 2.6), (math.cos(a) * 0.6, 2.8, math.sin(a) * 0.6)], [0.5, 0.25], seg=6)
    # branches + canopy clumps
    clumps = [(0, height * 0.82, 0, 7.5)]
    for k in range(5):
        a = k * 2 * math.pi / 5 + r.uniform(-0.4, 0.4) + yaw
        reach = r.uniform(5, 8)
        y = height * r.uniform(0.55, 0.75)
        end = (math.cos(a) * reach, y + r.uniform(2, 4), math.sin(a) * reach)
        add_tube(p, "Bark", [(0, y - 2, 0), end], [0.55, 0.3], seg=6)
        clumps.append((end[0], end[1] + 1.5, end[2], r.uniform(4.5, 6.0)))
    for i, (x, y, z, s) in enumerate(clumps):
        p.tri_soup("Leaf", blob((x, y, z), (s * 1.15, s * 0.75, s * 1.15), 1, 0.32, seed=seed * 20 + i))
    return p


def bush(seed=0):
    p = Prop(f"Bush{seed}")
    r = np.random.default_rng(seed + 200)
    for i in range(4):
        a = r.uniform(0, 6.28)
        d = r.uniform(0, 1.6)
        s = r.uniform(1.6, 2.4)
        p.tri_soup("Leaf", blob((math.cos(a) * d, s * 0.55, math.sin(a) * d), (s, s * 0.8, s), 1, 0.3, seed=seed * 9 + i, squash_bottom=True))
    # a few broad tropical leaves poking out
    for k in range(7):
        a = 2 * math.pi * k / 7 + r.uniform(-0.2, 0.2)
        base = np.array([0, 1.0, 0])
        tip = base + [math.cos(a) * 4.0, r.uniform(0.5, 2.0), math.sin(a) * 4.0]
        side = np.array([-math.sin(a), 0, math.cos(a)]) * 0.9
        mid = (base + tip) / 2 + [0, 0.6, 0]
        p.tri_soup("Frond", double([[base, mid + side, tip], [base, tip, mid - side]]))
    return p


def rock(seed=0, size=(10, 6, 8)):
    p = Prop(f"Rock{seed}")
    sx, sy, sz = size
    p.tri_soup("Rock", blob((0, sy * 0.35, 0), (sx / 2, sy / 2, sz / 2), 2, 0.35, seed=300 + seed, squash_bottom=True))
    r = np.random.default_rng(seed)
    for k in range(3):
        a = r.uniform(0, 6.28)
        s = r.uniform(0.25, 0.45)
        c = (math.cos(a) * sx * 0.55, sy * 0.15, math.sin(a) * sz * 0.55)
        p.tri_soup("Rock", blob(c, (sx * s / 2, sy * s / 2, sz * s / 2), 1, 0.3, seed=400 + seed * 5 + k, squash_bottom=True))
    return p


def sea_stack(seed=0, h=44.0):
    p = Prop(f"SeaStack{seed}")
    r = np.random.default_rng(seed + 500)
    T = []
    layers = 12
    seg = 11
    rings = []
    for i in range(layers + 1):
        t = i / layers
        y = -20 + (h + 20) * t
        rr = 9.0 * (1 - 0.45 * t) * (1 + 0.15 * math.sin(t * 9 + seed))
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            j = r.uniform(0.82, 1.15)
            ring.append((math.cos(a) * rr * j + 1.5 * math.sin(t * 4), y + r.uniform(-0.8, 0.8), math.sin(a) * rr * j))
        rings.append(ring)
    R = np.array(rings)
    for i in range(layers):
        for k in range(seg):
            k2 = (k + 1) % seg
            T += [[R[i, k], R[i + 1, k2], R[i, k2]], [R[i, k], R[i + 1, k], R[i + 1, k2]]]
    top = R[-1].mean(0) + [0, 2.5, 0]
    for k in range(seg):
        T.append([R[-1, k], top, R[-1, (k + 1) % seg]])
    p.tri_soup("Rock", fix_winding(T, (0, h * 0.3, 0)) if False else np.array(T))
    # mossy cap
    p.tri_soup("Leaf", blob(top + [0, -1.2, 0], (5.5, 2.2, 5.5), 1, 0.3, seed=seed + 600))
    return p


def coral(seed=0):
    p = Prop(f"Coral{seed}")
    r = np.random.default_rng(seed + 700)
    p.tri_soup("Rock", blob((0, 0.6, 0), (4.5, 1.6, 4.0), 1, 0.3, seed=seed + 710, squash_bottom=True))
    def branch(base, d, length, rad, depth):
        end = base + d * length
        add_tube(p, "Coral", [base, end], [rad, rad * 0.7], seg=6)
        if depth > 0:
            for s in (-1, 1):
                nd = norm(d + np.array([r.uniform(-0.6, 0.6), 0.3, r.uniform(-0.6, 0.6)]) * s)
                branch(end, nd, length * 0.7, rad * 0.7, depth - 1)
        else:
            p.tri_soup("Coral", blob(end, (rad * 1.5,) * 3, 0, 0.1, seed=int(abs(end[0]) * 10)))
    for k in range(4):
        a = r.uniform(0, 6.28)
        b = np.array([math.cos(a) * 2.0, 1.4, math.sin(a) * 2.0])
        branch(b, norm(np.array([math.cos(a) * 0.4, 1, math.sin(a) * 0.4])), 2.0, 0.35, 2)
    # fan corals (thin double-sided discs)
    for k in range(2):
        a = r.uniform(0, 6.28)
        c = np.array([math.cos(a) * 2.6, 2.6, math.sin(a) * 2.6])
        side = np.array([-math.sin(a), 0, math.cos(a)])
        pts = [c + side * math.cos(t) * 2.2 + [0, math.sin(t) * 2.2, 0] for t in np.linspace(0, math.pi, 9)]
        base = c - [0, 1.5, 0]
        p.tri_soup("Coral", double([[base, pts[i], pts[i + 1]] for i in range(8)]))
    # tube coral
    for k in range(5):
        a = r.uniform(0, 6.28)
        d = r.uniform(0.5, 2.5)
        x, z = math.cos(a) * d, math.sin(a) * d
        hh = r.uniform(1.2, 2.6)
        add_tube(p, "Coral", [(x, 1.2, z), (x, 1.2 + hh, z)], [0.35, 0.45], seg=7, cap=False)
    return p


def kelp(seed=0, h=22.0):
    p = Prop(f"Kelp{seed}")
    r = np.random.default_rng(seed + 800)
    for s in range(4):
        x0, z0 = r.uniform(-2, 2), r.uniform(-2, 2)
        stem = [(x0 + 0.8 * math.sin(t * 5 + s), t * h * r.uniform(0.7, 1.0), z0 + 0.8 * math.cos(t * 4 + s)) for t in np.linspace(0, 1, 12)]
        add_tube(p, "Kelp", stem, 0.12, seg=4, cap=False)
        T = []
        for i in range(2, len(stem) - 1):
            a = r.uniform(0, 6.28)
            d = np.array([math.cos(a), 0.6, math.sin(a)])
            base = np.array(stem[i])
            tip = base + d * r.uniform(1.6, 2.6)
            side = norm(np.cross(d, [0, 1, 0])) * 0.45
            T += [[base, base + d * 0.9 + side, tip], [base, tip, base + d * 0.9 - side]]
        p.tri_soup("Kelp", double(T))
    return p


def shipwreck():
    p = Prop("Shipwreck")
    L, B, Hh = 46.0, 13.0, 9.0
    sections = []
    zs = np.linspace(-1, 1, 15)
    for t in zs:
        w = B / 2 * (1 - abs(t) ** 2.4) + 0.2
        sec = []
        for k in np.linspace(0, 1, 9):
            ang = math.pi * k
            depth = Hh * (0.85 + 0.15 * abs(t) ** 2)
            sec.append((math.cos(ang) * w, -depth * math.sin(ang) * (1 - 0.35 * abs(t) ** 3) + Hh, t * L / 2))
        sections.append(sec)
    S = np.array(sections)
    T = []
    rr = np.random.default_rng(5)
    for i in range(len(S) - 1):
        for k in range(S.shape[1] - 1):
            # broken hole in the side + missing aft planks
            if (i in (6, 7, 8) and k in (1, 2)) or (i >= 12 and k <= 2 and rr.uniform() < 0.6):
                continue
            a, b, c, d = S[i, k], S[i, k + 1], S[i + 1, k + 1], S[i + 1, k]
            T += [[a, b, c], [a, c, d]]
    p.tri_soup("RoofDark", double(np.array(T)))
    # ribs showing through the hole
    for i in range(5, 10):
        add_tube(p, "Beam", [tuple(S[i, k]) for k in range(S.shape[1])], 0.35, seg=5)
    # deck planks (partially collapsed)
    planks_floor(p, -B / 2 + 1, B / 2 - 1, -L / 2 + 6, L / 2 - 14, Hh - 0.2, along="x", plank=1.2, gap=0.3, thick=0.4, mat="Plank", seed=91, jitter=0.4)
    # broken mast lying across + standing stump
    add_tube(p, "Beam", [(0, Hh, 4), (0, Hh + 9, 4)], [0.9, 0.8], seg=9)
    add_tube(p, "Beam", [(1, Hh + 0.5, 6), (16, 1.0, 26)], [0.75, 0.6], seg=9)
    # torn sail draped from the mast
    p.tri_soup("Sail", double([[(1.5, Hh + 0.8, 7), (9, 4.5, 16), (4, Hh - 2, 4)], [(9, 4.5, 16), (12, 1.6, 22), (6, 2.5, 13)]]))
    # cannons / barrels scattered
    for x, z in ((-3, -8), (3.5, -2), (-4, 12)):
        barrel(p, (x, Hh - 0.2, z), 0.9, 2.2)
    for k in range(4):
        z = -12 + k * 6
        add_tube(p, "Iron", [(B / 2 - 1.5, Hh + 0.6, z), (B / 2 + 1.2, Hh + 0.9, z)], [0.45, 0.38], seg=8)
    # treasure chest in the hold (an exploration reward to spot)
    p.tri_soup("Plank", box_tris((-1.5, 2.6, 2), (3.2, 2.0, 2.2), rot_y(0.3)))
    p.tri_soup("Iron", box_tris((-1.5, 3.7, 2), (3.4, 0.3, 2.4), rot_y(0.3)))
    p.tri_soup("Glow", box_tris((-1.5, 3.95, 2), (2.6, 0.2, 1.6), rot_y(0.3)))
    return p


def ruins_arch():
    p = Prop("RuinsArch")
    span, hgt = 18.0, 16.0
    for x in (-span / 2, span / 2):
        for k in range(5):
            y = k * 2.6 + 1.3
            j = np.random.default_rng(int(x) + k + 50).uniform(-0.25, 0.25)
            p.tri_soup("Stone", box_tris((x + j, y, j), (3.6, 2.4, 3.6), rot_y(j * 0.3)))
    # voussoir blocks along the arch
    n = 11
    for k in range(n):
        a0 = math.pi * k / n
        a1 = math.pi * (k + 1) / n
        am = (a0 + a1) / 2
        r = span / 2
        c = (math.cos(am) * r, 13.0 + math.sin(am) * 5.5, 0)
        if k == 7:
            continue  # a missing stone
        p.tri_soup("Stone", box_tris(c, (2.6, 2.4, 3.4), rot_z(am - math.pi / 2)))
    # rubble
    for k in range(6):
        rr = np.random.default_rng(k + 40)
        p.tri_soup("Stone", box_tris((rr.uniform(-12, 12), 0.7, rr.uniform(-5, 5)), (2.4, 1.4, 2.4), rot_y(rr.uniform(0, 3)) @ rot_x(rr.uniform(-0.3, 0.3))))
    # glowing rune stone in the middle (underwater landmark)
    p.tri_soup("Glow", box_tris((0, 1.4, 0), (1.6, 2.8, 0.6)))
    return p


def sign_frame():
    """wooden frame + tiled roof for the leaderboard (board is 20 x 10, centred at y = 8.2 local -> here base y=0)"""
    p = Prop("SignFrame")
    for x in (-11.2, 11.2):
        post(p, x, 0, -0.5, 14.2, 0.55)
    p.tri_soup("Beam", box_tris((0, 13.6, 0), (24.0, 0.6, 0.9)))
    p.tri_soup("Beam", box_tris((0, 2.9, 0), (23.0, 0.6, 0.9)))
    gable_roof(p, 0, 0, 24.0, 2.4, 14.0, 1.6, over=0.8)
    for x in (-11.2, 11.2):
        lantern(p, (x, 12.0, -1.2), 0.8)
    return p


def build():
    props = [cabin(), townhouse(), shop_stall(), boathouse(), lantern_post(), hanging_lantern(), pier(), pier_platform(), rowboat(),
             bench(), picnic_table(), campfire(), shipwreck(), ruins_arch(), sign_frame()]
    props += props_small()
    props += [palm(0), palm(1, 24, 0.5), palm(2, 31, 0.25), jungle_tree(0), jungle_tree(1, 30), bush(0), bush(1),
              rock(0, (12, 7, 10)), rock(1, (20, 10, 16)), rock(2, (7, 4, 6)), sea_stack(0), sea_stack(1, 34), coral(0), coral(1), kelp(0), kelp(1, 16)]
    return props


if __name__ == "__main__":
    import sys
    props = build()
    nodes = []
    for i, pr in enumerate(props):
        print(f"{pr.name:16s} tris={pr.tris():6d} mats={list(pr.geo)}")
        nodes += pr.nodes()
    print("nodes", len(nodes))
    write_glb(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/meshkit/kit.glb", nodes)
