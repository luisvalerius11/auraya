"""Definitions for every villa and floor, and the build driver.

Coordinates are PDF points on the A3 sheets of the architect's PDF
(2026_0109 Villa Matteo Luas Bangunan, drawing date 05.01.2026).
Villas 1-3 sit on a 7.5 m module (212.6 pt at 1:100), so most of Villa 1's and 3's
zones are Villa 2's shifted; pools and gardens differ and are defined per villa.

Zone forms:
  (material, x, y)            seed: the region under the point (pools, rugs, skylights)
  (material, x0, y0, x1, y1)  every region whose centroid falls inside; first match wins
Regions enclosed by furniture lines become furniture automatically.
"""
import os
import sys
import pymupdf as fitz
from PIL import Image, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from render import Plan, frame  # noqa: E402

MODULE = 212.6
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FONTS = os.path.join(ROOT, "assets", "fonts")

CLIPS = {1: (55, 100, 372, 508), 2: (362, 100, 586, 508), 3: (575, 100, 799, 508), 4: (790, 172, 1068, 595)}
AREAS = {  # built area per floor (m²), from the drawing sheets
    1: (104.825, 68.265, 49.32, 222.41), 2: (95.175, 68.265, 49.32, 212.76),
    3: (89.625, 68.265, 49.32, 207.21), 4: (87.885, 68.265, 49.32, 205.47),
}
FLOORS = [("ground", "Ground Floor", 0), ("second", "Second Floor", 1), ("rooftop", "Rooftop", 2)]


def shift(zones, labels, dx):
    z2 = []
    for z in zones:
        if len(z) == 3:
            z2.append((z[0], z[1] + dx, z[2]))
        else:
            z2.append((z[0], z[1] + dx, z[2], z[3] + dx, z[4]) + tuple(z[5:]))
    l2 = [dict(l, at=(l["at"][0] + dx, l["at"][1])) for l in labels]
    return z2, l2


def L(name, x, y, sub="", **kw):
    return dict(name=name, at=(x, y), sub=sub, **kw)


# ---------------- Villa 2 (template for the 7.5 m module) ----------------
V2_GF_HOUSE = [
    ("rug", 410, 278),
    ("furn:walnut", 370, 365, 392, 435), ("furn:walnut", 419, 413, 447, 436), ("furn:walnut", 490, 413, 516, 436),
    ("terrazzo", 364, 225, 405, 262),
    ("travertine_out", 405, 225, 586, 262),
    ("terrazzo", 364, 432, 442, 466),
    ("stair", 442, 432, 500, 466),
    ("travertine", 364, 262, 586, 466),
    ("pavers", 362, 466, 586, 508, "edge"),
]
V2_GF_HOUSE_LABELS = [
    L("Shower", 391, 243), L("Terrace", 500, 246),
    L("Living", 548, 330, "25 m²"), L("Dining + Kitchen", 440, 407, "15 m²"),
    L("Powder", 398, 447, "3 m²"), L("Parking", 474, 488),
]
V2_2F = [
    ("furn", 441, 265), ("furn", 530, 265), ("travertine", 440, 302), ("travertine", 520, 302),
    ("furn", 398, 318, 426, 342), ("furn", 521, 318, 558, 342),
    ("furn:walnut", 398, 318, 426, 342), ("furn:walnut", 521, 318, 558, 342),
    ("terrazzo", 400, 331, 476, 405, "paint"), ("terrazzo", 477, 331, 551, 405, "paint"),
    ("travertine", 364, 222, 586, 404), ("travertine", 364, 404, 586, 436), ("stair", 364, 436, 586, 466),
]
V2_2F_LABELS = [
    L("Bedroom", 422, 266, "14 m²"), L("Bedroom", 530, 266, "14 m²"),
    L("Bathroom", 437, 368, "6 m²"), L("Bathroom", 526, 368, "6 m²"), L("Hallway", 476, 420),
]
V2_RT = [
    ("water", 406, 268), ("glass", 489, 420), ("furn:teak", 441, 348),
    ("planting", 486, 218, 586, 258), ("travertine_out", 364, 218, 586, 404),
    ("travertine_out", 364, 404, 400, 436), ("stair", 364, 436, 586, 466),
]
V2_RT_LABELS = [L("Rooftop", 535, 330, "33 m²"), L("Jacuzzi", 406, 268, light=True), L("Skylight", 489, 418)]


def villa_123(n):
    dx = (n - 2) * MODULE
    gf, gfl = shift(V2_GF_HOUSE, V2_GF_HOUSE_LABELS, dx)
    if n == 1:
        # keep the rug and joinery (first 4), replace V2's shower/terrace (next 2) with Villa 1's own
        gf = [("water", 206, 165)] + gf[:4] + [
            ("terrazzo", 157, 222, 195, 256), ("travertine_out", 195, 215, 372, 256),
            ("travertine_out", 300, 100, 372, 222), ("travertine_out", 108, 100, 302, 214),
            ("planting", 120, 300), ("planting", 130, 215),
        ] + gf[6:]
        gfl = [L("Pool", 206, 163, "15 m²", light=True), L("Sunbed", 336, 172, "8 m²"),
               L("Shower", 178, 240), L("Terrace", 290, 246)] + gfl[2:]
    elif n == 2:
        gf = [("water", 448, 175), ("travertine_out", 512, 100, 586, 226), ("planting", 362, 100, 382, 226),
              ("travertine_out", 380, 100, 515, 226)] + gf
        gfl = [L("Pool", 448, 178, "11 m²", light=True), L("Sunbed", 550, 175, "7 m²")] + gfl
    else:
        gf = [("water", 660, 182), ("travertine_out", 728, 100, 799, 226), ("planting", 575, 100, 594, 226),
              ("travertine_out", 592, 100, 731, 226)] + gf
        gfl = [L("Pool", 662, 180, "7 m²", light=True), L("Sunbed", 763, 190, "5 m²")] + gfl
    f2, f2l = shift(V2_2F, V2_2F_LABELS, dx)
    rt, rtl = shift(V2_RT, V2_RT_LABELS, dx)
    return [(gf, gfl), (f2, f2l), (rt, rtl)]


