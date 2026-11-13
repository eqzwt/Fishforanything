"""Low-poly island land for Fish For Anything (Fisch-inspired, original).
- one deterministic height function shared with Luau (value noise on a fixed permutation table)
- faceted jittered-grid surface, flat-shaded, coloured per triangle from a small palette texture
- terraced cliffs for angular ledges, rolling meadows, sandy beaches, dirt paths
- closed tiles (top + walls + bottom) so Roblox can build precise collision
Land below Y=-4.5 is left to smooth terrain (sea floor + the water itself)."""
import math, random
import numpy as np
from PIL import Image
from glb import write_glb

_r = random.Random(1337)
PERM = list(range(256))
_r.shuffle(PERM)
PERM_NP = np.array(PERM + PERM, dtype=np.int64)


def vnoise(x, z, s):
    ix = np.floor(x).astype(np.int64)
    iz = np.floor(z).astype(np.int64)
    fx = x - ix
    fz = z - iz
    u = fx * fx * (3 - 2 * fx)
    v = fz * fz * (3 - 2 * fz)
    def h(a, b):
        return PERM_NP[(PERM_NP[(a + s * 57) & 255] + b) & 255].astype(float)
    a = h(ix, iz); b = h(ix + 1, iz); c = h(ix, iz + 1); d = h(ix + 1, iz + 1)
    top = a + (b - a) * u
    bot = c + (d - c) * u
    return (top + (bot - top) * v) / 255.0 - 0.5


def fbm(x, z, octaves, scale, seed):
    amp, f, tot, norm = 1.0, 1.0 / scale, 0.0, 0.0
    for i in range(1, octaves + 1):
        tot = tot + amp * vnoise(x * f, z * f, seed + i)
        norm += amp
        amp *= 0.5
        f *= 2.03
    return tot / norm


def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def chain(px, pz, pts):
    best = np.full(np.shape(px), 1e9)
    for (ax, az, ar), (bx, bz, br) in zip(pts[:-1], pts[1:]):
        vx, vz = bx - ax, bz - az
        t = np.clip(((px - ax) * vx + (pz - az) * vz) / (vx * vx + vz * vz), 0, 1)
        qx, qz = ax + vx * t - px, az + vz * t - pz
        d = np.sqrt(qx * qx + qz * qz) - (ar + (br - ar) * t)
        best = np.minimum(best, d)
    return best


def ellipse(px, pz, cx, cz, rx, rz):
    dx, dz = (px - cx) / rx, (pz - cz) / rz
    return (np.sqrt(dx * dx + dz * dz) - 1) * min(rx, rz)


def circle(px, pz, cx, cz, r):
    return np.sqrt((px - cx) ** 2 + (pz - cz) ** 2) - r


def segd(px, pz, ax, az, bx, bz):
    vx, vz = bx - ax, bz - az
    t = np.clip(((px - ax) * vx + (pz - az) * vz) / (vx * vx + vz * vz), 0, 1)
    qx, qz = ax + vx * t - px, az + vz * t - pz
    return np.sqrt(qx * qx + qz * qz)


def terrace(h, step, sharp):
    k = h / step
    fl = np.floor(k)
    f = k - fl
    return (fl + ss(1 - sharp, 1.0, f)) * step


WEST = [(-170, 285, 52), (-250, 190, 70), (-318, 70, 92), (-296, -60, 70), (-262, -150, 58), (-236, -228, 40)]
WEST2 = [(-205, -268, 22), (-160, -318, 12)]
EAST = [(200, 290, 52), (268, 205, 64), (312, 110, 70), (318, 35, 56)]
EASTISLES = [(300, -65, 34), (262, -150, 44), (238, -210, 22)]
ROCKS = [(-170, 150, 13), (205, 148, 11), (78, -268, 15), (-48, -300, 10), (340, -270, 26), (-360, -330, 30)]
PATHS = [(0, 300, 0, 236), (0, 292, 24, 262), (24, 262, 46, 270), (0, 300, -40, 268), (0, 300, 40, 352), (40, 352, 70, 420)]


