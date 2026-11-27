"""Rendered 2D floor plans for the Auraya villas, generated from the architect's CAD PDF.

The PDF (Villa Matteo, A.01.01-A.01.03) keeps the CAD layers as optional content, so each
path is classified by layer:
  ACUT/ASIT  cut walls and site lines      APAT  hatch: diagonal = wall poche, other = deck/planter
  AFUR/AELE  furniture, doors, fixtures    ABOV  overhead / below (drawn faint)
  ASTR       columns (filled)              ATEX/ADIM/AHAT/0  text, dimensions, pool hatch, title block (dropped)

Rooms are filled by labelling the enclosed regions of the linework and assigning each region a
material, either through a zone rectangle (by the region's centroid) or as furniture
(a region fully enclosed by furniture lines). See plans.py for the per-villa definitions.

Usage: python3 tools/floorplans/plans.py <path-to-pdf> <out-dir>
"""
import math
import numpy as np
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
from scipy import ndimage as ndi

DPI = 300
S = DPI / 72.0
PT_PER_M = 72 / 25.4 * 10  # 1:100 -> 1 m is 10 mm on paper

PAL = {
    "paper": "#faf7ec", "ink": "#3E2D1E", "wall": "#4B4335", "fine": "#8d8270",
    "faint": "#cfc7b3", "furn": "#f6f1e4", "gold": "#a78b5f", "soft": "#6f6450",
}


def rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def classify(d):
    lay = (d.get("layer") or "").split("$")[-1]
    if lay in ("ATEX", "ADIM", "0", "AHAT", ""):
        return None
    if d.get("fill") is not None and d.get("color") in (None, (1.0, 1.0, 1.0)):
        return None
    if lay == "ASTR":
        return "column"
    if lay == "ACUT":
        return "struct"
    if lay == "ASIT":
        return "site"
    if lay == "APAT":
        it = d["items"][0]
        if it[0] == "l":
            dx, dy = it[2].x - it[1].x, it[2].y - it[1].y
            ang = abs(math.degrees(math.atan2(dy, dx))) % 90
            if 15 < ang < 75 and math.hypot(dx, dy) > 2.5:
                return "poche"
        return "slat"
    if lay == "ABOV":
        return "above"
    return "fine"


