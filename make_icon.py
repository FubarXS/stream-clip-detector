"""
FubarXS brand kit - generátor ikony rozšíření.

Použití:  python3 make_icon.py <výstupní_složka> [bone|heat]

  bone (výchozí) - černá dlaždice, horní půlkruh magma, dolní kostní bílá.
                   Hlavní logo doplňků.
  heat           - černá dlaždice, horní půlkruh žlutá→oranž, dolní červená
                   ("tón v tónu"). Alternativa, v malých velikostech slabší.

Pro nový doplněk vyměň jen funkci draw_glyph(): dlaždice, přechody a barvy
zůstávají stejné.
"""
import math
import sys
from PIL import Image, ImageDraw, ImageFilter

S = 512
SIZES = [16, 32, 48, 96, 128]
TILE = "#0a0706"

VARIANTS = {
    "heat": {"top": ("#ffc233", "#ff5a0a"), "bottom": ("#c71d06", "#ee3a08")},
    "bone": {"top": ("#e32805", "#fe5505"), "bottom": ("#f4ede7", "#f4ede7")},
}
# tvar symbolu (zesílený kvůli čitelnosti v 16 px)
RADIUS, THICK, ARROW = 160, 54, 72


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hgradient(c1, c2):
    """Vodorovný přechod; teče ve směru šipky."""
    g = Image.new("RGB", (S, S))
    px = g.load()
    a, b = rgb(c1), rgb(c2)
    for x in range(S):
        t = x / (S - 1)
        col = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
        for y in range(S):
            px[x, y] = col
    return g


def arc_mask(start, end):
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    cx = cy = S / 2
    d.arc([cx - RADIUS, cy - RADIUS, cx + RADIUS, cy + RADIUS], start=start, end=end, fill=255, width=THICK)
    ang = math.radians(end)
    tip = (cx + RADIUS * math.cos(ang), cy + RADIUS * math.sin(ang))
    tan = ang + math.pi / 2
    back = (tip[0] - ARROW * 1.15 * math.cos(ang), tip[1] - ARROW * 1.15 * math.sin(ang))
    p1 = (tip[0] + ARROW * .55 * math.cos(tan) - ARROW * .15 * math.cos(ang),
          tip[1] + ARROW * .55 * math.sin(tan) - ARROW * .15 * math.sin(ang))
    p2 = (tip[0] - ARROW * .55 * math.cos(tan) - ARROW * .15 * math.cos(ang),
          tip[1] - ARROW * .55 * math.sin(tan) - ARROW * .15 * math.sin(ang))
    d.polygon([p1, back, p2], fill=255)
    return m


def glyph_masks():
    """Clip symbol: play triangle (gradient, moves right) + a cut bar in bone white."""
    tri = Image.new("L", (S, S), 0)
    ImageDraw.Draw(tri).polygon([(120, 118), (120, 394), (338, 256)], fill=255)
    tri = tri.filter(ImageFilter.GaussianBlur(10)).point(lambda p: 255 if p > 128 else 0)  # soft corners
    bar = Image.new("L", (S, S), 0)
    ImageDraw.Draw(bar).rounded_rectangle([372, 118, 424, 394], radius=10, fill=255)
    return tri, bar


def build(variant):
    v = VARIANTS[variant]
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    tile_mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(tile_mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=96, fill=255)
    img.paste(Image.new("RGB", (S, S), rgb(TILE)), (0, 0), tile_mask)
    # glyph for Stream Clip Detector (the kit's sync symbol replaced; tile and colors unchanged)
    tri, bar = glyph_masks()
    img.paste(hgradient(*v["top"]), (0, 0), tri)
    img.paste(hgradient(*v["bottom"]), (0, 0), bar)
    return img


def main(out, variant="bone"):
    img = build(variant)
    for s in SIZES:
        img.resize((s, s), Image.LANCZOS).save(f"{out}/icon{s}.png")
    img.save(f"{out}/app.ico", sizes=[(16, 16), (32, 32), (48, 48), (128, 128), (256, 256)])
    print(f"ikony ({variant}) ->", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".", sys.argv[2] if len(sys.argv) > 2 else "bone")