def height(x, z):
    """returns (h, kind) ; kind codes: 0 sea, 1 beach/meadow, 2 ridge, 3 cliff, 4 islet"""
    x = np.asarray(x, float)
    z = np.asarray(z, float)
    n1 = fbm(x, z, 4, 90, 1)
    n2 = fbm(x, z, 3, 26, 9)
    r = np.sqrt((x - 8) ** 2 + (z + 10) ** 2)
    floor = -24 - 18 * ss(30, 170, r) + n1 * 14 + n2 * 4
    floor = lerp(floor, -80 + n1 * 14, ss(330, 560, r))
    h = floor.copy()
    kind = np.zeros(np.shape(x), int)
    dt = segd(x, z, 125, -50, 40, -235) - (24 + n2 * 10)
    h = np.where(dt < 22, np.minimum(h, lerp(-96 + n2 * 6, h, ss(-6, 22, dt))), h)

    def land(d, top, slope, code):
        nonlocal h, kind
        v = np.where(d <= 0, top(-d), -d * slope)
        m = v > h
        h = np.where(m, v, h)
        kind = np.where(m, code, kind)

    # meadow + beach in front of the bay (keeps the old spawn/shop/dock heights ~4.4)
    dv = ellipse(x, z, 10, 332, 285, 97) + fbm(x, z, 2, 60, 21) * 18 * ss(60, 140, np.abs(x - 10))
    land(dv, lambda i: 0.6 + 3.8 * ss(2, 24, i) + (n2 * 2.4 + n1 * 3) * ss(30, 60, i), 0.2, 1)
    # rolling forested hills behind, with a lookout knoll
    dr = ellipse(x, z, 20, 478, 400, 120) + n1 * 30
    def ridge_top(i):
        raw = 4.4 + 64 * ss(0, 85, i) * (0.75 + n1 * 1.4) + n2 * 6 * ss(0, 20, i)
        return lerp(raw, terrace(raw, 6.0, 0.35), 0.6 * ss(6, 14, raw))
    land(dr, ridge_top, 0.5, 2)
    dk = circle(x, z, 70, 425, 40) + n2 * 8
    land(dk, lambda i: lerp(6 + 22 * ss(0, 30, i), terrace(6 + 22 * ss(0, 30, i), 6.0, 0.3), 0.7), 0.6, 2)
    # rocky cliff arms: tall, terraced into angular ledges
    dw = np.minimum(chain(x, z, WEST), chain(x, z, WEST2)) + n2 * 14 + n1 * 26
    de = np.minimum(chain(x, z, EAST), chain(x, z, EASTISLES)) + n2 * 14 + n1 * 22

    def cliff_top(i, seed):
        H = 42 + 34 * fbm(x, z, 3, 70, seed) * 2
        raw = 2.5 + H * ss(5, 24, i) + 3 * ss(24, 60, i) * n2
        return lerp(raw, terrace(raw, 8.0, 0.25), 0.9)
    land(dw, lambda i: cliff_top(i, 31), 1.25, 3)
    land(de, lambda i: cliff_top(i, 47), 1.25, 3)
    land(circle(x, z, -118, -212, 27) + n2 * 6, lambda i: 0.6 + 3.2 * ss(0, 12, i), 0.45, 4)
    land(circle(x, z, 168, -252, 32) + n2 * 8, lambda i: lerp(2 + 30 * ss(4, 20, i), terrace(2 + 30 * ss(4, 20, i), 6.0, 0.3), 0.8), 1.1, 3)
    for rx, rz, rr in ROCKS:
        land(circle(x, z, rx, rz, rr) + n2 * 6, lambda i, rr=rr: lerp(1.5 + rr * 1.1 * ss(2, rr * 0.7, i), terrace(1.5 + rr * 1.1 * ss(2, rr * 0.7, i), 5.0, 0.3), 0.8), 1.3, 3)
    # hidden cove pool cut into the west cliffs, reached by a swim-through gap
    dc = circle(x, z, -268, -40, 30) + n2 * 5
    m = dc < 0
    h = np.where(m, np.minimum(h, lerp(-14, h, ss(-30, 0, dc))), h)
    kind = np.where(m, 0, kind)
    gap = segd(x, z, -268, -40, -205, -52) - (8 + n2 * 6)
    m = gap < 0
    h = np.where(m, np.minimum(h, -10), h)
    kind = np.where(m, 0, kind)
    # flatten the dirt paths a little
    pd = np.min([segd(x, z, *p) for p in PATHS], axis=0)
    h = np.where((pd < 5) & (h > 2) & (kind <= 2), lerp(h, h - 0.35, ss(5, 2, pd)), h)
    return h, kind, pd


