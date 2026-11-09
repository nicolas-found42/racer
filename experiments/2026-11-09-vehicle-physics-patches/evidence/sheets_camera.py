import sys, os
from PIL import Image, ImageDraw
S = sys.argv[1]
SHOTS = S + '/cam/shots'
names = {0: "Acura NSX '04", 2: "Mustang '73", 7: "Dodge RAM", 16: "Juiced 2 CCX"}
cars = [0, 2, 7, 16]

def sheet(scenarios, out, w=504, h=279, variants=('before', 'after')):
    pad = 8
    label = 110
    cols = [(s, v) for s in scenarios for v in variants]
    W = label + len(cols) * (w + pad) + pad
    H = 30 + len(cars) * (h + pad) + pad
    im = Image.new('RGB', (W, H), (20, 20, 24))
    d = ImageDraw.Draw(im)
    for j, (s, v) in enumerate(cols):
        d.text((label + j * (w + pad), 10), f"{s} - {v}", fill=(230, 230, 230))
    for i, c in enumerate(cars):
        y = 30 + i * (h + pad)
        d.text((6, y + h // 2), names[c], fill=(230, 230, 230))
        for j, (s, v) in enumerate(cols):
            f = f"{SHOTS}/{v}-c{c}-{s}.ppm"
            if os.path.exists(f):
                t = Image.open(f).convert('RGB').resize((w, h), Image.LANCZOS)
                im.paste(t, (label + j * (w + pad), y))
    im.save(f"{S}/cam/{out}", quality=88)

sheet(['cruise', 'brake'], 'sheet-chase.jpg')
sheet(['launch', 'slide'], 'sheet-smoke.jpg')
sheet(['donut', 'slide2'], 'sheet-stress.jpg', variants=('after',))
print('ok')
