"""Brick land for Fish For Anything: the current island heightfield rebuilt as studded 8x8 brick columns
(like the original lego map), in darker, muted colours. Same logic is ported to Luau (MapTools.BrickLand)."""
import colorsys, json
import numpy as np
from PIL import Image
from landgen import height, fbm

CELL = 8
X0, X1, Z0, Z1 = -504, 504, -376, 600
nx, nz = (X1 - X0) // CELL, (Z1 - Z0) // CELL

# base colours (the old lego map's own palette), darkened + desaturated below
BASE = {
    "grass1": (75, 160, 75), "grass2": (58, 138, 64), "grass3": (110, 190, 80), "grass4": (42, 116, 58), "lime": (164, 196, 72),
    "sand": (242, 214, 134), "sand2": (236, 210, 140), "sandwet": (226, 192, 112), "dirt": (176, 124, 82), "dirt2": (156, 108, 72),
    "rock": (150, 150, 156), "rock2": (118, 118, 126), "moss": (98, 124, 84),
    "sea1": (78, 186, 182), "sea2": (44, 128, 176), "sea3": (30, 84, 146), "sea4": (22, 48, 104),
}
def darken(c, v=0.8, s=0.86):
    h, ss_, vv = colorsys.rgb_to_hsv(*[x / 255 for x in c])
    r, g, b = colorsys.hsv_to_rgb(h, ss_ * s, vv * v)
    return tuple(int(round(x * 255)) for x in (r, g, b))
PAL = {k: darken(v) for k, v in BASE.items()}
PAL["grass3"], PAL["lime"] = (86, 134, 70), (116, 136, 66)  # pulled down a notch (less toy-like)
PAL["rock"], PAL["rock2"] = (124, 121, 115), (99, 96, 91)  # warmer grey (no purple cast under blue sky)
NAMES = list(PAL)

def quant(h, pd):
    if h >= 0:
        step = 1 if (pd < 5 or h < 10) else (2 if h < 26 else 4)
        t = round(h / step) * step
        return max(t, 1)
    step = 1 if h > -10 else (2 if h > -30 else 4)
    t = round(h / step) * step
    return min(t, -1)

def build():
    cx = X0 + CELL / 2 + np.arange(nx) * CELL
    cz = Z0 + CELL / 2 + np.arange(nz) * CELL
    GX, GZ = np.meshgrid(cx, cz, indexing="ij")
    H, K, PD = height(GX, GZ)
    N = fbm(GX, GZ, 2, 40, 77)
    top = np.vectorize(quant)(H, PD).astype(int)
    pad = np.pad(top, 1, mode="edge")
    nb = np.stack([pad[2:, 1:-1], pad[:-2, 1:-1], pad[1:-1, 2:], pad[1:-1, :-2]])
    diff = np.max(np.abs(nb - top[None]), axis=0)
    nbmin = np.min(nb, axis=0)
    nbmax = np.max(nb, axis=0)
    col = np.empty(top.shape, object)
    for i in range(nx):
        for j in range(nz):
            t, k, pd, n, d = top[i, j], K[i, j], PD[i, j], N[i, j], diff[i, j]
            rise = nbmax[i, j] - t  # how much higher the tallest neighbour is (a riser below a ledge)
            if t < 0:
                c = "sandwet" if t >= -1 else "sea1" if t >= -5 else "sea2" if t >= -15 else "sea3" if t >= -39 else "sea4"
            elif (k == 3 and rise >= 6) or (k == 2 and rise >= 6) or (k == 3 and t <= 3):
                c = "rock" if (n > 0 or t % 8 < 4) else "rock2"
            elif k == 3:
                c = "moss" if n > 0.06 else "grass4" if n > -0.06 else "grass2"
            elif t <= 1:
                c = "sandwet" if (i + j) % 3 else "sand2"
            elif t <= 2 and k in (1, 4):
                c = "sand" if (i * 7 + j) % 4 else "sand2"
            elif pd < 3.5 and k <= 2:
                c = "dirt" if (i + j) % 2 else "dirt2"
            elif k == 2:
                c = "grass4" if n < -0.08 else "grass2" if n < 0.08 else "grass1"
            else:
                c = "grass3" if n > 0.12 else "lime" if n > 0.09 else "grass1" if n > -0.06 else "grass2"
            col[i, j] = c
    bottom = np.minimum(top, nbmin) - 2
    # greedy merge: same top+colour, land up to 2x2 cells (16 studs, like the old map), seabed up to 4x4
    used = np.zeros(top.shape, bool)
    boxes = []
    for i in range(nx):
        for j in range(nz):
            if used[i, j]:
                continue
            t, c = top[i, j], col[i, j]
            lim = 2 if t > 0 else (4 if t > -16 else 8)
            w = 1
            while w < lim and i + w < nx and not used[i + w, j] and top[i + w, j] == t and col[i + w, j] == c:
                w += 1
            hgt = 1
            while hgt < lim and j + hgt < nz and all(not used[i + a, j + hgt] and top[i + a, j + hgt] == t and col[i + a, j + hgt] == c for a in range(w)):
                hgt += 1
            used[i:i + w, j:j + hgt] = True
            b = int(bottom[i:i + w, j:j + hgt].min())
            boxes.append((X0 + i * CELL, Z0 + j * CELL, w * CELL, hgt * CELL, b, int(t), NAMES.index(c)))
    return top, col, boxes

if __name__ == "__main__":
    top, col, boxes = build()
    land = sum(1 for b in boxes if b[5] > 0)
    print("boxes", len(boxes), "land", land, "sea", len(boxes) - land, "top range", top.min(), top.max())
    img = np.zeros((nz, nx, 3), np.uint8)
    for i in range(nx):
        for j in range(nz):
            c = np.array(PAL[col[i, j]], float)
            shade = 0.85 + 0.15 * np.clip(top[i, j] / 40, -1, 1)
            img[nz - 1 - j, i] = np.clip(c * shade, 0, 255)
    Image.fromarray(img).resize((nx * 6, nz * 6), Image.NEAREST).save("/tmp/brick_preview.png")
    json.dump({"pal": PAL, "names": NAMES}, open("/tmp/brick_pal.json", "w"))
    print(PAL)