# ------------------------------------------------------------------ palette (8 rows x 16 shades)
ROWS = {
    "grass": (112, 150, 82), "grass_dark": (72, 112, 62), "sand": (226, 206, 160), "sand_wet": (186, 166, 128),
    "rock": (150, 142, 130), "rock_dark": (106, 100, 94), "dirt": (142, 108, 72), "moss": (98, 124, 84),
}
ROW_ORDER = ["grass", "grass_dark", "moss", "dirt", "sand", "sand_wet", "rock", "rock_dark"]
PAL_W, PAL_H = 16, 8
CELL = 32


def palette():
    img = np.zeros((PAL_H * CELL, PAL_W * CELL, 3))
    rr = np.random.default_rng(3)
    for ri, name in enumerate(ROW_ORDER):
        base = np.array(ROWS[name], float)
        for ci in range(PAL_W):
            k = (ci - (PAL_W - 1) / 2) / ((PAL_W - 1) / 2)  # -1..1
            col = base * (1 + 0.11 * k) + rr.uniform(-4, 4, 3)
            if name in ("grass", "grass_dark", "moss"):
                col += np.array([6 * k, 2 * k, -4 * k])  # warmer light shades, cooler dark ones
            img[ri * CELL:(ri + 1) * CELL, ci * CELL:(ci + 1) * CELL] = np.clip(col, 0, 255)
    Image.fromarray(img.astype(np.uint8)).save("/mnt/user-data/outputs/ffa_land_palette.png")
    return img


def pal_uv(row_name, col):
    ri = ROW_ORDER.index(row_name)
    return ((col + 0.5) / PAL_W, (ri + 0.5) / PAL_H)


# ------------------------------------------------------------------ mesh
S = 9.0            # facet spacing (chunky)
X0, X1, Z0, Z1 = -504, 504, -378, 602
TILE = 96.0
CUT = -4.5         # below this the smooth terrain sea floor takes over
BOTTOM = -12.0


