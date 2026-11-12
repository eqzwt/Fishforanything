"""Sharp lightning textures for the Stormcaller rod.
zap_glow.png  - beam profile (constant along U): razor core + tight halo, for procedural zap chains.
zap_sheet.png - 2x2 flipbook of thin branching micro-zaps, drawn at 4x and downsampled for crisp edges."""
import math, random, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def glow():
    W, H = 32, 128
    y = np.abs(np.arange(H) - (H - 1) / 2)
    a = np.clip(np.clip(1.6 - y / 1.2, 0, 1) + np.exp(-y / 7.0) * 0.55 + np.exp(-(y / 26.0) ** 2) * 0.18, 0, 1)
    arr = np.zeros((H, W, 4), np.uint8); arr[..., :3] = 255; arr[..., 3] = (a[:, None] * 255).astype(np.uint8)
    Image.fromarray(arr, "RGBA").save("tex/zap_glow.png")

def sheet(seed=23):
    R = random.Random(seed)
    def bolt(d, x0, y0, x1, y1, w, depth, S):
        pts = [(x0, y0)]; n = 8
        dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
        for i in range(1, n):
            t = i / n; off = R.uniform(-1, 1) * L * 0.1
            pts.append((x0 + dx * t + nx * off, y0 + dy * t + ny * off))
        pts.append((x1, y1))
        d.line(pts, fill=255, width=max(1, int(w * S)), joint="curve")
        if depth > 0:
            for i in range(2, n - 1):
                if R.random() < 0.5:
                    px, py = pts[i]; ang = math.atan2(dy, dx) + R.choice([-1, 1]) * R.uniform(0.4, 0.9)
                    l2 = L * R.uniform(0.2, 0.38)
                    bolt(d, px, py, px + math.cos(ang) * l2, py + math.sin(ang) * l2, w * 0.6, depth - 1, S)
    S, cell = 4, 256
    out = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    for k in range(4):
        big = Image.new("L", (cell * S, cell * S), 0); d = ImageDraw.Draw(big)
        c = cell * S / 2; ang = R.uniform(0, math.pi); r = cell * S * 0.43
        bolt(d, c - math.cos(ang) * r, c - math.sin(ang) * r, c + math.cos(ang) * r, c + math.sin(ang) * r, 3.2, 2, S)
        core = big.resize((cell, cell), Image.LANCZOS)
        ca = np.asarray(core).astype(float) / 255
        ga = np.clip(np.asarray(core.filter(ImageFilter.GaussianBlur(2.5))).astype(float) / 255 * 1.6
                     + np.asarray(core.filter(ImageFilter.GaussianBlur(7))).astype(float) / 255 * 1.4, 0, 1)
        alpha = np.clip(ca + ga * 0.8, 0, 1)
        rgb = np.zeros((cell, cell, 3))
        rgb[..., 0] = 255 * np.clip(ca + ga * 0.55, 0, 1); rgb[..., 1] = 255 * np.clip(ca + ga * 0.85, 0, 1); rgb[..., 2] = 255
        out.paste(Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA"), ((k % 2) * cell, (k // 2) * cell))
    out.save("tex/zap_sheet.png")

if __name__ == "__main__":
    os.makedirs("tex", exist_ok=True); glow(); sheet()