class Plan:
    def __init__(self, page, clip):
        self.clip = fitz.Rect(*clip)
        self.W, self.H = int(self.clip.width * S), int(self.clip.height * S)
        c = self.clip
        hit = lambda r: r.x1 >= c.x0 and r.x0 <= c.x1 and r.y1 >= c.y0 and r.y0 <= c.y1
        self.layers = {k: [] for k in ("struct", "site", "poche", "slat", "fine", "column", "above")}
        for d in page.get_drawings():
            if hit(d["rect"]):
                k = classify(d)
                if k:
                    self.layers[k].append(d)
        self.rng = np.random.default_rng(7)

    def px(self, x, y):
        return int((x - self.clip.x0) * S), int((y - self.clip.y0) * S)

    def raster(self, key, scale=1.0, min_w=1, fill=False):
        img = Image.new("L", (self.W, self.H), 0)
        dr = ImageDraw.Draw(img)
        for d in self.layers[key]:
            lw = int(round(max(min_w, (d.get("width") or 0.1) * S * scale)))
            for it in d["items"]:
                if it[0] == "l":
                    pts = [it[1], it[2]]
                elif it[0] == "c":
                    p0, p1, p2, p3 = it[1:5]
                    pts = []
                    for t in np.linspace(0, 1, 16):
                        a, b, cc, e = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
                        pts.append(fitz.Point(a * p0.x + b * p1.x + cc * p2.x + e * p3.x,
                                              a * p0.y + b * p1.y + cc * p2.y + e * p3.y))
                elif it[0] == "re":
                    r = it[1]
                    pts = [r.tl, r.tr, r.br, r.bl, r.tl]
                elif it[0] == "qu":
                    q = it[1]
                    pts = [q.ul, q.ur, q.lr, q.ll, q.ul]
                else:
                    continue
                xy = [((p.x - self.clip.x0) * S, (p.y - self.clip.y0) * S) for p in pts]
                if fill and len(xy) >= 3:
                    dr.polygon(xy, fill=255)
                dr.line(xy, fill=255, width=lw)
        return np.array(img) > 0

    # ---------- materials ----------
    def noise(self, scale, amp):
        H, W = self.H, self.W
        small = self.rng.standard_normal((H // scale + 2, W // scale + 2)).astype(np.float32)
        big = np.array(Image.fromarray(small).resize((W + scale, H + scale), Image.BICUBIC))[:H, :W]
        return big * amp

    def material(self, name):
        H, W = self.H, self.W
        yy, xx = np.mgrid[0:H, 0:W]
        if name in ("wood", "deck"):
            base, plank, vertical = ("#cfae86", 52, False) if name == "wood" else ("#b08660", 34, True)
            a, c = (xx, yy) if vertical else (yy, xx)
            row = a // plank
            offset = (row * 7919 % 13) * 61
            joint = ((c + offset) % 520) < 2
            seam = (a % plank) < 2
            tone = (row * 2654435761 % 97) / 97.0 - 0.5
            grain = np.sin(c * 0.02 + np.sin(a * 0.15) * 2 + row) * 0.5 + self.noise(6, 0.25)
            img = rgb(base)[None, None, :] * (1 + 0.07 * tone[..., None] + 0.03 * grain[..., None])
            img[seam | joint] *= 0.82
            return img
        if name == "stone":
            tile = 125
            t = ((yy // tile) * 31 + (xx // (tile * 2)) * 17) % 11 / 11.0 - 0.5
            img = rgb("#e2d9c6")[None, None, :] * (1 + 0.035 * t[..., None] + self.noise(3, 0.02)[..., None])
            img[((yy % tile) < 2) | ((xx % (tile * 2)) < 2)] *= 0.9
            return img
        if name == "terrazzo":
            img = rgb("#ebe5d5")[None, None, :] * (1 + self.noise(2, 0.015)[..., None])
            spots = ndi.binary_dilation(self.rng.random((H, W)) > 0.996, iterations=1)
            img[spots] *= 0.86
            return img
        if name == "water":
            t = (yy / H)[..., None]
            img = rgb("#86c9cc") * (1 - t) + rgb("#4a95a3") * t
            caust = np.sin(xx * 0.045 + np.sin(yy * 0.03) * 3) * np.sin(yy * 0.05 + np.sin(xx * 0.02) * 2)
            return img * (1 + 0.06 * caust[..., None] + self.noise(8, 0.04)[..., None])
        if name == "grass":
            return rgb("#98a67a")[None, None, :] * (1 + self.noise(2, 0.07)[..., None] + self.noise(12, 0.06)[..., None])
        if name == "concrete":
            return rgb("#d8d3c7")[None, None, :] * (1 + self.noise(2, 0.02)[..., None] + self.noise(30, 0.03)[..., None])
        if name == "glass":
            img = rgb("#c9dcdc")[None, None, :] * (1 + self.noise(20, 0.02)[..., None])
            band = ((xx + yy) % 220) < 40
            img[band] = img[band] * 0.85 + 255 * 0.15
            return img
        if name == "rug":
            return rgb("#e6dac1")[None, None, :] * (1 + self.noise(2, 0.03)[..., None])
        if name == "stair":
            return rgb("#e8dcc6")[None, None, :] * (1 + self.noise(3, 0.01)[..., None])
        return np.broadcast_to(rgb(PAL["paper"]), (H, W, 3)).astype(np.float32).copy()

    # ---------- render ----------
    def render(self, zones, labels, fonts):
        H, W = self.H, self.W
        m_struct = self.raster("struct", 0.9, 2)
        m_site = self.raster("site", 0.5, 1)
        m_fine = self.raster("fine", 1.0, 2)
        m_poche = self.raster("poche", 1.0, 2)
        m_slat = self.raster("slat", 1.0, 1)
        m_above = self.raster("above", 1.0, 1)
        m_col = self.raster("column", 1.0, 2, fill=True)

        walls = ndi.binary_closing(m_poche, structure=np.ones((9, 9)), iterations=2)
        walls = ndi.binary_opening(walls, structure=np.ones((5, 5))) | m_col

        barrier = ndi.binary_dilation(m_struct | m_fine | walls | m_poche | m_site, iterations=2)
        lab, n = ndi.label(~barrier)
        idx = np.arange(n + 1)
        area = np.bincount(lab.ravel(), minlength=n + 1)
        yy, xx = np.mgrid[0:H, 0:W]
        cx = np.bincount(lab.ravel(), weights=xx.ravel(), minlength=n + 1) / np.maximum(area, 1)
        cy = np.bincount(lab.ravel(), weights=yy.ravel(), minlength=n + 1) / np.maximum(area, 1)

        enclosed = ndi.binary_fill_holes(ndi.binary_dilation(m_fine, iterations=2))
        enc_frac = np.bincount(lab.ravel(), weights=enclosed.ravel(), minlength=n + 1) / np.maximum(area, 1)

        assign = np.full(n + 1, "", dtype=object)
        assign[0] = "-"
        border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}

        def in_zone(i, z):
            x0, y0 = self.px(*z[1:3])
            x1, y1 = self.px(*z[3:5])
            return x0 <= cx[i] <= x1 and y0 <= cy[i] <= y1

        # 1) seeds (pools, jacuzzis, rugs, skylights): the region under the point
        for z in zones:
            if len(z) == 3:
                x, y = self.px(z[1], z[2])
                i = lab[min(max(y, 0), H - 1), min(max(x, 0), W - 1)]
                if i and not assign[i]:
                    assign[i] = z[0]
        # 2) furniture: regions enclosed by furniture/fixture lines
        for i in idx[1:]:
            if not assign[i] and i not in border and enc_frac[i] > 0.9 and area[i] < 0.12 * W * H:
                assign[i] = "furn"
        # 3) zones by centroid, first match wins
        for z in zones:
            if len(z) == 3 or (len(z) > 5 and z[5] == "paint"):
                continue
            edge_ok = len(z) > 5 and z[5] == "edge"
            for i in idx[1:]:
                if not assign[i] and in_zone(i, z) and (edge_ok or i not in border):
                    assign[i] = z[0]

        canvas = np.broadcast_to(rgb(PAL["paper"]), (H, W, 3)).astype(np.float32).copy()
        floor = np.zeros((H, W), bool)
        furn = np.zeros((H, W), bool)
        cache = {}
        for mat in set(assign[1:]) - {"", "furn", "paper", "-"}:
            msk = np.isin(lab, idx[assign == mat])
            msk = ndi.binary_dilation(msk, iterations=3) & ~walls
            if mat not in cache:
                cache[mat] = self.material(mat)
            canvas[msk] = cache[mat][msk]
            floor |= msk
        furn = ndi.binary_dilation(np.isin(lab, idx[assign == "furn"]), iterations=2) & ~walls
        # paint zones: recolour floor inside a wall-bounded rectangle (rooms joined by open doorways)
        for z in zones:
            if len(z) > 5 and z[5] == "paint":
                x0, y0 = self.px(*z[1:3])
                x1, y1 = self.px(*z[3:5])
                r = np.zeros((H, W), bool)
                r[max(y0, 0):y1, max(x0, 0):x1] = True
                r &= floor & ~furn
                if z[0] not in cache:
                    cache[z[0]] = self.material(z[0])
                canvas[r] = cache[z[0]][r]

        def shadow(mask, dx, dy, blur, k):
            im = Image.fromarray((mask * 255).astype(np.uint8))
            im = ImageChops.offset(im, dx, dy).filter(ImageFilter.GaussianBlur(blur))
            return np.array(im, np.float32) / 255.0 * k

        sh = np.clip(shadow(furn, 10, 12, 10, 0.26) + shadow(walls | m_struct, 14, 16, 14, 0.34), 0, 0.45)
        canvas *= (1 - (sh * floor)[..., None])
        canvas[furn] = rgb(PAL["furn"])

        def ink(mask, color, alpha):
            canvas[mask] = canvas[mask] * (1 - alpha) + rgb(color) * alpha

        ink(m_above & ~walls, PAL["fine"], 0.35)
        ink(m_site & ~walls, PAL["fine"], 0.5)
        ink(m_slat & ~walls & ~floor, PAL["fine"], 0.3)
        ink(m_fine & ~walls, PAL["fine"], 0.7)
        canvas[m_struct] = rgb(PAL["ink"])
        canvas[walls] = rgb(PAL["wall"])

        img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
        dr = ImageDraw.Draw(img)
        for lb in labels:
            x, y = self.px(lb["at"][0], lb["at"][1])
            light = lb.get("light", False)
            c1 = (255, 255, 255) if light else (62, 45, 30)
            c2 = (240, 248, 248) if light else (95, 82, 62)
            rot = lb.get("rot", 0)
            if rot:
                tmp = Image.new("RGBA", (420, 120), (0, 0, 0, 0))
                td = ImageDraw.Draw(tmp)
                self._text(td, 210, 60, lb, fonts, c1, c2)
                tmp = tmp.rotate(rot, expand=True)
                img.paste(tmp, (x - tmp.width // 2, y - tmp.height // 2), tmp)
            else:
                self._text(dr, x, y, lb, fonts, c1, c2)
        return img

    @staticmethod
    def _text(dr, x, y, lb, fonts, c1, c2):
        t1, t2 = lb["name"].upper(), lb.get("sub", "")
        f1, f2 = fonts["label"], fonts["sub"]
        w1 = dr.textlength(t1, font=f1)
        if t2:
            w2 = dr.textlength(t2, font=f2)
            dr.text((x - w1 / 2, y - 30), t1, font=f1, fill=c1)
            dr.text((x - w2 / 2, y + 8), t2, font=f2, fill=c2)
        else:
            dr.text((x - w1 / 2, y - 14), t1, font=f1, fill=c1)


def frame(plan_img, title, subtitle, meta, fonts, logo=None):
    """Place a rendered plan on a sheet with a title block and a 1:100 scale bar."""
    pad, band = 90, 330
    W = plan_img.width + pad * 2
    H = plan_img.height + pad + band
    sheet = Image.new("RGB", (W, H), tuple(int(v) for v in rgb(PAL["paper"])))
    sheet.paste(plan_img, (pad, pad))
    dr = ImageDraw.Draw(sheet)
    y0 = plan_img.height + pad + 50
    dr.line([(pad, y0), (W - pad, y0)], fill=tuple(int(v) for v in rgb(PAL["gold"])), width=3)
    dr.text((pad, y0 + 34), title, font=fonts["title"], fill=(62, 45, 30))
    dr.text((pad, y0 + 118), subtitle, font=fonts["subtitle"], fill=(111, 100, 80))
    dr.text((pad, y0 + 175), meta, font=fonts["sub"], fill=(141, 130, 112))
    # scale bar 0-1-2-3 m
    m = PT_PER_M * S
    bx, by = W - pad - 3 * m, y0 + 60
    for k in range(3):
        col = (62, 45, 30) if k % 2 == 0 else (250, 247, 236)
        dr.rectangle([bx + k * m, by, bx + (k + 1) * m, by + 18], fill=col, outline=(62, 45, 30), width=2)
    for k in range(4):
        t = f"{k}" if k < 3 else "3 m"
        tw = dr.textlength(t, font=fonts["sub"])
        dr.text((bx + k * m - tw / 2, by + 30), t, font=fonts["sub"], fill=(111, 100, 80))
    return sheet
