"""Compile the rendered floor plans into one brochure-ready PDF.

Run after plans.py:  python3 tools/floorplans/compile.py assets/floorplans
Writes <dir>/auraya-floor-plans.pdf: a cover, then one A3 landscape page per villa
(ground, second floor and rooftop side by side), at 200 dpi.
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FONTS = os.path.join(ROOT, "assets", "fonts")
DPI = 200
PW, PH = int(420 / 25.4 * DPI), int(297 / 25.4 * DPI)  # A3 landscape
PAPER, INK, SOFT, GOLD = (250, 247, 236), (62, 45, 30), (111, 100, 80), (167, 139, 95)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def centred(dr, y, text, f, fill):
    w = dr.textlength(text, font=f)
    dr.text(((PW - w) / 2, y), text, font=f, fill=fill)


def cover():
    page = Image.new("RGB", (PW, PH), PAPER)
    dr = ImageDraw.Draw(page)
    logo = Image.open(os.path.join(ROOT, "assets", "logo-brown.webp")).convert("RGBA")
    logo.thumbnail((int(PW * 0.22), int(PH * 0.22)), Image.LANCZOS)
    page.paste(logo, ((PW - logo.width) // 2, int(PH * 0.22)), logo)
    y = int(PH * 0.22) + logo.height + 120
    centred(dr, y, "FLOOR PLANS", font("cinzel-latin.woff2", 150), INK)
    centred(dr, y + 210, "Villas A1 – A4  ·  Uluwatu, Bali", font("jost-latin.woff2", 64), SOFT)
    dr.line([(PW / 2 - 220, y + 330), (PW / 2 + 220, y + 330)], fill=GOLD, width=4)
    centred(dr, y + 380, "Ground floor  ·  Second floor  ·  Rooftop", font("jost-latin.woff2", 48), SOFT)
    centred(dr, PH - 170, "Indicative plans based on the architect's design development drawings of 05.01.2026. "
            "Dimensions in millimetres.", font("jost-latin.woff2", 34), SOFT)
    return page


def villa_page(board_path, n):
    page = Image.new("RGB", (PW, PH), PAPER)
    dr = ImageDraw.Draw(page)
    dr.text((140, 110), f"VILLA A{n}", font=font("cinzel-latin.woff2", 96), fill=INK)
    sub = "Ground floor  ·  Second floor  ·  Rooftop"
    f = font("jost-latin.woff2", 44)
    dr.text((PW - 140 - dr.textlength(sub, font=f), 140), sub, font=f, fill=SOFT)
    dr.line([(140, 250), (PW - 140, 250)], fill=GOLD, width=3)
    board = Image.open(board_path).convert("RGB")
    board.thumbnail((PW - 280, PH - 250 - 200), Image.LANCZOS)
    page.paste(board, ((PW - board.width) // 2, 290 + (PH - 290 - 170 - board.height) // 2))
    f2 = font("jost-latin.woff2", 32)
    foot = f"Auraya Villas  ·  Villa A{n}  ·  Indicative, design development 05.01.2026  ·  Dimensions in mm"
    dr.text((140, PH - 120), foot, font=f2, fill=SOFT)
    return page


def main(folder):
    pages = [cover()]
    for n in (1, 2, 3, 4):
        pages.append(villa_page(os.path.join(folder, "hires", f"villa-a{n}-all-floors.jpg"), n))
    out = os.path.join(folder, "auraya-floor-plans.pdf")
    pages[0].save(out, save_all=True, append_images=pages[1:], resolution=DPI, quality=90)
    print("wrote", out, f"{os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets", "floorplans"))
