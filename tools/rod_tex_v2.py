"""Textures for the 5 new rods (Driftwood, Coral Reef, Stormcaller, Celestial, Leviathan's Wrath).
Writes cloud, planet_ring, seashell, raindrop, star4, sand PNGs into ./tex. Mostly white so ParticleEmitters can tint them."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def cloud():
    W, H = 512, 320
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for x, y, s in [(140,190,90),(240,150,115),(350,175,95),(420,210,70),(90,225,60),(250,225,95),(330,235,80)]:
        d.ellipse([x-s, y-s, x+s, y+s], fill=(255,255,255,255))
    a = np.asarray(img.filter(ImageFilter.GaussianBlur(2))).astype(float)
    shade = 1 - 0.35*np.clip((np.linspace(0,1,H)[:,None]-0.45)/0.55, 0, 1)
    for i in range(3): a[..., i] *= shade
    Image.fromarray(a.astype(np.uint8), "RGBA").save("tex/cloud.png")

def planet():
    S = 256; c = S/2
    img = Image.new("RGBA", (S,S), (0,0,0,0))
    rb = Image.new("RGBA", (S,S), (0,0,0,0)); ImageDraw.Draw(rb).ellipse([c-118,c-30,c+118,c+30], outline=(255,255,255,200), width=10)
    img.alpha_composite(rb)
    body = Image.new("RGBA", (S,S), (0,0,0,0)); ImageDraw.Draw(body).ellipse([c-70,c-70,c+70,c+70], fill=(255,255,255,255))
    ba = np.asarray(body).astype(float); y, x = np.mgrid[0:S,0:S]
    band = 0.82 + 0.18*np.sin((y-c)/9.0)
    light = np.clip(1.1 - ((x-c+30)**2 + (y-c+30)**2)**0.5/140, 0.45, 1)
    for i in range(3): ba[..., i] *= band*light
    img.alpha_composite(Image.fromarray(ba.astype(np.uint8), "RGBA"))
    fr = Image.new("RGBA", (S,S), (0,0,0,0)); ImageDraw.Draw(fr).arc([c-118,c-30,c+118,c+30], 0, 180, fill=(255,255,255,235), width=10)
    img.alpha_composite(fr); img.save("tex/planet_ring.png")

def seashell():
    S = 128; img = Image.new("RGBA", (S,S), (0,0,0,0)); d = ImageDraw.Draw(img); cx, cy = 64, 80
    for i in range(9):
        a0 = math.radians(200 + i*15.5); pts = [(cx,cy)]
        for t in range(9):
            aa = a0 + math.radians(15.5)*t/8; pts.append((cx+math.cos(aa)*56, cy+math.sin(aa)*56))
        d.polygon(pts, fill=(255,215-i*4,190-i*6,255) if i % 2 == 0 else (250,185,160,255))
    for i in range(10):
        aa = math.radians(200 + i*15.5); d.line([(cx,cy),(cx+math.cos(aa)*56, cy+math.sin(aa)*56)], fill=(205,140,120,255), width=2)
    d.rounded_rectangle([cx-16,cy-4,cx+16,cy+14], radius=6, fill=(240,180,150,255))
    img.filter(ImageFilter.GaussianBlur(0.6)).save("tex/seashell.png")

def raindrop():
    W, H = 64, 256; img = Image.new("RGBA", (W,H), (0,0,0,0)); d = ImageDraw.Draw(img)
    for y in range(H):
        t = y/H; w = 2 + 4*t; d.line([(W/2-w/2,y),(W/2+w/2,y)], fill=(255,255,255,int(255*t**1.4)))
    d.ellipse([W/2-7,H-18,W/2+7,H-2], fill=(255,255,255,255))
    img.filter(ImageFilter.GaussianBlur(1.2)).save("tex/raindrop.png")

def star():
    S = 256; c = (S-1)/2; y, x = np.mgrid[0:S,0:S]; dx, dy = np.abs(x-c), np.abs(y-c); r = np.sqrt(dx**2+dy**2)
    spike = np.exp(-dy/2.2)*np.exp(-dx/45) + np.exp(-dx/2.2)*np.exp(-dy/45)
    a = np.clip((spike + np.exp(-(r/30)**2))*np.clip(1-r/126, 0, 1), 0, 1)
    arr = np.zeros((S,S,4), np.uint8); arr[..., :3] = 255; arr[..., 3] = (a*255).astype(np.uint8)
    Image.fromarray(arr, "RGBA").save("tex/star4.png")

def sand():
    S = 128; img = Image.new("RGBA", (S,S), (0,0,0,0)); d = ImageDraw.Draw(img); R = random.Random(7)
    for _ in range(26):
        px, py, s = R.uniform(10,118), R.uniform(10,118), R.uniform(2,5)
        d.ellipse([px-s,py-s,px+s,py+s], fill=(255,255,255,R.randint(160,255)))
    img.filter(ImageFilter.GaussianBlur(0.7)).save("tex/sand.png")

if __name__ == "__main__":
    import os; os.makedirs("tex", exist_ok=True)
    for f in (cloud, planet, seashell, raindrop, star, sand): f()
