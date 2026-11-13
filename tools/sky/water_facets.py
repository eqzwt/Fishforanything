# tileable low-poly "facet sheen" for the crisp water surface: white triangles with soft alpha
import numpy as np, random
from PIL import Image, ImageDraw
N, G = 512, 8                      # 8x8 jittered grid on a torus -> seamless
rnd = random.Random(42)
cell = N / G
pts = {(i, j): (i * cell + rnd.uniform(-0.3, 0.3) * cell, j * cell + rnd.uniform(-0.3, 0.3) * cell) for i in range(G) for j in range(G)}
def P(i, j):
    x, y = pts[(i % G, j % G)]
    return x + (i // G) * N if i >= 0 else x - N, y + (j // G) * N if j >= 0 else y - N
img = Image.new("RGBA", (N * 3, N * 3), (255, 255, 255, 0))
d = ImageDraw.Draw(img, "RGBA")
alphas = {}
for i in range(G):
    for j in range(G):
        for k in range(2):
            r = rnd.random()
            alphas[(i, j, k)] = 0 if r < 0.45 else int(rnd.uniform(18, 70) if r < 0.9 else rnd.uniform(80, 120))
for oi in (-1, 0, 1):
    for oj in (-1, 0, 1):
        for i in range(G):
            for j in range(G):
                def q(a, b):
                    x, y = pts[((i + a) % G, (j + b) % G)]
                    x += ((i + a) // G) * N; y += ((j + b) // G) * N
                    return (x + (oi + 1) * N, y + (oj + 1) * N)
                a, b, c, e = q(0, 0), q(1, 0), q(1, 1), q(0, 1)
                for k, tri in enumerate(((a, b, c), (a, c, e))):
                    al = alphas[(i, j, k)]
                    if al: d.polygon(tri, fill=(255, 255, 255, al))
out = img.crop((N, N, 2 * N, 2 * N))
out.save("/mnt/user-data/outputs/ffa_water_facets.png")
print(out.size)
