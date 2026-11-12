"""Procedural VFX textures for Fish For Anything rods. All drawn from scratch.
White/greyscale textures are meant to be tinted by ParticleEmitter/Beam colour."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = "/home/claude/vfx/tex/"
rng = random.Random(11)


def save(img, name):
    img.save(OUT + name)
    print("saved", name, img.size)


def glow_layer(size, draw_fn, blur):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def compose(size, layers):
    base = Image.new("RGBA", size, (0, 0, 0, 0))
    for l in layers:
        base.alpha_composite(l)
    return base


def radial(size, inner=0.0, power=2.0):
    h, w = size[1], size[0]
    y, x = np.mgrid[0:h, 0:w]
    cx, cy = (w - 1) / 2, (h - 1) / 2
    r = np.sqrt(((x - cx) / (w / 2)) ** 2 + ((y - cy) / (h / 2)) ** 2)
    return np.clip(1 - (r - inner) / (1 - inner), 0, 1) ** power


def from_alpha(a, rgb=(255, 255, 255)):
    a = np.clip(a, 0, 1)
    arr = np.zeros(a.shape + (4,), dtype=np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = rgb
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def value_noise(w, h, scale, seed, octaves=4):
    r = np.random.RandomState(seed)
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(scale * 2 ** o))
        g = r.rand(s + 1, s + 1)
        g[:, -1] = g[:, 0]  # tile horizontally
        g[-1, :] = g[0, :]
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += np.asarray(img) / 255 * amp
        tot += amp
        amp *= 0.5
    return out / tot


# 1) energy flow: tileable horizontal streaks for beams running along the rod
def energy_flow():
    w, h = 512, 64
    n = value_noise(w, h, 3, 1)
    y = np.linspace(-1, 1, h)[:, None]
    core = np.exp(-(y / 0.18) ** 2)
    halo = np.exp(-(y / 0.55) ** 2) * 0.45
    x = np.linspace(0, 1, w)[None, :]
    pulses = 0.55 + 0.45 * np.sin(x * math.pi * 2 * 4) ** 2  # 4 bright packets per tile
    streak = np.clip(n * 1.6 - 0.35, 0, 1)
    a = (core * (0.55 + 0.45 * streak) + halo * streak) * pulses
    save(from_alpha(a * 1.15), "energy_flow.png")


# 2) lightning: jagged branching bolt across the texture, glowing core
def lightning():
    w, h = 512, 128
    def bolt(d, x0, y0, x1, y1, width, depth):
        pts = [(x0, y0)]
        segs = 18
        for i in range(1, segs):
            t = i / segs
            pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + rng.uniform(-22, 22) * (1 - abs(t - 0.5))))
        pts.append((x1, y1))
        d.line(pts, fill=(255, 255, 255, 255), width=width, joint="curve")
        if depth > 0:
            for _ in range(2):
                i = rng.randrange(3, segs - 3)
                bx, by = pts[i]
                bolt(d, bx, by, bx + rng.uniform(40, 110), by + rng.uniform(-40, 40), max(1, width - 2), depth - 1)
    glow = glow_layer((w, h), lambda d: bolt(d, 0, h / 2, w, h / 2, 14, 1), 10)
    rng.seed(11)
    core = glow_layer((w, h), lambda d: bolt(d, 0, h / 2, w, h / 2, 5, 1), 0.6)
    save(compose((w, h), [glow, glow, core]), "lightning.png")


# 3) magic circle with runes (spins around the reel)
def rune_circle(name="rune_circle.png", seed=3, spokes=8):
    S = 512
    r = random.Random(seed)
    def draw(d):
        c = S / 2
        for rad, wdt in ((246, 6), (226, 3), (160, 4), (148, 2), (70, 3)):
            d.ellipse([c - rad, c - rad, c + rad, c + rad], outline=(255, 255, 255, 255), width=wdt)
        # rune glyphs between the outer rings
        for i in range(24):
            a = i / 24 * math.tau
            gx, gy = c + math.cos(a) * 236 * 0.92, c + math.sin(a) * 236 * 0.92
            pts = []
            for k in range(r.randint(3, 5)):
                pts.append((gx + r.uniform(-9, 9), gy + r.uniform(-9, 9)))
            d.line(pts, fill=(255, 255, 255, 255), width=3)
        # star polygon
        pts = [(c + math.cos(i / spokes * math.tau * 3) * 160, c + math.sin(i / spokes * math.tau * 3) * 160) for i in range(spokes + 1)]
        d.line(pts, fill=(255, 255, 255, 230), width=3)
        for i in range(spokes):
            a = i / spokes * math.tau
            d.line([(c + math.cos(a) * 70, c + math.sin(a) * 70), (c + math.cos(a) * 148, c + math.sin(a) * 148)], fill=(255, 255, 255, 200), width=2)
            d.ellipse([c + math.cos(a) * 160 - 9, c + math.sin(a) * 160 - 9, c + math.cos(a) * 160 + 9, c + math.sin(a) * 160 + 9], outline=(255, 255, 255, 255), width=3)
    glow = glow_layer((S, S), draw, 7)
    sharp = glow_layer((S, S), draw, 0.5)
    save(compose((S, S), [glow, sharp]), name)


# 4) flame flipbook 4x4 (128px frames): teardrop flame, flickering tongues rising
def flame_sheet():
    F, N = 128, 4
    sheet = Image.new("RGBA", (F * N, F * N), (0, 0, 0, 0))
    big = value_noise(F, F * 8, 3, 7, 5)
    y, x = np.mgrid[0:F, 0:F]
    xn = (x - F / 2) / (F / 2)
    up = 1 - y / F  # 0 bottom .. 1 top
    for i in range(16):
        t = i / 16
        off = int(t * F * 4)
        n = big[F * 4 - off:F * 4 - off + F, :] if off else big[F * 4:F * 5, :]
        sway = (n - 0.5) * 0.9 * up ** 1.2
        h = np.clip((up - 0.04) / 0.9, 0, 1)
        half = 0.62 * np.sin(np.pi * np.clip(h * 0.8 + 0.2, 0, 1)) ** 0.9 * (1 - h) ** 0.35
        half = np.maximum(half, 1e-3)
        d = np.abs(xn - sway) / half
        a = np.clip(1 - d, 0, 1) ** 0.9 * (h > 0)
        a *= np.clip(up * 6, 0, 1)
        a *= 0.55 + 0.7 * n
        core = np.clip(1 - d * 1.8, 0, 1) * np.clip(1 - h * 1.6, 0, 1)
        life = 0.75 + 0.25 * math.sin(t * math.tau)
        frame = from_alpha(np.clip((a + core * 0.6) * life, 0, 1))
        sheet.paste(frame, ((i % N) * F, (i // N) * F))
    save(sheet, "flame_sheet.png")


# 5) soft orb with a hot core
def orb():
    S = 256
    a = radial((S, S), 0, 2.6) * 0.75 + radial((S, S), 0.55, 1.2) * 0.6
    save(from_alpha(np.clip(a, 0, 1)), "orb_glow.png")


# 6) shockwave ring
def ring():
    S = 512
    y, x = np.mgrid[0:S, 0:S]
    r = np.sqrt((x - S / 2) ** 2 + (y - S / 2) ** 2) / (S / 2)
    a = np.exp(-((r - 0.86) / 0.05) ** 2) + np.exp(-((r - 0.86) / 0.16) ** 2) * 0.35
    a *= (r < 1)
    save(from_alpha(np.clip(a, 0, 1)), "ring.png")


# 7) bubble (coloured, not tinted)
def bubble():
    S = 128
    y, x = np.mgrid[0:S, 0:S]
    r = np.sqrt((x - S / 2) ** 2 + (y - S / 2) ** 2) / (S / 2 - 2)
    rim = np.clip((r - 0.72) / 0.28, 0, 1) ** 2 * (r <= 1)
    fill = 0.18 * (r <= 1)
    a = np.clip(rim + fill, 0, 1)
    img = from_alpha(a, (200, 240, 255))
    d = ImageDraw.Draw(img)
    d.ellipse([34, 26, 58, 46], fill=(255, 255, 255, 235))
    d.ellipse([78, 84, 88, 94], fill=(255, 255, 255, 140))
    save(img, "bubble.png")


# 8) leaf (coloured)
def leaf():
    S = 128
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = []
    for i in range(41):
        t = i / 40
        pts.append((14 + t * 100, 64 - math.sin(t * math.pi) * 34))
    for i in range(41):
        t = 1 - i / 40
        pts.append((14 + t * 100, 64 + math.sin(t * math.pi) * 26))
    d.polygon(pts, fill=(120, 205, 90, 255))
    d.line([(14, 64), (114, 62)], fill=(70, 150, 60, 255), width=3)
    for k in range(5):
        x = 30 + k * 16
        d.line([(x, 63), (x + 12, 63 - 18)], fill=(80, 160, 65, 255), width=2)
        d.line([(x, 63), (x + 12, 63 + 14)], fill=(80, 160, 65, 255), width=2)
    save(img, "leaf.png")


# 9) trail streaks (u along length, v across)
def trail():
    w, h = 256, 64
    n = value_noise(w, h, 6, 21, 3)
    y = np.linspace(-1, 1, h)[:, None]
    lines = np.zeros((h, w))
    for k in range(7):
        yy = rng.uniform(-0.7, 0.7)
        lines += np.exp(-((y - yy) / 0.05) ** 2) * rng.uniform(0.4, 1)
    a = (np.exp(-(y / 0.6) ** 2) * 0.45 + lines * 0.7) * (0.6 + 0.6 * n)
    save(from_alpha(np.clip(a, 0, 1)), "trail_streaks.png")


# 10) nebula smoke puff
def nebula():
    S = 256
    n = value_noise(S, S, 3, 33, 6)
    a = np.clip(n * 1.8 - 0.55, 0, 1) * radial((S, S), 0, 1.4)
    save(from_alpha(np.clip(a * 1.5, 0, 1)), "nebula.png")


# 11) spark streak (for VelocityParallel)
def spark():
    w, h = 64, 256
    x = np.linspace(-1, 1, w)[None, :]
    y = np.linspace(0, 1, h)[:, None]
    a = np.exp(-(x / 0.18) ** 2) * (y ** 1.5) * np.clip((1 - y) * 12, 0, 1)
    a += np.exp(-(x / 0.5) ** 2) * (y ** 3) * 0.3
    save(from_alpha(np.clip(a * 1.2, 0, 1)), "spark_streak.png")


# 12) spiral swirl (vortex / black hole)
def swirl():
    S = 512
    y, x = np.mgrid[0:S, 0:S]
    dx, dy = (x - S / 2) / (S / 2), (y - S / 2) / (S / 2)
    r = np.sqrt(dx ** 2 + dy ** 2) + 1e-6
    th = np.arctan2(dy, dx)
    arms = 3
    v = np.cos(arms * th + 7 * np.log(r)) * 0.5 + 0.5
    a = v ** 3 * np.clip(1 - r, 0, 1) ** 0.8 * np.clip(r * 3, 0, 1)
    a += np.exp(-(r / 0.12) ** 2) * 0.5
    save(from_alpha(np.clip(a * 1.3, 0, 1)), "swirl.png")


# 13) sunburst rays
def sunburst():
    S = 512
    y, x = np.mgrid[0:S, 0:S]
    dx, dy = (x - S / 2) / (S / 2), (y - S / 2) / (S / 2)
    r = np.sqrt(dx ** 2 + dy ** 2) + 1e-6
    th = np.arctan2(dy, dx)
    rays = (np.cos(th * 12) * 0.5 + 0.5) ** 6 + (np.cos(th * 12 + math.pi) * 0.5 + 0.5) ** 14 * 0.6
    a = rays * np.clip(1 - r, 0, 1) ** 1.5 + np.exp(-(r / 0.22) ** 2)
    save(from_alpha(np.clip(a, 0, 1)), "sunburst.png")


# 14) glyph sheet 4x4 for floating rune particles (Flipbook Random)
def glyphs():
    F, N = 128, 4
    sheet = Image.new("RGBA", (F * N, F * N), (0, 0, 0, 0))
    r = random.Random(5)
    for i in range(16):
        layer = Image.new("RGBA", (F, F), (0, 0, 0, 0))
        def draw(d):
            c = F / 2
            d.ellipse([c - 50, c - 50, c + 50, c + 50], outline=(255, 255, 255, 255), width=4)
            for _ in range(3):
                pts = [(c + r.uniform(-32, 32), c + r.uniform(-32, 32)) for _ in range(r.randint(2, 4))]
                d.line(pts, fill=(255, 255, 255, 255), width=6)
            if r.random() < 0.5:
                d.ellipse([c - 8, c - 8, c + 8, c + 8], fill=(255, 255, 255, 255))
        g = glow_layer((F, F), draw, 5)
        r.seed(5 + i * 31)
        s = glow_layer((F, F), draw, 0.4)
        r.seed(5 + (i + 1) * 31)
        frame = compose((F, F), [g, s])
        sheet.paste(frame, ((i % N) * F, (i // N) * F))
    save(sheet, "glyph_sheet.png")


# 15) water droplet (coloured)
def droplet():
    S = 128
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = []
    for i in range(60):
        t = i / 59 * math.tau
        rx = 30 * math.sin(t)
        ry = -40 * math.cos(t) if math.cos(t) > 0 else -28 * math.cos(t)
        k = (1 - math.cos(t)) / 2
        pts.append((64 + rx * (k ** 0.6), 72 + ry))
    d.polygon(pts, fill=(110, 205, 255, 230))
    d.ellipse([52, 74, 64, 90], fill=(255, 255, 255, 220))
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    save(img, "droplet.png")


for fn in (energy_flow, lightning, rune_circle, flame_sheet, orb, ring, bubble, leaf, trail, nebula, spark, swirl, sunburst, glyphs, droplet):
    fn()
rune_circle("rune_circle2.png", seed=9, spokes=7)