def build():
    rr = np.random.default_rng(21)
    nx = int((X1 - X0) / S) + 1
    nz = int((Z1 - Z0) / S) + 1
    gx, gz = np.meshgrid(X0 + np.arange(nx) * S, Z0 + np.arange(nz) * S, indexing="ij")
    jx = rr.uniform(-2.0, 2.0, gx.shape)
    jz = rr.uniform(-2.0, 2.0, gz.shape)
    jx[[0, -1], :] = 0; jz[:, [0, -1]] = 0
    vx, vz = gx + jx, gz + jz
    vh, vk, vpd = height(vx, vz)
    # cliffs: lift the jitter so ledge edges stay crisp
    tiles = {}
    low = np.random.default_rng(5)
    for i in range(nx - 1):
        for j in range(nz - 1):
            q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            # alternate the diagonal for a less regular look
            tris = [(q[0], q[1], q[2]), (q[0], q[2], q[3])] if (i + j) % 2 == 0 else [(q[0], q[1], q[3]), (q[1], q[2], q[3])]
            for t in tris:
                P = np.array([[vx[a, b], vh[a, b], vz[a, b]] for a, b in t])
                if P[:, 1].max() < CUT:
                    continue
                c = P.mean(0)
                key = (int((c[0] - X0) // TILE), int((c[2] - Z0) // TILE))
                tiles.setdefault(key, []).append((P, [vk[a, b] for a, b in t], [vpd[a, b] for a, b in t]))
    nodes = []
    stats = []
    for key, tl in sorted(tiles.items()):
        tris, uvs, nrms = [], [], []
        edge_count = {}
        for P, ks, pds in tl:
            # make every top triangle face up
            n = np.cross(P[1] - P[0], P[2] - P[0])
            if n[1] < 0:
                P = P[[0, 2, 1]]
                n = -n
            n = n / np.linalg.norm(n)
            c = P.mean(0)
            hy = c[1]
            kind = max(ks)
            pd = min(pds)
            steep = n[1]
            nz_ = float(fbm(np.array(c[0]), np.array(c[2]), 2, 40, 77))
            if steep < 0.55:
                row = "rock_dark" if nz_ > 0.02 else "rock"
            elif steep < 0.74 and hy > 2:
                row = "moss" if (kind != 3 and nz_ > -0.05) else "rock"
            elif hy < 0.3:
                row = "sand_wet"
            elif hy < 2.8 and kind in (1, 4, 0):
                row = "sand"
            elif pd < 4.2 and kind in (1, 2) and hy > 2:
                row = "dirt"
            elif kind == 2 and hy > 9:
                row = "grass_dark"
            elif kind == 3:
                row = "grass_dark" if nz_ > 0 else "moss"
            else:
                row = "grass"
            col = int(np.clip((nz_ + 0.25) * 22 + low.uniform(-3, 3) + (steep - 0.8) * 6, 0, PAL_W - 1))
            uv = pal_uv(row, col)
            tris.append(P)
            uvs.append([uv, uv, uv])
            nrms.append([n, n, n])
            for a, b in ((0, 1), (1, 2), (2, 0)):
                ka = tuple(np.round(P[a], 3)); kb = tuple(np.round(P[b], 3))
                e = (ka, kb) if ka < kb else (kb, ka)
                edge_count[e] = edge_count.get(e, 0) + 1
        # bottom (reversed copy) + walls along the open boundary so the tile is a closed solid
        top = np.array(tris)
        bot = top.copy()
        bot[:, :, 1] = BOTTOM
        bot = bot[:, ::-1]
        dark = pal_uv("rock_dark", 3)
        walls = []
        for P in tris:
            for a, b in ((0, 1), (1, 2), (2, 0)):
                ka = tuple(np.round(P[a], 3)); kb = tuple(np.round(P[b], 3))
                e = (ka, kb) if ka < kb else (kb, ka)
                if edge_count[e] == 1:
                    A, B = P[a], P[b]
                    A2, B2 = np.array([A[0], BOTTOM, A[2]]), np.array([B[0], BOTTOM, B[2]])
                    walls += [[A, B2, B], [A, A2, B2]]  # outward for counter-clockwise top winding
        allT = [top, bot]
        if walls:
            allT.append(np.array(walls))
        T = np.concatenate(allT)
        fn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        fn = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-9)
        N = np.repeat(fn[:, None, :], 3, axis=1)
        U = np.concatenate([np.array(uvs), np.full((len(bot), 3, 2), dark), np.full((len(walls), 3, 2), dark)]) if walls else np.concatenate([np.array(uvs), np.full((len(bot), 3, 2), dark)])
        pos = T.reshape(-1, 3) * np.array([-1, 1, -1])
        nrm = N.reshape(-1, 3) * np.array([-1, 1, -1])
        nodes.append(dict(name=f"Land_{key[0]}_{key[1]}", prims=[dict(material="Land", pos=pos, nrm=nrm, uv=U.reshape(-1, 2), idx=np.arange(len(pos)))]))
        stats.append((key, len(tris), len(T)))
    return nodes, stats


if __name__ == "__main__":
    palette()
    nodes, stats = build()
    print("tiles", len(nodes), "max tris", max(s[2] for s in stats), "total top tris", sum(s[1] for s in stats))
    write_glb("/mnt/user-data/outputs/ffa_land.glb", nodes)
    # spot checks of gameplay heights
    for name, (x, z) in {"spawn": (0, 292), "gill": (24.76, 267.3), "dock base": (0, 262), "dock end": (0, 166), "cast ring N": (8, -190), "cast ring W": (-182, 0)}.items():
        h, k, _ = height(np.array(x, float), np.array(z, float))
        print(f"{name:12s} h={float(h):7.2f} kind={int(k)}")
