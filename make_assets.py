"""FubarXS brand assets for the desktop app: main-button gradient (normal, hover), stop button and Ko-fi mug icons.
Usage: python3 make_assets.py <icons folder>"""
import sys
from PIL import Image, ImageDraw, ImageEnhance

W, H, R = 420, 84, 14  # drawn at 2x for the 210x42 button


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rounded(img):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=R, fill=255)
    out = img.convert("RGBA")
    out.putalpha(m)
    return out


def gradient(c1, c2):  # 135 degrees like the CSS: #c71d06 -> #fe5505
    g = Image.new("RGB", (W, H))
    px, a, b = g.load(), rgb(c1), rgb(c2)
    for y in range(H):
        for x in range(W):
            t = (x + y) / (W + H - 2)
            px[x, y] = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return g


def kofi(stroke, heart):  # own mug-with-heart icon, not the official Ko-fi logo
    k = 8
    im = Image.new("RGBA", (24 * k, 24 * k), (0, 0, 0, 0))
    d, w = ImageDraw.Draw(im), int(1.7 * k)
    d.rounded_rectangle([4 * k, 8.5 * k, 16 * k, 20 * k], radius=5 * k, corners=(False, False, True, True), outline=stroke, width=w)
    d.line([(16 * k, 10 * k), (17.4 * k, 10 * k)], fill=stroke, width=w)
    d.arc([14.8 * k, 10 * k, 20 * k, 15.2 * k], -90, 90, fill=stroke, width=w)
    d.line([(17.4 * k, 15.2 * k), (16 * k, 15.2 * k)], fill=stroke, width=w)
    for cx in (8.9, 11.1):
        d.ellipse([(cx - 1.3) * k, 12.1 * k, (cx + 1.3) * k, 14.7 * k], fill=heart)
    d.polygon([(7.7 * k, 13.9 * k), (12.3 * k, 13.9 * k), (10 * k, 17.5 * k)], fill=heart)
    return im.resize((48, 48), Image.LANCZOS)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    g = gradient("#c71d06", "#fe5505")
    rounded(g).save(f"{out}/btn_gradient.png")
    rounded(ImageEnhance.Brightness(g).enhance(1.12)).save(f"{out}/btn_gradient_hover.png")
    rounded(Image.new("RGB", (W, H), rgb("#c71d06"))).save(f"{out}/btn_stop.png")
    kofi("#a89c95", "#fe5505").save(f"{out}/kofi.png")
    kofi("#f4ede7", "#ffc233").save(f"{out}/kofi_hover.png")
    print("assets ->", out)
