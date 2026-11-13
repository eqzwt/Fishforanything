import numpy as np
from PIL import Image
import sys
sys.path.insert(0, "/home/claude/meshkit")
import landgen as L
n = 1024
u = (np.arange(n) + 0.5) / n * 2 - 1
U, V = np.meshgrid(u, u)
one = np.ones_like(U)
FACES = {"Ft": (U, -V, -one), "Bk": (-U, -V, one), "Lf": (one, -V, U), "Rt": (-one, -V, -U), "Up": (-V, one, -U), "Dn": (U, -one, -V)}
for name, (X, Y, Z) in FACES.items():
    d = np.stack([X, Y, Z], -1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    x, y, z = d[..., 0], d[..., 1], d[..., 2]
    e = np.clip(y, -1, 1)
    zen = np.array([62, 122, 206.0]); mid = np.array([110, 165, 226.0]); hor = np.array([184, 212, 236.0])
    t = np.clip(e, 0, 1)
    col = hor + (mid - hor) * (np.clip(t / 0.35, 0, 1) ** 0.8)[..., None]
    col = col + (zen - col) * (np.clip((t - 0.35) / 0.65, 0, 1) ** 1.2)[..., None]
    col[e < 0] = hor * 0.92
    # soft clouds on a virtual plane above (continuous across faces)
    k = 1.0 / (np.maximum(y, 0.02) + 0.18)
    px, pz = x * k * 220, z * k * 220
    c = L.fbm(px, pz, 5, 140, 300) + 0.35 * L.fbm(px * 2.3, pz * 2.3, 3, 90, 400)
    cover = np.clip((c - 0.06) * 4.5, 0, 1) ** 1.6
    cover *= np.clip(y * 5, 0, 1) * (0.55 + 0.45 * np.clip(1 - y, 0, 1))  # thin near zenith/horizon
    shade = 0.82 + 0.18 * np.clip(L.fbm(px + 40, pz + 40, 3, 60, 500) * 3 + 0.5, 0, 1)
    cloud = np.array([246, 248, 252.0]) * shade[..., None]
    col = col * (1 - cover[..., None] * 0.85) + cloud * cover[..., None] * 0.85
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(f"/mnt/user-data/outputs/daysky_{name}.png")

def disc(path, size, core, glow, color, craters=False):
    yy, xx = (np.mgrid[0:size, 0:size] + 0.5) / size * 2 - 1
    r = np.sqrt(xx * xx + yy * yy)
    a = np.clip((core - r) / 0.02, 0, 1)
    g = np.exp(-((r / glow) ** 2)) * 0.55
    alpha = np.clip(a + g * (1 - a), 0, 1)
    col = np.zeros((size, size, 3)) + np.array(color, float)
    if craters:
        rr = np.random.default_rng(4)
        sh = np.ones((size, size))
        for _ in range(26):
            cx, cy, cr = rr.uniform(-0.8, 0.8) * core, rr.uniform(-0.8, 0.8) * core, rr.uniform(0.04, 0.16) * core
            dd = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            sh -= 0.13 * np.exp(-((dd / cr) ** 2) * 2)
        sh -= 0.12 * np.clip(xx * 0.6 + yy * 0.3, 0, 1)  # soft terminator
        col = col * np.clip(sh, 0.5, 1)[..., None]
    img = np.dstack([col, alpha * 255]).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(path)

disc("/mnt/user-data/outputs/fx_sun.png", 256, 0.32, 0.85, (255, 244, 214))
disc("/mnt/user-data/outputs/fx_moon.png", 256, 0.62, 0.95, (226, 232, 246), craters=True)

# shoreline foam strip: tiles along U, soft fade across V (shore side bright)
W, H = 512, 128
xx = np.arange(W)[None, :] / W
yy = np.arange(H)[:, None] / H
f = L.fbm(xx * 64 * np.ones((H, 1)), yy * 16 * np.ones((1, W)), 4, 6, 600)
f2 = L.fbm(xx * 128 * np.ones((H, 1)) + 7, yy * 32 * np.ones((1, W)), 3, 5, 700)
# make U periodic by blending the end into the start
blend = np.clip((xx - 0.85) / 0.15, 0, 1)
f = f * (1 - blend) + np.roll(f, -int(W * 0.85), axis=1) * blend
lace = np.clip((f + 0.5 * f2 + 0.1) * 3.2, 0, 1)
edge = np.exp(-((yy - 0.25) / 0.16) ** 2)       # bright foam line
fade = np.clip(1 - yy, 0, 1) ** 1.5
a = np.clip(edge * 0.95 + lace * 0.6 * fade, 0, 1) * np.clip(yy / 0.05, 0, 1)
img = np.dstack([np.full((H, W), 255), np.full((H, W), 255), np.full((H, W), 255), a * 255]).astype(np.uint8)
Image.fromarray(img, "RGBA").save("/mnt/user-data/outputs/fx_foam_strip.png")

# underwater light shaft: soft streaks, fade at both ends
W, H = 256, 512
xx = np.arange(W)[None, :] / W
yy = np.arange(H)[:, None] / H
streak = np.zeros(W)
r = np.random.default_rng(8)
for fq in (3, 5, 9, 14, 23):
    streak += np.sin(2 * np.pi * fq * np.arange(W) / W + r.uniform(0, 6.28)) / fq ** 0.5
streak = (streak - streak.min()) / (streak.max() - streak.min())
a = (streak[None, :] ** 2) * np.sin(np.pi * xx) ** 1.5 * (1 - yy) ** 1.4 * np.clip(yy / 0.08, 0, 1)
img = np.dstack([np.full((H, W), 255), np.full((H, W), 255), np.full((H, W), 255), np.clip(a, 0, 1) * 255]).astype(np.uint8)
Image.fromarray(img, "RGBA").save("/mnt/user-data/outputs/fx_lightshaft.png")
# preview
prev = Image.new("RGB", (1024, 512))
row = ["Rt", "Ft", "Lf", "Bk"]
for i, nme in enumerate(row):
    prev.paste(Image.open(f"/mnt/user-data/outputs/daysky_{nme}.png").resize((256, 256)), (i * 256, 256))
prev.paste(Image.open("/mnt/user-data/outputs/daysky_Up.png").resize((256, 256)), (256, 0))
prev.save("/home/claude/sky/dayprev.png")
print("ok")
