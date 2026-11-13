"""Tileable stylized PBR-ish textures (color + normal) for the island kit and terrain variants."""
import numpy as np
from PIL import Image
import os

OUT = "/home/claude/meshkit/tex"
os.makedirs(OUT, exist_ok=True)
N = 512
rng = np.random.default_rng(11)


def fnoise(n=N, beta=2.0, seed=0, aniso=(1.0, 1.0)):
    """periodic fractal noise via FFT (perfectly tileable), normalised 0..1"""
    r = np.random.default_rng(seed)
    w = r.normal(size=(n, n))
    fx = np.fft.fftfreq(n)[:, None] * aniso[0]
    fy = np.fft.fftfreq(n)[None, :] * aniso[1]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1
    spec = np.fft.fft2(w) / f ** (beta / 2)
    spec[0, 0] = 0
    out = np.real(np.fft.ifft2(spec))
    out = (out - out.min()) / (out.max() - out.min())
    return out


def lerpc(a, b, t):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    return a + (b - a) * t[..., None]


def ramp(t, stops):
    """stops: list of (pos, rgb)"""
    t = np.clip(t, 0, 1)
    out = np.zeros(t.shape + (3,))
    for (p0, c0), (p1, c1) in zip(stops[:-1], stops[1:]):
        m = (t >= p0) & (t <= p1)
        k = (t[m] - p0) / max(p1 - p0, 1e-6)
        out[m] = lerpc(c0, c1, k)
    return out


