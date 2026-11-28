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
# Site-layer lines that are not the plot boundary (setback line ending at Villa 4's boundary)
SITE_EXCLUDE = {(4, 1): [(978, 462, 1050, 472)], (4, 2): [(978, 462, 1050, 472)]}
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
    ("polished_concrete", 405, 225, 586, 262),
    ("terrazzo", 364, 432, 442, 466),
    ("stair", 442, 432, 500, 466),
    ("marble", 364, 262, 586, 466),
    ("pavers", 362, 466, 586, 508, "edge"),
]
V2_GF_HOUSE_LABELS = [
    L("Shower", 391, 243), L("Terrace", 500, 246),
    L("Living", 548, 330, "25 m²"), L("Dining + Kitchen", 432, 409, "15 m²"),
    L("Powder", 398, 447, "3 m²"), L("Bike Parking", 474, 488),
]
V2_2F = [
    ("furn", 441, 265), ("furn", 530, 265), ("marble", 440, 302), ("marble", 520, 302),
    ("furn", 398, 318, 426, 342), ("furn", 521, 318, 558, 342),
    ("furn:walnut", 398, 318, 426, 342), ("furn:walnut", 521, 318, 558, 342),
    ("terrazzo", 400, 331, 476, 405, "paint"), ("terrazzo", 477, 331, 551, 405, "paint"),
    ("marble", 364, 222, 586, 404), ("marble", 364, 404, 586, 436), ("stair", 364, 436, 586, 466),
]
V2_2F_LABELS = [
    L("Bedroom", 422, 266, "14 m²"), L("Bedroom", 530, 266, "14 m²"),
    L("Bathroom", 437, 368, "6 m²"), L("Bathroom", 526, 368, "6 m²"), L("Hallway", 476, 420),
]
V2_RT = [
    ("water", 406, 268), ("glass", 489, 420), ("furn:teak", 441, 348),
    ("planting", 486, 218, 586, 258), ("polished_concrete", 364, 218, 586, 404),
    ("polished_concrete", 364, 404, 400, 436), ("stair", 364, 436, 586, 466),
]
V2_RT_LABELS = [L("Rooftop", 535, 330, "33 m²"), L("Jacuzzi", 406, 268, "Optional add-on", light=True), L("Skylight", 489, 418)]


# ---------------- furniture (decor.py), Villa 2 module ----------------
V2_GF_DECOR = [  # inside the 7.5 m module (same in every villa, Villa 4 shifted)
    ("rug", 403, 270, 494, 348, "#d6cab2"),
    ("console", 374, 270, 383, 340, "#5e4533"),
    ("ottoman", 412, 320, 446, 341),
    ("table_round", 459, 298.5, 11, "#8f6848"),
    ("sofa", 481, 274, 501, 343, 90), ("sofa", 461, 321, 482, 343, 180),
    ("tall_units", 374, 369, 391, 433, 4),
    ("island", 416, 369, 463, 395),
    ("chair", 428, 364, 10, 10, 0, "#9b7250"), ("chair", 449, 364, 10, 10, 0, "#9b7250"),
    ("table", 463, 369, 510, 395, "#b48a62"),
    ("chair", 476.5, 364, 13, 12, 0), ("chair", 498.5, 364, 13, 12, 0),
    ("chair", 476.5, 400, 13, 12, 180), ("chair", 498.5, 400, 13, 12, 180),
    ("tall_units", 421, 416, 445, 433, 1), ("tall_units", 492, 416, 514, 433, 1),
    ("counter", 445, 416, 492, 433, 180, [("sink", 0.3), ("hob", 0.72)]),
    ("pot_plant", 576, 236, 8), ("pot_plant", 577, 350, 9),
    ("scooter", 397, 486, 90), ("scooter", 551, 486, 90),
]
STRIP = [("shrub", 373, 128, 9, 0), ("palm", 372, 160, 20), ("shrub", 373, 192, 9, 2), ("shrub", 373, 214, 9, 1)]
GF_OUTSIDE = {  # loungers on the sunbed deck and garden planting, per villa
    1: [("lounger", 338.4, 158, 90), ("lounger", 338.4, 182, 90),
        ("palm", 118, 140, 22), ("shrub", 98, 172, 10, 1), ("palm", 126, 214, 20), ("shrub", 132, 258, 10, 2),
        ("shrub", 140, 298, 9, 0), ("palm", 146, 340, 16), ("shrub", 150, 392, 7, 1)],
    2: [("lounger", 551, 158, 90), ("lounger", 551, 182, 90)] + STRIP,
    3: [("lounger", 764, 205, 90)],
    4: [("lounger", 950, 281, 90), ("pot_plant", 995, 284, 7),
        ("palm", 1022, 330, 18), ("shrub", 1026, 380, 12, 1), ("palm", 1030, 440, 20), ("shrub", 1030, 498, 12, 2),
        ("palm", 1034, 546, 18), ("shrub", 812, 581, 10, 0), ("shrub", 852, 582, 10, 2), ("shrub", 892, 581, 10, 1),
        ("shrub", 932, 582, 10, 0), ("shrub", 972, 581, 10, 2), ("shrub", 1012, 582, 10, 1)],
}
V2_2F_DECOR = [
    ("rug", 392, 234, 452, 296, "#d3c6ac"), ("rug", 512, 234, 572, 296, "#d3c6ac"),
    ("bed", 404, 244, 474, 286, 90), ("bed", 492, 244, 560, 286, 270),
    ("nightstand", 462, 230, 474, 242), ("nightstand", 462, 288, 474, 300),
    ("nightstand", 492, 230, 504, 242), ("nightstand", 492, 288, 504, 300),
    ("desk", 374, 244, 382, 286, 270), ("chair", 388, 258, 13, 12, 90),
    ("desk", 575, 244, 583, 286, 90), ("chair", 568, 258, 13, 12, 270),
    ("tall_units", 399, 314, 425, 331, 2), ("tall_units", 527, 314, 552, 331, 2),
]
V2_RT_DECOR = [
    ("daybed", 437, 225, 487, 257, 0),
    ("shrub", 500, 240, 11, 0), ("palm", 525, 241, 22), ("shrub", 552, 238, 11, 2), ("shrub", 575, 242, 10, 1),
    ("lounge_chair", 516, 274, -25), ("lounge_chair", 553, 276, 25), ("table_round", 534, 288, 6, "#9b7250"),
    ("table", 404, 338, 480, 366, "#9b7250"),
    ("chair", 417, 332, 13, 12, 0, "#9b7250"), ("chair", 434, 332, 13, 12, 0, "#9b7250"),
    ("chair", 451, 332, 13, 12, 0, "#9b7250"), ("chair", 468, 332, 13, 12, 0, "#9b7250"),
    ("chair", 417, 372, 13, 12, 180, "#9b7250"), ("chair", 434, 372, 13, 12, 180, "#9b7250"),
    ("chair", 451, 372, 13, 12, 180, "#9b7250"), ("chair", 468, 372, 13, 12, 180, "#9b7250"),
    ("counter", 492, 387, 586, 403, 180, [("sink", 0.25), ("hob", 0.7)]),
    ("pot_plant", 576, 330, 9), ("pot_plant", 376, 322, 8),
]
CENTRED = {"palm", "shrub", "pot_plant", "toilet", "lounger", "lounge_chair", "basin_round", "table_round", "chair", "scooter"}


