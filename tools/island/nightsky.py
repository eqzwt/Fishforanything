import numpy as np
from PIL import Image
n = 1024
rng = np.random.default_rng(3)
u = (np.arange(n) + 0.5) / n * 2 - 1
U, V = np.meshgrid(u, u)
one = np.ones_like(U)
# slot -> direction for image pixel (U right, V down); verified in-game
FACES = {
    "Ft": (U, -V, -one),        # -Z
    "Bk": (-U, -V, one),        # +Z
    "Lf": (one, -V, U),         # +X side uses the Lf slot
    "Rt": (-one, -V, -U),       # -X side uses the Rt slot
    "Up": (-V, one, -U),
    "Dn": (U, -one, -V),
}

def per(x, freqs, seed):
    """periodic 1D noise in angle x (radians) from random sinusoids"""
    r = np.random.default_rng(seed)
    out = np.zeros_like(x)
    tot = 0
    for f in freqs:
        a = 1.0 / f ** 0.6
        out += a * np.sin(f * x + r.uniform(0, 6.283))
        tot += a
    return out / tot

def sky(d):
    x, y, z = d[..., 0], d[..., 1], d[..., 2]
    el = np.arcsin(np.clip(y, -1, 1))            # elevation
    az = np.arctan2(x, -z)                        # 0 = toward -Z (north over the bay), + toward +X
    e = np.clip(el / (np.pi / 2), -1, 1)
    # base gradient: teal-blue horizon glow -> deep navy zenith
    hz = np.exp(-np.maximum(e, 0) * 5.0)
    col = np.zeros(d.shape)
    zen = np.array([5, 9, 26.0]); mid = np.array([12, 24, 56.0]); hor = np.array([34, 58, 96.0])
    col = zen + (mid - zen) * (1 - np.clip(e, 0, 1))[..., None] ** 2 + (hor - mid) * hz[..., None] * 0.9
    below = e < 0
    col[below] = (hor * 0.55)  # below horizon (rarely seen)
    # milky way: faint broad band tilted across the sky
    mw_axis = np.array([0.35, 0.55, 0.76]); mw_axis /= np.linalg.norm(mw_axis)
    dist = np.abs(d @ mw_axis)
    mw = np.exp(-(dist / 0.18) ** 2) * (0.6 + 0.4 * per(az * 3 + el * 5, [3, 7, 13, 29], 9))
    col += mw[..., None] * np.array([18, 22, 38.0]) * (e > 0)[..., None]
    # aurora curtains: three bands arcing over the northern sky
    aur = np.zeros(d.shape)
    bands = [  # (centre az, half-width az, base elevation, wobble, height, seed, colour low, colour high, strength)
        (0.15, 1.6, 0.36, 0.12, 0.75, 11, (70, 255, 170), (150, 80, 235), 1.0),
        (-0.8, 1.0, 0.62, 0.10, 0.55, 23, (60, 230, 235), (190, 90, 240), 0.8),
        (1.1, 0.9, 0.22, 0.07, 0.40, 37, (90, 255, 140), (70, 150, 255), 0.65),
        (2.6, 0.7, 0.75, 0.08, 0.35, 53, (80, 240, 200), (140, 100, 255), 0.45),
    ]
    for c_az, w_az, base, wob, hgt, seed, clo, chi, s in bands:
        da = np.angle(np.exp(1j * (az - c_az)))
        span = np.exp(-(da / w_az) ** 4)
        b = base + wob * per(az * 1.0, [1, 2, 3, 5], seed) + 0.04 * per(az, [9, 15], seed + 1)
        t = (el - b) / hgt
        rays = 0.45 + 0.55 * np.clip(per(az * 1.0 + 0.15 * t, [37, 61, 97, 151, 233], seed + 2) * 1.6 + 0.4, 0, 1)
        fold = 0.6 + 0.4 * per(az, [6, 11], seed + 3)
        up = np.where(t >= 0, np.clip(1 - t, 0, 1) ** 1.6, np.exp(-(t / 0.06) ** 2))
        inten = span * up * rays * fold * s * (el > 0)
        mixk = np.clip(t, 0, 1)[..., None]
        ccol = np.array(clo, float) * (1 - mixk) + np.array(chi, float) * mixk
        # bright lower edge
        edge = np.exp(-(t / 0.05) ** 2) * span * rays * s
        aur += ccol * inten[..., None] * 0.85 + np.array(clo, float) * edge[..., None] * 0.5
    col = col + aur
    # stars
    return col

def stars(img_faces):
    N = 5200
    dirs = rng.normal(size=(N, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    dirs = dirs[dirs[:, 1] > -0.02]
    mag = rng.power(6, len(dirs))  # mostly faint
    tint = rng.choice([0, 1, 2], len(dirs), p=[0.7, 0.2, 0.1])
    tints = np.array([[255, 255, 255], [200, 220, 255], [255, 236, 200]], float)
    for d, m, t in zip(dirs, mag, tint):
        x, y, z = d
        a = np.abs(d)
        if a[2] >= a[0] and a[2] >= a[1]:
            if z < 0: face, s = "Ft", -1 / z; Uc, Vc = x * s, -y * s
            else: face, s = "Bk", 1 / z; Uc, Vc = -x * s, -y * s
        elif a[0] >= a[1]:
            if x > 0: face, s = "Lf", 1 / x; Uc, Vc = z * s, -y * s
            else: face, s = "Rt", -1 / x; Uc, Vc = -z * s, -y * s
        else:
            if y > 0: face, s = "Up", 1 / y; Uc, Vc = -z * s, -x * s
            else: continue
        px, py = (Uc + 1) / 2 * n, (Vc + 1) / 2 * n
        img = img_faces[face]
        r = 0.6 + 1.3 * m
        bright = (0.35 + 0.65 * m ** 2) * 255
        x0, x1 = int(max(px - 3, 0)), int(min(px + 4, n))
        y0, y1 = int(max(py - 3, 0)), int(min(py + 4, n))
        if x1 <= x0 or y1 <= y0: continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        g = np.exp(-(((xx + 0.5 - px) ** 2 + (yy + 0.5 - py) ** 2) / (r * r)))
        # fade stars near the horizon
        k = np.clip(y * 6, 0, 1)
        img[y0:y1, x0:x1] += g[..., None] * tints[t] * (bright / 255) * k

faces = {}
for name, (X, Y, Z) in FACES.items():
    d = np.stack([X, Y, Z], -1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    faces[name] = sky(d)
stars(faces)
for name, img in faces.items():
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(f"/mnt/user-data/outputs/nightsky_{name}.png")
# preview: horizontal strip Rt(-X) | Ft(-Z) | Lf(+X) | Bk(+Z) with Up above Ft
prev = Image.new("RGB", (n * 4 // 4, n * 2 // 4))
row = [faces["Rt"], faces["Ft"], faces["Lf"], faces["Bk"]]
for i, f in enumerate(row):
    prev.paste(Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).resize((n // 4, n // 4)), (i * n // 4, n // 4))
prev.paste(Image.fromarray(np.clip(faces["Up"], 0, 255).astype(np.uint8)).resize((n // 4, n // 4)), (n // 4, 0))
prev.save("/home/claude/sky/preview.png")
print("done")