def normal_from_height(h, strength=4.0):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nz = np.ones_like(h)
    n = np.stack([-dx, dy, nz], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def save(name, col, height=None, strength=4.0):
    col = np.clip(col, 0, 255).astype(np.uint8)
    Image.fromarray(col).save(f"{OUT}/{name}_c.png")
    if height is not None:
        Image.fromarray(normal_from_height(height, strength)).save(f"{OUT}/{name}_n.png")


def voronoi(n, count, seed, jitter=1.0):
    """periodic voronoi: returns (F1 dist, F2-F1 edge, cell id)"""
    r = np.random.default_rng(seed)
    pts = r.uniform(0, n, (count, 2))
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    best = np.full((n, n), 1e9)
    second = np.full((n, n), 1e9)
    ids = np.zeros((n, n), int)
    for i, (px, py) in enumerate(pts):
        dx = np.abs(xx - px)
        dx = np.minimum(dx, n - dx)
        dy = np.abs(yy - py)
        dy = np.minimum(dy, n - dy)
        d = np.sqrt(dx * dx + dy * dy)
        m = d < best
        second = np.where(m, best, np.minimum(second, d))
        ids = np.where(m, i, ids)
        best = np.where(m, d, best)
    return best, second - best, ids


# ------------------------------------------------------------------ wood planks (grain along U / horizontal)
def planks(name, base, dark, light, plank_rows=4, seed=1, gap_dark=0.35):
    grain = fnoise(beta=2.2, seed=seed, aniso=(1.0, 0.06))  # long streaks
    fine = fnoise(beta=1.2, seed=seed + 1, aniso=(1.0, 0.15))
    rows = np.floor(np.arange(N) / (N / plank_rows)).astype(int)
    r = np.random.default_rng(seed)
    tint = r.uniform(-0.12, 0.12, plank_rows + 1)[rows][:, None]
    # plank end joints at random offsets per row
    t = 0.55 * grain + 0.3 * fine + 0.15 + tint
    col = ramp(t, [(0, dark), (0.55, base), (1, light)])
    yin = (np.arange(N) % (N / plank_rows)) / (N / plank_rows)
    edge = np.minimum(yin, 1 - yin)[:, None]
    seam = np.broadcast_to(np.clip(edge * N / plank_rows / 3.0, 0, 1), (N, N)).copy()
    h = 0.6 * grain + 0.2 * fine
    for k in range(plank_rows):
        jx = int(r.uniform(0, N))
        y0, y1 = int(k * N / plank_rows), int((k + 1) * N / plank_rows)
        xs = (np.arange(N) - jx) % N
        joint = np.clip(np.minimum(xs, N - xs) / 3.0, 0, 1)
        seam[y0:y1] = np.minimum(seam[y0:y1], joint[None, :])
    col = col * (gap_dark + (1 - gap_dark) * seam[..., None] ** 0.6)
    h = h * 0.4 + seam * 0.6
    # nail heads
    for k in range(plank_rows):
        for x in (int(r.uniform(0, N)),):
            yc = int((k + 0.5) * N / plank_rows)
            for dy in (-int(N / plank_rows * 0.25), int(N / plank_rows * 0.25)):
                yy, xx = np.ogrid[:N, :N]
                m = ((yy - (yc + dy)) % N - 0) ** 2 + ((xx - x) % N) ** 2 < 9
                col[m] = col[m] * 0.45
    save(name, col, h, 3.0)


# ------------------------------------------------------------------ roof tiles (terracotta rows, scalloped)
def roof(name, base, dark, light, seed=3):
    n1 = fnoise(beta=2.0, seed=seed)
    rows = 8
    cols = 10
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    ry = (yy / (N / rows)) % 1.0
    row = np.floor(yy / (N / rows))
    xshift = (row % 2) * 0.5
    rx = ((xx / (N / cols)) + xshift) % 1.0
    # each tile: rounded bottom edge, bump across
    curve = 1 - (2 * rx - 1) ** 2
    bottom = ry
    h = curve * 0.6 + bottom * 0.4
    shade = 0.55 + 0.45 * curve * (0.6 + 0.4 * bottom)
    r = np.random.default_rng(seed)
    tid = (row * cols + np.floor((xx / (N / cols)) + xshift)).astype(int)
    var = r.uniform(-0.15, 0.15, tid.max() + 1)[tid]
    t = np.clip(0.5 + var + (n1 - 0.5) * 0.4, 0, 1)
    col = ramp(t, [(0, dark), (0.5, base), (1, light)]) * shade[..., None]
    gap = np.clip(np.minimum(ry, 1 - ry) * 18, 0.3, 1)
    col *= gap[..., None]
    # moss / grime toward the bottom of each row
    grime = np.clip((n1 - 0.6) * 3, 0, 1) * 0.4
    col = col * (1 - grime[..., None]) + np.array([70, 80, 60]) * grime[..., None]
    save(name, col, h * gap, 5.0)


# ------------------------------------------------------------------ stone blocks (irregular rounded stones + mortar)
def stone(name, base, dark, light, count=38, seed=5, mortar=(70, 70, 72)):
    f1, edge, ids = voronoi(N, count, seed)
    r = np.random.default_rng(seed)
    var = r.uniform(-0.2, 0.2, count)[ids]
    n1 = fnoise(beta=1.6, seed=seed + 1)
    n2 = fnoise(beta=2.4, seed=seed + 2)
    t = np.clip(0.5 + var + (n1 - 0.5) * 0.5, 0, 1)
    col = ramp(t, [(0, dark), (0.5, base), (1, light)])
    bevel = np.clip(edge / 9.0, 0, 1)
    col = col * (0.55 + 0.45 * bevel[..., None])
    m = edge < 2.5
    col[m] = np.array(mortar)
    h = bevel * 0.8 + n2 * 0.2
    save(name, col, h, 6.0)


def plaster(name):
    n1 = fnoise(beta=1.8, seed=21)
    n2 = fnoise(beta=2.6, seed=22)
    t = 0.6 * n1 + 0.4 * n2
    col = ramp(t, [(0, (190, 170, 140)), (0.5, (226, 210, 178)), (1, (240, 230, 205))])
    grime = np.clip((n2 - 0.55) * 2.5, 0, 1) * 0.35
    col = col * (1 - grime[..., None]) + np.array([120, 110, 95]) * grime[..., None]
    save(name, col, n1 * 0.6 + n2 * 0.4, 2.0)


def bark(name, base, dark, light, rings=8, seed=31):
    """palm/tree bark: v (vertical) has ring bands; u wraps around"""
    n1 = fnoise(beta=2.0, seed=seed, aniso=(0.12, 1.0))  # vertical streaks
    yy = np.arange(N)[:, None] / N
    band = (yy * rings) % 1.0
    ring = np.clip(np.abs(band - 0.5) * 2, 0, 1) ** 3
    t = 0.65 * n1 + 0.35 * (1 - ring)
    col = ramp(t, [(0, dark), (0.5, base), (1, light)])
    col = col * (0.6 + 0.4 * (1 - ring))[..., None] if False else col * (1 - 0.45 * ring)[..., None]
    save(name, col, n1 * 0.5 + (1 - ring) * 0.5, 5.0)


def foliage(name, base, dark, light, seed=41, scale=1.0):
    f1, edge, ids = voronoi(N, 90, seed)
    r = np.random.default_rng(seed)
    var = r.uniform(-0.25, 0.25, 90)[ids]
    n1 = fnoise(beta=1.7, seed=seed + 1)
    leaf = np.clip(1 - f1 / 28.0, 0, 1)
    t = np.clip(0.45 + var + leaf * 0.35 + (n1 - 0.5) * 0.3, 0, 1)
    col = ramp(t, [(0, dark), (0.5, base), (1, light)])
    col = col * (0.6 + 0.4 * np.clip(edge / 6, 0, 1))[..., None]
    save(name, col, leaf * 0.7 + n1 * 0.3, 4.0)


def frond(name):
    """palm leaf: strong parallel veins along U"""
    yy = np.arange(N)[:, None] / N
    veins = (np.sin(yy * np.pi * 2 * 24) * 0.5 + 0.5) ** 2
    n1 = fnoise(beta=2.2, seed=51, aniso=(0.1, 1.0))
    t = 0.55 * n1 + 0.45 * veins
    col = ramp(t, [(0, (34, 70, 32)), (0.5, (62, 118, 52)), (1, (110, 160, 80))])
    save(name, np.broadcast_to(col, (N, N, 3)).copy(), np.broadcast_to(veins * 0.5 + n1 * 0.5, (N, N)).copy(), 3.0)


def rock(name, base, dark, light, seed=61, strata=True):
    n1 = fnoise(beta=2.2, seed=seed)
    n2 = fnoise(beta=1.5, seed=seed + 1)
    f1, edge, ids = voronoi(N, 26, seed + 2)
    cracks = np.clip(edge / 5.0, 0, 1)
    t = 0.5 * n1 + 0.3 * n2 + 0.2
    if strata:
        yy = np.arange(N)[:, None] / N
        t = t + 0.15 * np.sin((yy + n1 * 0.15) * np.pi * 2 * 5)
    col = ramp(np.clip(t, 0, 1), [(0, dark), (0.5, base), (1, light)])
    col = col * (0.55 + 0.45 * cracks[..., None])
    save(name, col, n1 * 0.6 + cracks * 0.4, 6.0)


def sand():
    n1 = fnoise(beta=1.2, seed=71)
    n2 = fnoise(beta=2.6, seed=72)
    yy, xx = np.mgrid[0:N, 0:N] / N
    ripple = np.sin((xx * 6 + yy * 2 + n2 * 0.8) * np.pi * 2) * 0.5 + 0.5
    t = 0.45 * n1 + 0.25 * n2 + 0.3 * ripple
    col = ramp(t, [(0, (176, 162, 132)), (0.5, (214, 202, 170)), (1, (238, 230, 205))])
    # speckles
    sp = rng.uniform(size=(N, N)) > 0.985
    col[sp] *= 0.7
    save("t_sand", col, ripple * 0.6 + n1 * 0.4, 2.5)


def grass():
    n1 = fnoise(beta=2.0, seed=81)
    n2 = fnoise(beta=1.0, seed=82)
    blades = fnoise(beta=0.6, seed=83, aniso=(1.0, 0.3))
    t = 0.5 * n1 + 0.2 * n2 + 0.3 * blades
    col = ramp(t, [(0, (30, 62, 34)), (0.5, (52, 98, 48)), (1, (96, 140, 70))])
    save("t_grass", col, blades * 0.7 + n2 * 0.3, 3.0)


def leafy():
    foliage("t_leafy", (44, 90, 46), (22, 50, 30), (80, 130, 66), seed=91)


def dirt():
    n1 = fnoise(beta=2.0, seed=101)
    n2 = fnoise(beta=1.0, seed=102)
    f1, edge, ids = voronoi(N, 70, 103)
    pebble = np.clip(1 - f1 / 9, 0, 1) * (np.random.default_rng(104).uniform(size=70)[ids] > 0.6)
    t = 0.6 * n1 + 0.4 * n2
    col = ramp(t, [(0, (82, 62, 44)), (0.5, (120, 94, 66)), (1, (150, 124, 92))])
    col = col * (1 - pebble[..., None] * 0.2) + pebble[..., None] * np.array([40, 40, 40])
    save("t_dirt", col, n1 * 0.5 + pebble * 0.5, 3.0)


def mud():
    n1 = fnoise(beta=2.2, seed=111)
    n2 = fnoise(beta=1.2, seed=112)
    t = 0.6 * n1 + 0.4 * n2
    col = ramp(t, [(0, (70, 74, 64)), (0.5, (104, 106, 88)), (1, (134, 132, 110))])
    save("t_silt", col, t, 2.0)


def fabric():
    """red / cream awning stripes along V"""
    xx = np.arange(N)[None, :] / N
    stripe = ((xx * 4) % 1.0) < 0.5
    weave = (np.sin(np.arange(N)[:, None] * 1.3) * np.sin(np.arange(N)[None, :] * 1.3)) * 0.04
    n1 = fnoise(beta=2.0, seed=121)
    col = np.where(stripe[..., None], np.array([186, 52, 44]), np.array([232, 220, 196])).astype(float)
    col = np.broadcast_to(col, (N, N, 3)) * (0.85 + 0.15 * n1[..., None] + weave[..., None])
    save("m_fabric", col, n1 * 0.3 + weave * 4, 2.0)


def rope():
    yy, xx = np.mgrid[0:N, 0:N] / N
    twist = (np.sin((xx * 3 + yy * 8) * np.pi * 2) * 0.5 + 0.5)
    col = ramp(twist, [(0, (120, 96, 64)), (1, (206, 180, 132))])
    save("m_rope", col, twist, 4.0)


def iron():
    n1 = fnoise(beta=2.0, seed=131)
    n2 = fnoise(beta=1.0, seed=132)
    t = 0.7 * n1 + 0.3 * n2
    col = ramp(t, [(0, (30, 30, 34)), (0.6, (58, 58, 62)), (1, (110, 80, 60))])
    save("m_iron", col, n1, 2.0)


def coral_tex():
    n1 = fnoise(beta=1.6, seed=141)
    f1, edge, ids = voronoi(N, 140, 142)
    pores = np.clip(f1 / 8.0, 0, 1)
    t = 0.6 * n1 + 0.4 * pores
    col = ramp(t, [(0, (150, 50, 90)), (0.5, (236, 104, 120)), (1, (255, 178, 140))])
    save("m_coral", col, pores, 4.0)


def kelp_tex():
    xx = np.arange(N)[None, :] / N
    n1 = fnoise(beta=2.0, seed=151, aniso=(1.0, 0.12))
    t = 0.7 * n1 + 0.3 * (np.sin(xx * np.pi * 2 * 6) * 0.5 + 0.5)
    col = ramp(t, [(0, (40, 60, 24)), (0.5, (86, 110, 40)), (1, (140, 150, 60))])
    save("m_kelp", col, t, 2.0)


def sail():
    n1 = fnoise(beta=1.8, seed=161)
    n2 = fnoise(beta=2.6, seed=162)
    col = ramp(0.6 * n1 + 0.4 * n2, [(0, (120, 112, 90)), (0.6, (196, 186, 156)), (1, (226, 218, 194))])
    holes = (n2 > 0.86)
    col[holes] *= 0.35
    save("m_sail", col, n1, 2.0)


if __name__ == "__main__":
    planks("m_plank", (150, 104, 66), (92, 60, 36), (196, 150, 102), plank_rows=4, seed=1)
    planks("m_beam", (102, 70, 46), (56, 38, 26), (140, 102, 70), plank_rows=2, seed=2, gap_dark=0.6)
    planks("m_roofdark", (78, 68, 64), (42, 38, 38), (112, 100, 92), plank_rows=6, seed=3)
    roof("m_roof", (196, 96, 54), (130, 56, 34), (232, 140, 86))
    stone("m_stone", (132, 138, 146), (86, 90, 100), (176, 180, 186))
    plaster("m_plaster")
    bark("m_bark", (110, 86, 64), (64, 48, 36), (150, 124, 94))
    foliage("m_leaf", (40, 92, 52), (18, 46, 30), (82, 140, 78))
    frond("m_frond")
    rock("m_rock", (120, 130, 140), (70, 78, 90), (168, 176, 184))
    fabric(); rope(); iron(); coral_tex(); kelp_tex(); sail()
    # terrain variants
    sand(); grass(); leafy(); dirt(); mud()
    rock("t_rock", (112, 122, 134), (62, 70, 84), (160, 168, 178), seed=171)
    rock("t_basalt", (66, 72, 84), (34, 38, 48), (102, 110, 122), seed=181)
    stone("t_slate", (70, 82, 90), (40, 48, 56), (100, 112, 118), count=24, seed=191, mortar=(36, 40, 44))
    print(sorted(os.listdir(OUT)))