def shift_decor(items, dx, dy=0):
    out = []
    for it in items:
        it = list(it)
        it[1] += dx
        it[2] += dy
        if it[0] not in CENTRED:
            it[3] += dx
            it[4] += dy
        out.append(tuple(it))
    return out


V4_SHIFT = (425.4, 68)  # Villa 4's rooms are the 7.5 m module moved by this much on the sheet


def villa_123(n):
    dx = (n - 2) * MODULE
    gf, gfl = shift(V2_GF_HOUSE, V2_GF_HOUSE_LABELS, dx)
    if n == 1:
        # keep the rug and joinery (first 4), replace V2's shower/terrace (next 2) with Villa 1's own
        gf = [("water", 206, 165)] + gf[:4] + [
            ("terrazzo", 157, 222, 195, 256), ("polished_concrete", 195, 215, 372, 256),
            ("polished_concrete", 300, 100, 372, 222), ("polished_concrete", 108, 100, 302, 214),
            ("planting", 120, 300), ("planting", 130, 215),
        ] + gf[6:]
        gfl = [L("Pool", 206, 163, "15 m²", light=True), L("Sunbed", 338, 211),
               L("Shower", 178, 240), L("Terrace", 290, 246)] + gfl[2:]
    elif n == 2:
        gf = [("water", 448, 175), ("polished_concrete", 512, 100, 586, 226), ("planting", 362, 100, 382, 226),
              ("polished_concrete", 380, 100, 515, 226)] + gf
        gfl = [L("Pool", 448, 178, "11 m²", light=True), L("Sunbed", 551, 211)] + gfl
    else:
        gf = [("water", 660, 182), ("polished_concrete", 728, 100, 799, 226), ("planting", 575, 100, 594, 226),
              ("polished_concrete", 592, 100, 731, 226)] + gf
        gfl = [L("Pool", 662, 180, "7 m²", light=True), L("Sunbed", 762, 184)] + gfl
    f2, f2l = shift(V2_2F, V2_2F_LABELS, dx)
    rt, rtl = shift(V2_RT, V2_RT_LABELS, dx)
    strip = shift_decor(STRIP[1:], dx) if n == 3 else []
    decor = [shift_decor(V2_GF_DECOR, dx) + GF_OUTSIDE[n] + strip,
             shift_decor(V2_2F_DECOR, dx), shift_decor(V2_RT_DECOR, dx)]
    return [(gf, gfl, decor[0]), (f2, f2l, decor[1]), (rt, rtl, decor[2])]


