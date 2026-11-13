"""Item background icons for Fish For Anything.
Each icon is a shaded, bevelled grey silhouette on transparency (so the game can tint it),
drawn at 4x and downsampled to 256x256."""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = 1024           # working size
OUT = 256          # final size
OUTDIR = "/home/claude/icons/out"
os.makedirs(OUTDIR, exist_ok=True)


# ------------------------------------------------------------------ geometry helpers
def P(x, y):
    """icon space is 0..256 -> working space"""
    return (x * S / 256, y * S / 256)


def lerp(a, b, t):
    return a + (b - a) * t


def thick_line(d, pts, w, fill=255):
    """polyline with round joints, w in icon units"""
    w4 = w * S / 256
    pp = [P(*p) for p in pts]
    d.line(pp, fill=fill, width=int(w4), joint="curve")
    r = w4 / 2
    for (x, y) in (pp[0], pp[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def tapered(d, pts, w0, w1, fill=255, steps=None):
    """polyline whose width tapers from w0 to w1 (icon units)"""
    # resample along length
    seg = []
    total = 0
    for a, b in zip(pts, pts[1:]):
        l = math.dist(a, b)
        seg.append((a, b, l))
        total += l
    n = steps or max(8, int(total / 2))
    acc = 0
    samples = []
    for a, b, l in seg:
        k = max(1, int(n * l / total))
        for i in range(k):
            t = i / k
            samples.append(((lerp(a[0], b[0], t), lerp(a[1], b[1], t)), (acc + l * t) / total))
        acc += l
    samples.append((pts[-1], 1.0))
    for (p, t) in samples:
        r = lerp(w0, w1, t) / 2 * S / 256
        x, y = P(*p)
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def circle(d, c, r, fill=255):
    x, y = P(*c)
    r = r * S / 256
    d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def ring(d, c, r, w, fill=255):
    x, y = P(*c)
    r = r * S / 256
    d.ellipse([x - r, y - r, x + r, y + r], outline=fill, width=int(w * S / 256))


def poly(d, pts, fill=255):
    d.polygon([P(*p) for p in pts], fill=fill)


def star_pts(c, r_out, r_in, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        a = math.radians(rot + i * 180 / n)
        r = r_out if i % 2 == 0 else r_in
        pts.append((c[0] + math.cos(a) * r, c[1] + math.sin(a) * r))
    return pts


def bezier(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]))
    return out


def mask():
    m = Image.new("L", (S, S), 0)
    return m, ImageDraw.Draw(m)


# ------------------------------------------------------------------ rendering
class Icon:
    def __init__(self):
        self.layers = []  # (mask, tone)

    def layer(self, tone):
        m, d = mask()
        self.layers.append((m, tone))
        return d

    def render(self, name):
        tone = np.zeros((S, S), np.float32)
        alpha = np.zeros((S, S), np.float32)
        for m, t in self.layers:
            a = np.asarray(m, np.float32) / 255
            tone = tone * (1 - a) + t * a
            alpha = np.maximum(alpha, a)
        amask = Image.fromarray((alpha * 255).astype(np.uint8))
        # bevel: light from the top-left
        blur = np.asarray(amask.filter(ImageFilter.GaussianBlur(14)), np.float32) / 255
        sh = 10
        up = np.roll(np.roll(blur, sh, 0), sh, 1)
        dn = np.roll(np.roll(blur, -sh, 0), -sh, 1)
        bevel = np.clip((up - dn) * 1.6, -0.5, 0.5)
        # soft top-to-bottom shade
        yy = np.linspace(1.08, 0.78, S, dtype=np.float32)[:, None]
        # internal layer edges read as seams
        edges = np.zeros((S, S), np.float32)
        for m, _ in self.layers[1:]:
            e = np.asarray(m.filter(ImageFilter.FIND_EDGES), np.float32) / 255
            edges = np.maximum(edges, e)
        edges = np.asarray(Image.fromarray((edges * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)), np.float32) / 255
        v = tone * yy + bevel * 0.55 - edges * 0.22
        # dark rim around the whole silhouette
        rim = np.asarray(amask.filter(ImageFilter.MinFilter(13)), np.float32) / 255
        v = np.where(rim < 0.5, v * 0.55, v)
        v = np.clip(v, 0, 1)
        rgb = (v * 255).astype(np.uint8)
        img = Image.merge("RGBA", (Image.fromarray(rgb),) * 3 + (amask,))
        img = img.resize((OUT, OUT), Image.LANCZOS)
        img.save(os.path.join(OUTDIR, name + ".png"))
        return img


# ------------------------------------------------------------------ shared rod parts
# rods run diagonally: butt bottom-left, tip top-right
BUTT, TIP = (46, 214), (214, 40)


def along(t, off=0):
    """point along the rod axis, with a perpendicular offset"""
    x = lerp(BUTT[0], TIP[0], t)
    y = lerp(BUTT[1], TIP[1], t)
    dx, dy = TIP[0] - BUTT[0], TIP[1] - BUTT[1]
    l = math.hypot(dx, dy)
    nx, ny = -dy / l, dx / l
    return (x + nx * off, y + ny * off)


def rod_base(ic, blank_w0=17, blank_w1=6, tone=0.86, grip_tone=0.62, reel_tone=0.7, guides=True, reel=True):
    d = ic.layer(tone)
    tapered(d, [along(0.22), along(1.0)], blank_w0, blank_w1)
    if guides:
        for t in (0.45, 0.62, 0.78, 0.92):
            a = along(t, 0)
            b = along(t, 13 - t * 5)
            thick_line(d, [a, b], 4)
            ring(d, b, 5 - t * 1.6, 3)
    g = ic.layer(grip_tone)
    tapered(g, [along(0.0), along(0.26)], 30, 24)
    if reel:
        r = ic.layer(reel_tone)
        c = along(0.2, 24)
        thick_line(r, [along(0.2, 6), c], 9)
        circle(r, c, 21)
        r2 = ic.layer(reel_tone * 0.72)
        circle(r2, c, 11)
        r3 = ic.layer(reel_tone * 1.15)
        circle(r3, c, 5)
        thick_line(r3, [c, (c[0] + 18, c[1] + 8)], 5)
        circle(r3, (c[0] + 19, c[1] + 9), 5.5)


def line_and_hook(ic, tone=0.9):
    d = ic.layer(tone)
    tip = along(1.0)
    thick_line(d, [tip, (tip[0], tip[1] + 70)], 2.6)
    # hook
    hx, hy = tip[0], tip[1] + 70
    pts = bezier((hx, hy), (hx, hy + 14), (hx - 14, hy + 14), (hx - 13, hy + 2), 20)
    thick_line(d, pts, 4.5)


# ------------------------------------------------------------------ rods
def bamboo():
    ic = Icon()
    d = ic.layer(0.84)
    tapered(d, [along(0.0), along(1.0)], 26, 10)
    n = ic.layer(0.62)
    for t in (0.14, 0.3, 0.46, 0.62, 0.78, 0.92):
        w = lerp(30, 12, t)
        thick_line(n, [along(t, -w / 2), along(t, w / 2)], 6)
    leaf = ic.layer(0.74)
    base = along(0.56, -6)
    pts = bezier(base, (base[0] - 40, base[1] - 30), (base[0] - 66, base[1] - 4), (base[0] - 70, base[1] + 6), 30)
    pts2 = bezier((base[0] - 70, base[1] + 6), (base[0] - 50, base[1] + 18), (base[0] - 20, base[1] + 14), base, 30)
    poly(leaf, pts + pts2)
    vein = ic.layer(0.56)
    thick_line(vein, bezier(base, (base[0] - 26, base[1] - 10), (base[0] - 48, base[1] - 2), (base[0] - 66, base[1] + 6), 20), 2)
    line_and_hook(ic)
    return ic


def driftwood():
    ic = Icon()
    d = ic.layer(0.78)
    path = [(44, 216), (70, 186), (82, 170), (104, 150), (118, 128), (142, 112), (160, 88), (186, 70), (214, 42)]
    tapered(d, path, 30, 9)
    # side twig
    tapered(d, [(118, 128), (106, 98), (96, 84)], 12, 5)
    tapered(d, [(160, 88), (176, 104), (196, 108)], 11, 5)
    k = ic.layer(0.56)
    for c, r in (((82, 170), 5), ((142, 112), 4.5), ((104, 150), 3)):
        ring(k, c, r, 2.4)
    grain = ic.layer(0.66)
    thick_line(grain, [(56, 206), (72, 186), (90, 166)], 2)
    thick_line(grain, [(124, 128), (150, 104), (168, 84)], 2)
    line_and_hook(ic)
    return ic


def fiberglass():
    ic = Icon()
    rod_base(ic, 15, 5, tone=0.92)
    w = ic.layer(0.72)
    for t in (0.3, 0.33):
        thick_line(w, [along(t, -6), along(t, 6)], 2.5)
    line_and_hook(ic)
    return ic


def carbon():
    ic = Icon()
    rod_base(ic, 14, 5, tone=0.55, grip_tone=0.48)
    hexes = ic.layer(0.74)
    for i in range(6):
        t = 0.03 + i * 0.038
        for o in (-4.5, 4.5):
            c = along(t + (0.019 if o > 0 else 0), o)
            poly(hexes, star_pts(c, 3.4, 3.4, 3, 0))
    stripe = ic.layer(0.85)
    for t in (0.5, 0.72):
        thick_line(stripe, [along(t, -5), along(t, 5)], 2.6)
    line_and_hook(ic)
    return ic


def coral():
    ic = Icon()
    rod_base(ic, 16, 6, tone=0.84)
    c = ic.layer(0.7)
    random.seed(4)

    def branch(p, ang, length, w, depth):
        if depth == 0 or length < 6:
            circle(c, p, w * 0.7)
            return
        q = (p[0] + math.cos(ang) * length, p[1] + math.sin(ang) * length)
        tapered(c, [p, q], w, w * 0.7)
        branch(q, ang - 0.5 + random.uniform(-0.15, 0.15), length * 0.72, w * 0.72, depth - 1)
        branch(q, ang + 0.45 + random.uniform(-0.15, 0.15), length * 0.68, w * 0.72, depth - 1)

    branch((150, 236), -math.pi / 2 - 0.1, 34, 12, 4)
    branch((188, 238), -math.pi / 2 + 0.25, 24, 9, 3)
    dots = ic.layer(0.9)
    for p in ((128, 170), (176, 160), (204, 186), (140, 196)):
        circle(dots, p, 3)
    line_and_hook(ic)
    return ic


def deepsea():
    ic = Icon()
    rod_base(ic, 20, 7, tone=0.7, reel_tone=0.82)
    a = ic.layer(0.82)
    cx, cy, k = 172, 162, 1.45
    def Q(x, y): return (cx + x * k, cy + y * k)
    ring(a, Q(0, -34), 7 * k, 4 * k)
    thick_line(a, [Q(0, -27), Q(0, 34)], 7 * k)
    thick_line(a, [Q(-16, -14), Q(16, -14)], 6 * k)
    thick_line(a, bezier(Q(-30, 10), Q(-26, 38), Q(26, 38), Q(30, 10), 30), 6.5 * k)
    poly(a, [Q(-36, 4), Q(-22, 6), Q(-31, 22)])
    poly(a, [Q(36, 4), Q(22, 6), Q(31, 22)])
    b = ic.layer(0.95)
    for p, r in (((86, 74), 9), ((108, 48), 7), ((72, 44), 5)):
        ring(b, p, r, 3)
    return ic


def golden():
    ic = Icon()
    rod_base(ic, 17, 6, tone=0.96, grip_tone=0.7)
    s = ic.layer(0.98)
    poly(s, star_pts((80, 76), 50, 21, 5))
    s2 = ic.layer(0.78)
    poly(s2, star_pts((80, 78), 24, 10, 5))
    sp = ic.layer(1.0)
    for c, r in (((176, 150), 12), ((140, 46), 9), ((206, 106), 7)):
        poly(sp, star_pts(c, r, r * 0.25, 4, -90))
    line_and_hook(ic)
    return ic


def miter_poly(center, widths):
    """polygon outline of a polyline with per-vertex widths and sharp (mitered) joints"""
    left, right = [], []
    n = len(center)
    for i, (p, w) in enumerate(zip(center, widths)):
        if i == 0:
            d = (center[1][0] - p[0], center[1][1] - p[1])
        elif i == n - 1:
            d = (p[0] - center[i - 1][0], p[1] - center[i - 1][1])
        else:
            a = (p[0] - center[i - 1][0], p[1] - center[i - 1][1])
            b = (center[i + 1][0] - p[0], center[i + 1][1] - p[1])
            la, lb = math.hypot(*a), math.hypot(*b)
            d = (a[0] / la + b[0] / lb, a[1] / la + b[1] / lb)
        l = math.hypot(*d)
        nx, ny = -d[1] / l, d[0] / l
        if 0 < i < n - 1:
            a = (p[0] - center[i - 1][0], p[1] - center[i - 1][1])
            la = math.hypot(*a)
            cosang = abs(nx * (-a[1] / la) + ny * (a[0] / la))
            w = w / max(cosang, 0.45)
        left.append((p[0] + nx * w / 2, p[1] + ny * w / 2))
        right.append((p[0] - nx * w / 2, p[1] - ny * w / 2))
    return left + right[::-1]


def stormcaller():
    ic = Icon()
    g = ic.layer(0.6)
    tapered(g, [along(0.0), along(0.2)], 30, 24)
    center = [along(0.18, 0), along(0.46, -20), along(0.5, 14), along(0.76, -12), along(0.8, 12), along(1.0, -4)]
    widths = [22, 20, 17, 13, 10, 2]
    bolt = ic.layer(0.9)
    poly(bolt, miter_poly(center, widths))
    core = ic.layer(1.0)
    poly(core, miter_poly(center[:-1] + [along(0.96, -2)], [6, 6, 5, 4, 3, 1]))
    base = ic.layer(0.72)
    circle(base, along(0.0), 21)
    base2 = ic.layer(0.5)
    circle(base2, along(0.0), 10)
    zap = ic.layer(0.85)
    for c in ((66, 70), (196, 178)):
        pts = [(c[0] - 10, c[1] - 18), (c[0] + 6, c[1] - 2), (c[0] - 4, c[1] + 2), (c[0] + 10, c[1] + 18)]
        poly(zap, miter_poly(pts, [7, 6, 6, 1]))
    return ic


def abyssal():
    ic = Icon()
    rod_base(ic, 17, 6, tone=0.62, reel_tone=0.6)
    t = ic.layer(0.82)
    # tentacle coiling up around the blank
    pts = []
    for i in range(80):
        k = i / 79
        p = along(0.12 + k * 0.62, math.sin(k * math.pi * 3.2) * 18 * (1 - k * 0.6))
        pts.append(p)
    tapered(t, pts, 22, 6)
    su = ic.layer(0.6)
    for i in range(4, 70, 9):
        k = i / 79
        p = along(0.12 + k * 0.62, math.sin(k * math.pi * 3.2) * 18 * (1 - k * 0.6))
        circle(su, p, lerp(4.5, 1.6, k))
    eye = ic.layer(0.95)
    circle(eye, (180, 180), 26)
    pupil = ic.layer(0.3)
    poly(pupil, [(180, 158), (188, 180), (180, 202), (172, 180)])
    return ic


def celestial():
    ic = Icon()
    rod_base(ic, 15, 5, tone=0.9)
    moon = ic.layer(0.96)
    m, md = mask()
    circle(md, (82, 80), 48)
    circle(md, (104, 64), 42, fill=0)
    moon_arr = np.asarray(m)
    ic.layers[-1] = (Image.fromarray(moon_arr), 0.96)
    st = ic.layer(1.0)
    for c, r in (((190, 160), 13), ((150, 196), 8), ((206, 118), 7), ((60, 140), 7)):
        poly(st, star_pts(c, r, r * 0.3, 4, -90))
    orbit = ic.layer(0.7)
    ring(orbit, (82, 80), 64, 3)
    circle(orbit, (136, 44), 8)
    line_and_hook(ic)
    return ic


def leviathan():
    ic = Icon()
    rod_base(ic, 17, 6, tone=0.8, grip_tone=0.55)
    s = ic.layer(0.7)
    # serpent body looping behind the rod
    body = bezier((40, 120), (70, 60), (150, 230), (200, 150), 60)
    tapered(s, body, 6, 20)
    head = ic.layer(0.76)
    poly(head, [(194, 132), (232, 140), (238, 158), (204, 172), (190, 160)])
    jaw = ic.layer(0.55)
    poly(jaw, [(206, 158), (238, 158), (210, 172)])
    eye = ic.layer(1.0)
    circle(eye, (212, 146), 4)
    fin = ic.layer(0.86)
    for (x, y) in ((88, 112), (120, 158), (156, 178)):
        poly(fin, [(x, y), (x + 8, y - 22), (x + 16, y + 2)])
    # trident tip
    tri = ic.layer(0.95)
    tip = along(1.0)
    thick_line(tri, [(tip[0] - 14, tip[1] + 6), (tip[0] + 2, tip[1] - 12), (tip[0] + 12, tip[1] + 10)], 4)
    poly(tri, [(tip[0] + 2, tip[1] - 26), (tip[0] - 4, tip[1] - 10), (tip[0] + 8, tip[1] - 10)])
    return ic


# ------------------------------------------------------------------ bait
def worm_shape(ic, tone, glow=False):
    if glow:
        g = ic.layer(0.62)
        for i in range(10):
            a = math.radians(i * 36 + 10)
            p0 = (128 + math.cos(a) * 84, 132 + math.sin(a) * 84)
            p1 = (128 + math.cos(a) * 106, 132 + math.sin(a) * 106)
            thick_line(g, [p0, p1], 5)
    w = ic.layer(tone)
    pts = []
    for i in range(90):
        k = i / 89
        pts.append((44 + k * 170, 136 + math.sin(k * math.pi * 2.4) * 38))
    tapered(w, pts, 26, 18)
    seg = ic.layer(tone * 0.72)
    for i in range(8, 86, 10):
        k = i / 89
        x, y = 44 + k * 170, 136 + math.sin(k * math.pi * 2.4) * 38
        dy = math.cos(k * math.pi * 2.4) * 38 * math.pi * 2.4 / 170
        nx, ny = -dy, 1
        l = math.hypot(nx, ny)
        nx, ny = nx / l * 10, ny / l * 10
        thick_line(seg, [(x - nx, y - ny), (x + nx, y + ny)], 2.6)
    band = ic.layer(tone * 1.12)
    k = 0.66
    x, y = 44 + k * 170, 136 + math.sin(k * math.pi * 2.4) * 38
    circle(band, (x, y), 15)
    eye = ic.layer(0.25)
    circle(eye, (44 + 6, 136 + 4), 3.2)


def bait_worm():
    ic = Icon()
    worm_shape(ic, 0.8)
    return ic


def bait_glow():
    ic = Icon()
    worm_shape(ic, 0.98, glow=True)
    return ic


def fish_shape(ic, tone, c=(124, 128), sc=1.0):
    b = ic.layer(tone)
    cx, cy = c
    top = bezier((cx - 70 * sc, cy), (cx - 40 * sc, cy - 46 * sc), (cx + 40 * sc, cy - 46 * sc), (cx + 66 * sc, cy), 30)
    bot = bezier((cx + 66 * sc, cy), (cx + 40 * sc, cy + 42 * sc), (cx - 40 * sc, cy + 42 * sc), (cx - 70 * sc, cy), 30)
    poly(b, top + bot)
    tail = ic.layer(tone * 0.8)
    poly(tail, [(cx - 62 * sc, cy), (cx - 100 * sc, cy - 36 * sc), (cx - 92 * sc, cy), (cx - 100 * sc, cy + 36 * sc)])
    fin = ic.layer(tone * 0.86)
    poly(fin, [(cx - 18 * sc, cy - 34 * sc), (cx + 6 * sc, cy - 60 * sc), (cx + 26 * sc, cy - 34 * sc)])
    gill = ic.layer(tone * 0.68)
    thick_line(gill, bezier((cx + 30 * sc, cy - 22 * sc), (cx + 22 * sc, cy - 6 * sc), (cx + 22 * sc, cy + 6 * sc), (cx + 30 * sc, cy + 20 * sc), 16), 4 * sc)
    eye = ic.layer(0.98)
    circle(eye, (cx + 44 * sc, cy - 8 * sc), 8 * sc)
    pup = ic.layer(0.2)
    circle(pup, (cx + 46 * sc, cy - 8 * sc), 4 * sc)


def bait_minnow():
    ic = Icon()
    fish_shape(ic, 0.84, (134, 128), 0.95)
    h = ic.layer(0.62)
    hx, hy = 150, 92
    thick_line(h, [(hx, 20), (hx, hy)], 2.5)
    thick_line(h, bezier((hx, hy), (hx, hy + 18), (hx - 16, hy + 18), (hx - 15, hy + 4), 16), 4)
    return ic


def bait_shrimp():
    ic = Icon()
    s = ic.layer(0.84)
    # curled body as a chain of shrinking segments along an arc
    segs = []
    for i in range(7):
        a = math.radians(200 - i * 34)
        r = 64 - i * 4
        c = (128 + math.cos(a) * r, 128 + math.sin(a) * r)
        segs.append((c, 26 - i * 2.4))
    for c, r in segs:
        circle(s, c, r)
    sh = ic.layer(0.66)
    for c, r in segs[1:]:
        circle(sh, c, r * 0.35)
    tail = ic.layer(0.74)
    c, r = segs[-1]
    poly(tail, [(c[0], c[1]), (c[0] + 26, c[1] - 30), (c[0] + 34, c[1] + 4)])
    ant = ic.layer(0.7)
    hc = segs[0][0]
    thick_line(ant, bezier(hc, (hc[0] - 10, hc[1] - 60), (hc[0] + 60, hc[1] - 110), (hc[0] + 120, hc[1] - 100), 30), 2.6)
    thick_line(ant, bezier(hc, (hc[0] - 20, hc[1] - 40), (hc[0] + 20, hc[1] - 96), (hc[0] + 80, hc[1] - 112), 30), 2.6)
    for i in range(4):
        x = hc[0] + 18 + i * 14
        thick_line(ant, [(x, hc[1] + 14), (x + 4, hc[1] + 34)], 3)
    eye = ic.layer(0.2)
    circle(eye, (hc[0] - 4, hc[1] - 6), 5)
    return ic


def clover(ic, c, r, tone):
    l = ic.layer(tone)
    for i in range(4):
        a = math.radians(45 + i * 90)
        tipd = r * 0.08
        for sgn in (-1, 1):
            b = a + sgn * math.radians(28)
            circle(l, (c[0] + math.cos(b) * r * 0.58, c[1] + math.sin(b) * r * 0.58), r * 0.3)
        # heart point toward the centre
        poly(l, [(c[0] + math.cos(a) * tipd, c[1] + math.sin(a) * tipd),
                 (c[0] + math.cos(a - 0.9) * r * 0.62, c[1] + math.sin(a - 0.9) * r * 0.62),
                 (c[0] + math.cos(a) * r * 0.6, c[1] + math.sin(a) * r * 0.6),
                 (c[0] + math.cos(a + 0.9) * r * 0.62, c[1] + math.sin(a + 0.9) * r * 0.62)])
    # cut gaps between the four leaflets
    m = ic.layers[-1][0]
    md = ImageDraw.Draw(m)
    for i in range(4):
        a = math.radians(i * 90)
        thick_line(md, [(c[0] + math.cos(a) * r * 0.12, c[1] + math.sin(a) * r * 0.12), (c[0] + math.cos(a) * r * 1.2, c[1] + math.sin(a) * r * 1.2)], max(4, r * 0.08), fill=0)
    v = ic.layer(tone * 0.68)
    for i in range(4):
        a = math.radians(45 + i * 90)
        thick_line(v, [(c[0] + math.cos(a) * r * 0.12, c[1] + math.sin(a) * r * 0.12), (c[0] + math.cos(a) * r * 0.62, c[1] + math.sin(a) * r * 0.62)], max(2, r * 0.045))
    st = ic.layer(tone * 0.8)
    tapered(st, bezier(c, (c[0] + r * 0.1, c[1] + r * 0.5), (c[0] + r * 0.3, c[1] + r * 0.8), (c[0] + r * 0.12, c[1] + r * 1.1), 20), r * 0.12, r * 0.07)


def bait_lucky():
    ic = Icon()
    clover(ic, (128, 112), 92, 0.84)
    return ic


def bait_golden():
    ic = Icon()
    s = ic.layer(0.95)
    poly(s, star_pts((128, 132), 104, 44, 5))
    s2 = ic.layer(0.78)
    poly(s2, star_pts((128, 134), 52, 22, 5))
    sp = ic.layer(1.0)
    for c, r in (((206, 50), 18), ((46, 210), 14), ((214, 196), 10)):
        poly(sp, star_pts(c, r, r * 0.24, 4, -90))
    return ic


# ------------------------------------------------------------------ chum (bucket + contents)
def bucket(ic, tone=0.76):
    b = ic.layer(tone)
    poly(b, [(54, 104), (202, 104), (184, 226), (72, 226)])
    rim = ic.layer(tone * 1.12)
    thick_line(rim, [(48, 104), (208, 104)], 14)
    bands = ic.layer(tone * 0.72)
    thick_line(bands, [(62, 150), (194, 150)], 6)
    thick_line(bands, [(68, 196), (188, 196)], 6)
    h = ic.layer(tone * 0.86)
    thick_line(h, bezier((52, 104), (52, 30), (204, 30), (204, 104), 30), 6)


def chum_basic():
    ic = Icon()
    bucket(ic)
    s = ic.layer(0.9)
    for c, r in (((96, 94), 16), ((126, 86), 20), ((160, 92), 16), ((112, 72), 11), ((146, 70), 10)):
        circle(s, c, r)
    d = ic.layer(0.66)
    for c in ((104, 90), (138, 80), (164, 96), (122, 74)):
        circle(d, c, 4)
    return ic


def chum_premium():
    ic = Icon()
    bucket(ic, 0.72)
    m = ic.layer(0.88)
    circle(m, (108, 80), 30)
    circle(m, (134, 92), 26)
    bone = ic.layer(1.0)
    thick_line(bone, [(140, 76), (196, 34)], 10)
    for c in ((196, 28), (204, 38)):
        circle(bone, c, 9)
    marb = ic.layer(0.68)
    thick_line(marb, bezier((92, 70), (104, 84), (120, 74), (130, 92), 16), 4)
    fishtail = ic.layer(0.8)
    poly(fishtail, [(72, 100), (40, 58), (60, 62), (54, 36), (86, 92)])
    return ic


def chum_lucky():
    ic = Icon()
    bucket(ic, 0.76)
    clover(ic, (128, 64), 58, 0.92)
    return ic


ICONS = {
    "rod_Bamboo": bamboo, "rod_Driftwood": driftwood, "rod_Fiberglass": fiberglass, "rod_Carbon": carbon,
    "rod_CoralReef": coral, "rod_DeepSea": deepsea, "rod_Golden": golden, "rod_Stormcaller": stormcaller,
    "rod_Abyssal": abyssal, "rod_Celestial": celestial, "rod_Leviathan": leviathan,
    "bait_Worm": bait_worm, "bait_Minnow": bait_minnow, "bait_Shrimp": bait_shrimp, "bait_GlowWorm": bait_glow,
    "bait_Lucky": bait_lucky, "bait_Golden": bait_golden,
    "chum_Basic": chum_basic, "chum_Premium": chum_premium, "chum_Lucky": chum_lucky,
}

if __name__ == "__main__":
    imgs = []
    for name, fn in ICONS.items():
        imgs.append((name, fn().render(name)))
    # contact sheet on a dark tile background for review
    cols = 6
    rows = math.ceil(len(imgs) / cols)
    sheet = Image.new("RGBA", (cols * 140, rows * 140), (16, 18, 27, 255))
    for i, (name, im) in enumerate(imgs):
        tile = Image.new("RGBA", (128, 128), (23, 26, 38, 255))
        small = im.resize((128, 128), Image.LANCZOS)
        tile.alpha_composite(small)
        sheet.alpha_composite(tile, ((i % cols) * 140 + 6, (i // cols) * 140 + 6))
    sheet.save("/home/claude/icons/sheet.png")
    print("done", len(imgs))
