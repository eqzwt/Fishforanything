import math
from PIL import Image, ImageDraw, ImageFilter, ImageChops
W, H = 768, 256
S = 2  # supersample
def fish_mask(scale=1.0):
    img = Image.new("L", (W*S, H*S), 0)
    d = ImageDraw.Draw(img)
    cx, cy = 330*S, 128*S
    # body: smooth lens/teardrop facing right
    pts = []
    for i in range(181):
        t = i / 180 * math.pi
        x = cx + math.cos(math.pi - t) * 250*S
        k = math.sin(t)
        # fuller near head (right), thinner at tail (left)
        fat = (0.55 + 0.45 * (1 - (math.cos(math.pi - t) + 1) / 2) ** 0.7)
        pts.append((x, cy - k * 92*S * fat))
    for i in range(181):
        t = (180 - i) / 180 * math.pi
        x = cx + math.cos(math.pi - t) * 250*S
        k = math.sin(t)
        fat = (0.55 + 0.45 * (1 - (math.cos(math.pi - t) + 1) / 2) ** 0.7)
        pts.append((x, cy + k * 84*S * fat))
    d.polygon(pts, fill=255)
    # tail fin (left)
    tx = cx - 235*S
    d.polygon([(tx + 30*S, cy), (tx - 70*S, cy - 95*S), (tx - 45*S, cy), (tx - 70*S, cy + 95*S)], fill=255)
    # dorsal + belly fins
    d.polygon([(cx - 90*S, cy - 70*S), (cx - 20*S, cy - 125*S), (cx + 70*S, cy - 86*S)], fill=255)
    d.polygon([(cx - 40*S, cy + 65*S), (cx + 10*S, cy + 108*S), (cx + 50*S, cy + 72*S)], fill=255)
    return img
m = fish_mask()
# eye hole + gill cut (transparent so it reads at any fill level)
cut = Image.new("L", m.size, 0); cd = ImageDraw.Draw(cut)
cx, cy = 330*S, 128*S
cd.ellipse([cx + 160*S, cy - 40*S, cx + 190*S, cy - 10*S], fill=255)
cd.arc([cx + 60*S, cy - 70*S, cx + 140*S, cy + 70*S], 120, 240, fill=255, width=7*S)
m = ImageChops.subtract(m, cut)
m = m.resize((W, H), Image.LANCZOS)
sil = Image.new("RGBA", (W, H), (255, 255, 255, 0)); sil.putalpha(m)
sil.save("tex/fish_silhouette.png")
# outline: dilate - original
big = m.filter(ImageFilter.MaxFilter(9))
edge = ImageChops.subtract(big, m.filter(ImageFilter.MinFilter(3)))
out = Image.new("RGBA", (W, H), (255, 255, 255, 0)); out.putalpha(edge)
out.save("tex/fish_outline.png")
prev = Image.new("RGBA", (W, H), (30, 60, 120, 255)); prev.alpha_composite(sil); prev.alpha_composite(out); prev.save("p_fish.png")
print("ok")