def villa_4():
    gf = [
        ("furn:walnut", 797, 435, 820, 503), ("furn:walnut", 845, 478, 870, 503), ("furn:walnut", 905, 478, 930, 503),
        ("water", 860, 255), ("rug", 832, 345), ("planting", 1030, 450),
        ("terrazzo", 800, 296, 830, 333), ("polished_concrete", 830, 292, 1003, 333),
        ("polished_concrete", 912, 172, 1020, 294), ("polished_concrete", 795, 172, 915, 294),
        ("planting", 1000, 172, 1068, 568, "edge"),
        ("terrazzo", 800, 502, 868, 532), ("stair", 868, 502, 975, 532),
        ("marble", 797, 333, 1003, 532), ("pavers", 797, 532, 1003, 568, "edge"), ("pavers", 797, 531, 1001, 567, "paint"),
        ("planting", 790, 568, 1068, 595, "edge"),
    ]
    gfl = [L("Pool", 860, 256, "6 m²", light=True), L("Sunbed", 932, 262),
           L("Shower", 815, 312), L("Terrace", 925, 314),
           L("Living", 968, 378, "25 m²"), L("Dining + Kitchen", 972, 442, "15 m²"),
           L("Powder", 834, 518, "3 m²"), L("Bike Parking", 900, 550)]
    f2 = [("furn", 864, 330), ("furn", 955, 330), ("marble", 864, 365), ("marble", 955, 365),
          ("furn", 824, 392, 852, 412), ("furn", 949, 392, 977, 412),
          ("furn:walnut", 824, 392, 852, 412), ("furn:walnut", 949, 392, 977, 412),
          ("terrazzo", 826, 403, 901, 472, "paint"), ("terrazzo", 902, 403, 977, 472, "paint"),
          ("marble", 797, 292, 1006, 472), ("marble", 797, 472, 1006, 501), ("stair", 797, 501, 1006, 532)]
    f2l = [L("Bedroom", 850, 322, "14 m²"), L("Bedroom", 955, 322, "14 m²"),
           L("Bathroom", 864, 425, "6 m²"), L("Bathroom", 940, 425, "6 m²"), L("Hallway", 900, 487)]
    rt = [("water", 830, 337), ("glass", 915, 486), ("furn:teak", 868, 420),
          ("planting", 915, 288, 1006, 326), ("polished_concrete", 797, 288, 1006, 470),
          ("polished_concrete", 797, 470, 826, 500), ("stair", 797, 500, 1006, 532)]
    rtl = [L("Rooftop", 960, 410, "33 m²"), L("Jacuzzi", 830, 337, "Optional add-on", light=True), L("Skylight", 915, 486)]
    rtd = [it if it[0] != "counter" else it[:3] + (1004,) + it[4:] for it in shift_decor(V2_RT_DECOR, *V4_SHIFT)]
    decor = [shift_decor(V2_GF_DECOR, *V4_SHIFT) + GF_OUTSIDE[4], shift_decor(V2_2F_DECOR, *V4_SHIFT), rtd]
    return [(gf, gfl, decor[0]), (f2, f2l, decor[1]), (rt, rtl, decor[2])]


def fonts():
    head, body = os.path.join(FONTS, "cinzel-latin.woff2"), os.path.join(FONTS, "jost-latin.woff2")
    return {
        "label": ImageFont.truetype(head, 28), "sub": ImageFont.truetype(body, 24),
        "title": ImageFont.truetype(head, 64), "subtitle": ImageFont.truetype(body, 36),
        "num": ImageFont.truetype(body, 26), "numsmall": ImageFont.truetype(body, 20),
        "legend": ImageFont.truetype(body, 26),
        "dim": ImageFont.truetype(body, 24),
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
        for (slug, fname, page), (zones, labels, decor) in zip(FLOORS, defs):
            plan = Plan(doc[page], CLIPS[n])
            plan.site_exclude = SITE_EXCLUDE.get((n, page), ())
            img, legend = plan.render(zones, labels, F, decor)
            os.makedirs(os.path.join(out, "brochure"), exist_ok=True)
            plan_only = img.copy()  # plan + dimensions + labels, no title block: for the brochure page
            plan_only.thumbnail((1800, 1800), Image.LANCZOS)
            plan_only.save(os.path.join(out, "brochure", f"villa-a{n}-{slug}.webp"), quality=88, method=6)
            sheet = frame(img, f"Villa A{n}", fname,
                          "Scale 1:100 at 300 dpi  ·  Indicative, design development 05.01.2026", F, legend)
            sheets.append(sheet)
            base = f"villa-a{n}-{slug}"
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
        board.save(os.path.join(out, "hires", f"villa-a{n}-all-floors.pdf"), resolution=300)
        board.save(os.path.join(out, "hires", f"villa-a{n}-all-floors.jpg"), quality=92)
        web = board.copy()
        web.thumbnail((2400, 2400), Image.LANCZOS)
        web.save(os.path.join(out, f"villa-a{n}-all-floors.webp"), quality=86, method=6)
        print("wrote board", n, board.size)


if __name__ == "__main__":
    only = {int(a) for a in sys.argv[3:]} or None
    build(sys.argv[1], sys.argv[2], only)