def villa_4():
    gf = [
        ("furn:walnut", 797, 435, 820, 503), ("furn:walnut", 845, 478, 870, 503), ("furn:walnut", 905, 478, 930, 503),
        ("water", 860, 255), ("rug", 832, 345), ("planting", 1030, 450),
        ("terrazzo", 800, 296, 830, 333), ("travertine_out", 830, 292, 1003, 333),
        ("travertine_out", 912, 172, 1020, 294), ("travertine_out", 795, 172, 915, 294),
        ("planting", 1000, 172, 1068, 568, "edge"),
        ("terrazzo", 800, 502, 868, 532), ("stair", 868, 502, 975, 532),
        ("travertine", 797, 333, 1003, 532), ("pavers", 797, 532, 1003, 568, "edge"), ("pavers", 797, 531, 1001, 567, "paint"),
        ("planting", 790, 568, 1068, 595, "edge"),
    ]
    gfl = [L("Pool", 860, 256, "6 m²", light=True), L("Sunbed", 965, 268, "6 m²"),
           L("Shower", 815, 312), L("Terrace", 925, 314),
           L("Living", 968, 378, "25 m²"), L("Dining", 972, 442, "+ Kitchen · 15 m²"),
           L("Powder", 834, 518, "3 m²"), L("Parking", 900, 550)]
    f2 = [("furn", 864, 330), ("furn", 955, 330), ("travertine", 864, 365), ("travertine", 955, 365),
          ("furn", 824, 392, 852, 412), ("furn", 949, 392, 977, 412),
          ("furn:walnut", 824, 392, 852, 412), ("furn:walnut", 949, 392, 977, 412),
          ("terrazzo", 826, 403, 901, 472, "paint"), ("terrazzo", 902, 403, 977, 472, "paint"),
          ("travertine", 797, 292, 1006, 472), ("travertine", 797, 472, 1006, 501), ("stair", 797, 501, 1006, 532)]
    f2l = [L("Bedroom", 850, 322, "14 m²"), L("Bedroom", 955, 322, "14 m²"),
           L("Bathroom", 864, 425, "6 m²"), L("Bathroom", 940, 425, "6 m²"), L("Hallway", 900, 487)]
    rt = [("water", 830, 337), ("glass", 915, 486), ("furn:teak", 868, 420),
          ("planting", 915, 288, 1006, 326), ("travertine_out", 797, 288, 1006, 470),
          ("travertine_out", 797, 470, 826, 500), ("stair", 797, 500, 1006, 532)]
    rtl = [L("Rooftop", 960, 410, "33 m²"), L("Jacuzzi", 830, 337, light=True), L("Skylight", 915, 486)]
    return [(gf, gfl), (f2, f2l), (rt, rtl)]


def fonts():
    head, body = os.path.join(FONTS, "cinzel-latin.woff2"), os.path.join(FONTS, "jost-latin.woff2")
    return {
        "label": ImageFont.truetype(head, 28), "sub": ImageFont.truetype(body, 24),
        "title": ImageFont.truetype(head, 64), "subtitle": ImageFont.truetype(body, 36),
    }


def build(pdf, out, only=None):
    os.makedirs(os.path.join(out, "hires"), exist_ok=True)
    doc = fitz.open(pdf)
    F = fonts()
    for n in (1, 2, 3, 4):
        if only and n not in only:
            continue
        defs = villa_123(n) if n < 4 else villa_4()
        sheets = []
        for (slug, fname, page), (zones, labels) in zip(FLOORS, defs):
            img = Plan(doc[page], CLIPS[n]).render(zones, labels, F)
            area = AREAS[n][page]
            sheet = frame(img, f"Villa {n}", fname,
                          f"Built area {area:.1f} m²  ·  Scale 1:100 at 300 dpi  ·  Indicative, design development 05.01.2026", F)
            sheets.append(sheet)
            base = f"villa-{n}-{slug}"
            sheet.save(os.path.join(out, "hires", base + ".png"), optimize=True)
            web = sheet.copy()
            web.thumbnail((1400, 1400), Image.LANCZOS)
            web.save(os.path.join(out, base + ".webp"), quality=86, method=6)
            print("wrote", base, sheet.size)
        # one landscape board per villa: three floors side by side
        gap = 40
        bw = sum(s.width for s in sheets) + gap * 2
        bh = max(s.height for s in sheets)
        board = Image.new("RGB", (bw, bh), sheets[0].getpixel((5, 5)))
        x = 0
        for s in sheets:
            board.paste(s, (x, 0))
            x += s.width + gap
        board.save(os.path.join(out, "hires", f"villa-{n}-all-floors.pdf"), resolution=300)
        web = board.copy()
        web.thumbnail((2400, 2400), Image.LANCZOS)
        web.save(os.path.join(out, f"villa-{n}-all-floors.webp"), quality=86, method=6)
        print("wrote board", n, board.size)


if __name__ == "__main__":
    only = {int(a) for a in sys.argv[3:]} or None
    build(sys.argv[1], sys.argv[2], only)
