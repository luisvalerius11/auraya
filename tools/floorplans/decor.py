"""Top-view furniture, fixtures and planting for the rendered plans.

Every item is drawn procedurally as an RGBA sprite (2x supersampled, then reduced) in a canonical
orientation, rotated if asked, and composited onto the plan with a soft drop shadow.
Canonical orientation: the item's back / head / wall side is at the TOP of its rectangle.

Item specs (coordinates in PDF points, like the zones in plans.py):
  ("sofa", x0, y0, x1, y1, rot)            ("chair", cx, cy, w, h, rot)
  ("rug", x0, y0, x1, y1, colour)          ("table_round", cx, cy, r, wood)
  ("table", x0, y0, x1, y1, wood)          ("ottoman", x0, y0, x1, y1)
  ("console", x0, y0, x1, y1, wood)        ("tall_units", x0, y0, x1, y1, n, rot)
  ("island", x0, y0, x1, y1)               ("counter", x0, y0, x1, y1, rot, [("sink"|"hob", frac)])
  ("bed", x0, y0, x1, y1, rot)             ("desk", x0, y0, x1, y1, rot)
  ("vanity", x0, y0, x1, y1, rot, basins)  ("toilet", cx, cy, rot)
  ("basin_round", cx, cy, r)               ("shower", x0, y0, x1, y1, rot)
  ("lounger", cx, cy, rot)                 ("lounge_chair", cx, cy, rot)
  ("palm", cx, cy, r)                      ("shrub", cx, cy, r)
  ("pot_plant", cx, cy, r)                 ("daybed", x0, y0, x1, y1, rot)
  ("scooter", cx, cy, rot)
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

SS = 2  # supersampling


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Painter:
    def __init__(self, plan, seed=11):
        self.plan = plan
        self.rng = np.random.default_rng(seed)
        self.k = 300 / 72.0  # px per pt

    # ---------- texture helpers (operate on HxWx3 float arrays) ----------
    def noise(self, h, w, scale, amp):
        small = self.rng.standard_normal((h // scale + 2, w // scale + 2)).astype(np.float32)
        big = np.array(Image.fromarray(small).resize((w + scale, h + scale), Image.BICUBIC))[:h, :w]
        return big * amp

    def tex(self, kind, h, w, base):
        b = np.array(_rgb(base), np.float32)
        yy, xx = np.mgrid[0:h, 0:w]
        if kind == "boucle":
            t = self.noise(h, w, 1, 0.05) + self.noise(h, w, 3, 0.03)
        elif kind == "linen":
            t = np.sin(yy * 1.7 + self.noise(h, w, 6, 2)) * 0.02 + self.noise(h, w, 2, 0.02)
        elif kind == "wood":  # grain along x
            t = np.sin(yy * 0.55 + np.sin(xx * 0.03) * 2 + self.noise(h, w, 10, 2.0)) * 0.05 + self.noise(h, w, 2, 0.02)
        elif kind == "wool":
            t = self.noise(h, w, 1, 0.035) + self.noise(h, w, 8, 0.03)
        elif kind == "marble":
            v = np.sin(xx * 0.05 + yy * 0.02 + np.sin(yy * 0.04) * 3 + self.noise(h, w, 12, 1.5))
            t = -0.07 * (np.abs(v) < 0.06) - 0.025 * (np.abs(v) < 0.25) + self.noise(h, w, 2, 0.01)
        elif kind == "ceramic":
            t = self.noise(h, w, 6, 0.01)
        else:
            t = self.noise(h, w, 2, 0.01)
        return np.clip(b[None, None, :] * (1 + t[..., None]), 0, 255)

    # ---------- sprite plumbing ----------
    def canvas(self, w, h):
        return Image.new("RGBA", (int(w * SS), int(h * SS)), (0, 0, 0, 0))

    def fill_tex(self, spr, mask_img, kind, base, shade=0.0):
        """Fill the area of mask_img (L, sprite size) with a texture; optional edge shading."""
        m = np.array(mask_img, np.float32) / 255.0
        h, w = m.shape
        t = self.tex(kind, h, w, base)
        if shade:
            dist = np.array(mask_img.filter(ImageFilter.GaussianBlur(6 * SS)), np.float32) / 255.0
            t *= (1 - shade * (1 - dist))[..., None]
        arr = np.array(spr, np.float32)
        a = m[..., None]
        arr[..., :3] = arr[..., :3] * (1 - a) + t * a
        arr[..., 3] = np.maximum(arr[..., 3], m * 255)
        return Image.fromarray(arr.astype(np.uint8), "RGBA")

    def shape(self, w, h, fn):
        m = Image.new("L", (int(w * SS), int(h * SS)), 0)
        fn(ImageDraw.Draw(m), SS)
        return m

    def place(self, base, spr, cx, cy, rot=0, shadow=0.32, lift=1.0):
        """Composite sprite centred at plan pixel (cx, cy)."""
        spr = spr.resize((max(1, spr.width // SS), max(1, spr.height // SS)), Image.LANCZOS)
        if rot:
            spr = spr.rotate(-rot, resample=Image.BICUBIC, expand=True)
        x, y = int(round(cx - spr.width / 2)), int(round(cy - spr.height / 2))
        if shadow:
            a = spr.split()[3]
            pad = 40
            sh = Image.new("L", (spr.width + pad * 2, spr.height + pad * 2), 0)
            sh.paste(a, (pad, pad))
            sh = sh.filter(ImageFilter.GaussianBlur(7 * lift))
            dark = Image.new("RGBA", sh.size, (40, 28, 18, 0))
            dark.putalpha(sh.point(lambda v: int(v * shadow)))
            base.alpha_composite(dark, (x - pad + int(7 * lift), y - pad + int(9 * lift)))
        base.alpha_composite(spr, (x, y))

    def line(self, spr, pts, col, width):
        ImageDraw.Draw(spr).line([(p[0] * SS, p[1] * SS) for p in pts], fill=col, width=int(width * SS))

    # ---------- furniture ----------
    def sofa(self, w, h, fabric="#e7e0d2"):
        spr = self.canvas(w, h)
        back = max(5, h * 0.24)
        arm = max(5, h * 0.2)
        outer = self.shape(w, h, lambda d, s: d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=6 * s, fill=255))
        spr = self.fill_tex(spr, outer, "boucle", fabric, shade=0.18)
        n = max(1, round((w - 2 * arm) / (h * 0.9)))
        cw = (w - 2 * arm) / n
        for i in range(n):  # seat cushions
            x0 = arm + i * cw
            m = self.shape(w, h, lambda d, s, x0=x0: d.rounded_rectangle(
                [(x0 + 1.5) * s, (back + 1) * s, (x0 + cw - 1.5) * s, (h - 3) * s], radius=7 * s, fill=255))
            spr = self.fill_tex(spr, m, "boucle", "#f1ebdf", shade=0.22)
        for i in range(n):  # back cushions
            x0 = arm + i * cw
            m = self.shape(w, h, lambda d, s, x0=x0: d.rounded_rectangle(
                [(x0 + 1) * s, 2 * s, (x0 + cw - 1) * s, (back + 3) * s], radius=6 * s, fill=255))
            spr = self.fill_tex(spr, m, "boucle", "#ece5d8", shade=0.25)
        return spr

    def chair(self, w, h, fabric="#ede6d8", frame=None):
        spr = self.canvas(w, h)
        seat = self.shape(w, h, lambda d, s: d.rounded_rectangle([1 * s, h * 0.22 * s, (w - 1) * s, (h - 1) * s], radius=w * 0.28 * s, fill=255))
        backm = self.shape(w, h, lambda d, s: d.rounded_rectangle([0, 0, w * s - 1, h * 0.42 * s], radius=w * 0.25 * s, fill=255))
        if frame:
            spr = self.fill_tex(spr, backm, "wood", frame, shade=0.15)
        else:
            spr = self.fill_tex(spr, backm, "boucle", "#e2dbcc", shade=0.25)
        spr = self.fill_tex(spr, seat, "boucle", fabric, shade=0.2)
        return spr

    def rug(self, w, h, col="#d9cfbb"):
        spr = self.canvas(w, h)
        m = self.shape(w, h, lambda d, s: d.rectangle([0, 0, w * s - 1, h * s - 1], fill=255))
        spr = self.fill_tex(spr, m, "wool", col)
        inner = self.shape(w, h, lambda d, s: d.rectangle([5 * s, 5 * s, (w - 5) * s, (h - 5) * s], outline=255, width=int(2 * s)))
        spr = self.fill_tex(spr, inner, "wool", "#c4b89f")
        return spr

    def table(self, w, h, wood="#a87b52", kind="wood"):
        spr = self.canvas(w, h)
        m = self.shape(w, h, lambda d, s: d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=2 * s, fill=255))
        spr = self.fill_tex(spr, m, kind, wood, shade=0.12)
        return spr

    def table_round(self, r, wood="#9c7350"):
        w = h = 2 * r
        spr = self.canvas(w, h)
        m = self.shape(w, h, lambda d, s: d.ellipse([0, 0, w * s - 1, h * s - 1], fill=255))
        spr = self.fill_tex(spr, m, "wood", wood, shade=0.2)
        hl = self.shape(w, h, lambda d, s: d.ellipse([w * 0.18 * s, h * 0.18 * s, w * 0.55 * s, h * 0.5 * s], fill=255)).filter(ImageFilter.GaussianBlur(6 * SS))
        arr = np.array(spr, np.float32)
        arr[..., :3] += (np.array(hl, np.float32) / 255.0 * 22)[..., None]
        spr = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        # a vase / bowl
        v = self.shape(w, h, lambda d, s: d.ellipse([w * 0.4 * s, h * 0.4 * s, w * 0.6 * s, h * 0.6 * s], fill=255))
        return self.fill_tex(spr, v, "ceramic", "#e9e2d3", shade=0.35)

    def ottoman(self, w, h):
        spr = self.canvas(w, h)
        m = self.shape(w, h, lambda d, s: d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=8 * s, fill=255))
        spr = self.fill_tex(spr, m, "boucle", "#f0eadf", shade=0.25)
        nx, ny = max(2, round(w / 45)), max(1, round(h / 45))
        for i in range(1, nx):
            self.line(spr, [(w * i / nx, 3), (w * i / nx, h - 3)], (222, 214, 200, 255), 1.6)
        for j in range(1, ny):
            self.line(spr, [(3, h * j / ny), (w - 3, h * j / ny)], (222, 214, 200, 255), 1.6)
        return spr

    def joinery(self, w, h, n=1, wood="#5e4533"):
        spr = self.canvas(w, h)
        m = self.shape(w, h, lambda d, s: d.rectangle([0, 0, w * s - 1, h * s - 1], fill=255))
        spr = self.fill_tex(spr, m, "wood", wood, shade=0.1)
        for i in range(1, n):
            self.line(spr, [(w * i / n, 0), (w * i / n, h)], (40, 28, 20, 255), 1.2)
        return spr

    def counter(self, w, h, fixtures=()):
        spr = self.canvas(w, h)
        m = self.shape(w, h, lambda d, s: d.rectangle([0, 0, w * s - 1, h * s - 1], fill=255))
        spr = self.fill_tex(spr, m, "marble", "#ece6da", shade=0.06)
        for kind, f in fixtures:
            cx = w * f
            if kind == "sink":
                sm = self.shape(w, h, lambda d, s: d.rounded_rectangle([(cx - h * 0.45) * s, h * 0.22 * s, (cx + h * 0.45) * s, h * 0.82 * s], radius=4 * s, fill=255))
                spr = self.fill_tex(spr, sm, "plain", "#b9b9b6", shade=0.4)
                tap = self.shape(w, h, lambda d, s: d.ellipse([(cx - 2) * s, 1 * s, (cx + 2) * s, 5 * s], fill=255))
                spr = self.fill_tex(spr, tap, "plain", "#55524d")
            else:
                hm = self.shape(w, h, lambda d, s: d.rounded_rectangle([(cx - h * 0.55) * s, h * 0.15 * s, (cx + h * 0.55) * s, h * 0.85 * s], radius=2 * s, fill=255))
                spr = self.fill_tex(spr, hm, "plain", "#2a2826")
                dr = ImageDraw.Draw(spr)
                for ox in (-0.25, 0.25):
                    for oy in (-0.17, 0.17):
                        r = h * 0.12
                        x, y = cx + ox * h * 1.1, h * 0.5 + oy * h * 1.1
                        dr.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], outline=(110, 108, 104, 255), width=SS)
        return spr

    def bed(self, w, h):
        """w = width across, h = length; headboard at top."""
        spr = self.canvas(w, h)
        hb = max(4, h * 0.06)
        m = self.shape(w, h, lambda d, s: d.rectangle([0, 0, w * s - 1, hb * s], fill=255))
        spr = self.fill_tex(spr, m, "wood", "#5e4533", shade=0.1)
        mat = self.shape(w, h, lambda d, s: d.rounded_rectangle([2 * s, hb * s, (w - 2) * s, (h - 1) * s], radius=5 * s, fill=255))
        spr = self.fill_tex(spr, mat, "linen", "#f4f1ea", shade=0.2)
        # duvet fold and throw
        fold = h * 0.42
        self.line(spr, [(3, fold), (w - 3, fold)], (214, 207, 194, 255), 1.4)
        th = self.shape(w, h, lambda d, s: d.rectangle([1 * s, h * 0.72 * s, (w - 1) * s, h * 0.86 * s], fill=255))
        spr = self.fill_tex(spr, th, "linen", "#b8a68c", shade=0.15)
        # pillows
        pw = (w - 10) / 2
        for i in range(2):
            x0 = 4 + i * (pw + 2)
            p = self.shape(w, h, lambda d, s, x0=x0: d.rounded_rectangle([x0 * s, (hb + 2) * s, (x0 + pw) * s, (hb + h * 0.17) * s], radius=6 * s, fill=255))
            spr = self.fill_tex(spr, p, "linen", "#fbf9f4", shade=0.3)
        cp = self.shape(w, h, lambda d, s: d.rounded_rectangle([w * 0.3 * s, (hb + h * 0.13) * s, w * 0.7 * s, (hb + h * 0.23) * s], radius=5 * s, fill=255))
        return self.fill_tex(spr, cp, "linen", "#cdbfa8", shade=0.3)

    def nightstand(self, w, h):
        spr = self.joinery(w, h)
        lamp = self.shape(w, h, lambda d, s: d.ellipse([w * 0.22 * s, h * 0.22 * s, w * 0.78 * s, h * 0.78 * s], fill=255))
        return self.fill_tex(spr, lamp, "ceramic", "#f3ead6", shade=0.25)

    def vanity(self, w, h, basins=1):
        spr = self.canvas(w, h)
        m = self.shape(w, h, lambda d, s: d.rectangle([0, 0, w * s - 1, h * s - 1], fill=255))
        spr = self.fill_tex(spr, m, "marble", "#e6dccb", shade=0.08)
        for i in range(basins):
            cx = w * (i + 0.5) / basins
            b = self.shape(w, h, lambda d, s, cx=cx: d.ellipse([(cx - h * 0.55) * s, h * 0.2 * s, (cx + h * 0.55) * s, h * 0.85 * s], fill=255))
            spr = self.fill_tex(spr, b, "ceramic", "#fbfaf7", shade=0.45)
            t = self.shape(w, h, lambda d, s, cx=cx: d.ellipse([(cx - 1.5) * s, 1 * s, (cx + 1.5) * s, 4 * s], fill=255))
            spr = self.fill_tex(spr, t, "plain", "#6a5a48")
        return spr

    def toilet(self, w=11, h=16):
        spr = self.canvas(w, h)
        tank = self.shape(w, h, lambda d, s: d.rounded_rectangle([0, 0, w * s - 1, h * 0.28 * s], radius=2 * s, fill=255))
        spr = self.fill_tex(spr, tank, "ceramic", "#fbfaf7", shade=0.2)
        bowl = self.shape(w, h, lambda d, s: d.ellipse([w * 0.08 * s, h * 0.22 * s, w * 0.92 * s, (h - 0.5) * s], fill=255))
        spr = self.fill_tex(spr, bowl, "ceramic", "#fdfcf9", shade=0.35)
        inner = self.shape(w, h, lambda d, s: d.ellipse([w * 0.27 * s, h * 0.42 * s, w * 0.73 * s, h * 0.9 * s], fill=255))
        return self.fill_tex(spr, inner, "ceramic", "#dfe6e6", shade=0.4)

    def basin_round(self, r):
        spr = self.canvas(2 * r, 2 * r)
        m = self.shape(2 * r, 2 * r, lambda d, s: d.ellipse([0, 0, 2 * r * s - 1, 2 * r * s - 1], fill=255))
        spr = self.fill_tex(spr, m, "ceramic", "#e9e2d6", shade=0.2)
        i = self.shape(2 * r, 2 * r, lambda d, s: d.ellipse([r * 0.3 * s, r * 0.3 * s, r * 1.7 * s, r * 1.7 * s], fill=255))
        return self.fill_tex(spr, i, "ceramic", "#f8f6f1", shade=0.5)

    def shower(self, w, h):
        """Glass screen along the bottom edge, rain head, linear drain."""
        spr = self.canvas(w, h)
        g = self.shape(w, h, lambda d, s: d.rectangle([0, (h - 2) * s, w * 0.65 * s, h * s - 1], fill=255))
        spr = self.fill_tex(spr, g, "plain", "#b9d2d4")
        head = self.shape(w, h, lambda d, s: d.ellipse([w * 0.5 * s - 9 * s, h * 0.35 * s - 9 * s, w * 0.5 * s + 9 * s, h * 0.35 * s + 9 * s], outline=255, width=int(1.5 * s)))
        spr = self.fill_tex(spr, head, "plain", "#8c8a84")
        dr = self.shape(w, h, lambda d, s: d.rectangle([w * 0.15 * s, (h - 8) * s, w * 0.85 * s, (h - 6) * s], fill=255))
        spr = self.fill_tex(spr, dr, "plain", "#8c8a84")
        # pebble strip at the back (as in the bathroom render)
        peb = Image.new("L", spr.size, 0)
        d = ImageDraw.Draw(peb)
        for _ in range(int(w * 1.2)):
            x, y = self.rng.uniform(1, w - 1), self.rng.uniform(1, 6)
            r = self.rng.uniform(0.8, 1.6)
            d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=255)
        return self.fill_tex(spr, peb, "ceramic", "#d6cfc2", shade=0.3)

    def lounger(self, w=8, h=21):
        spr = self.canvas(w, h)
        f = self.shape(w, h, lambda d, s: d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=1.5 * s, fill=255))
        spr = self.fill_tex(spr, f, "wood", "#9b7250", shade=0.1)
        e = w * 0.09
        c = self.shape(w, h, lambda d, s: d.rounded_rectangle([e * s, e * s, (w - e) * s, (h - e) * s], radius=w * 0.15 * s, fill=255))
        spr = self.fill_tex(spr, c, "linen", "#f6f3ec", shade=0.25)
        self.line(spr, [(e, h * 0.33), (w - e, h * 0.33)], (205, 199, 188, 255), 1.4)
        t = self.shape(w, h, lambda d, s: d.rounded_rectangle([e * 1.4 * s, h * 0.55 * s, (w - e * 1.4) * s, h * 0.66 * s], radius=w * 0.15 * s, fill=255))
        return self.fill_tex(spr, t, "linen", "#c79a6b", shade=0.3)

    def lounge_chair(self, w=17, h=17):
        spr = self.canvas(w, h)
        f = self.shape(w, h, lambda d, s: d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=2 * s, fill=255))
        spr = self.fill_tex(spr, f, "wood", "#9b7250", shade=0.1)
        e = w * 0.12
        c = self.shape(w, h, lambda d, s: d.rounded_rectangle([e * s, h * 0.24 * s, (w - e) * s, (h - e * 0.4) * s], radius=w * 0.15 * s, fill=255))
        spr = self.fill_tex(spr, c, "boucle", "#f1ece2", shade=0.25)
        b = self.shape(w, h, lambda d, s: d.rounded_rectangle([e * 0.8 * s, e * 0.4 * s, (w - e * 0.8) * s, h * 0.3 * s], radius=w * 0.12 * s, fill=255))
        return self.fill_tex(spr, b, "boucle", "#e6dfd1", shade=0.25)

    def daybed(self, w, h):
        spr = self.canvas(w, h)
        f = self.shape(w, h, lambda d, s: d.rectangle([0, 0, w * s - 1, h * s - 1], fill=255))
        spr = self.fill_tex(spr, f, "marble", "#e3d7c1", shade=0.05)
        e = h * 0.08
        c = self.shape(w, h, lambda d, s: d.rounded_rectangle([e * s, e * s, (w - e) * s, (h - e) * s], radius=h * 0.12 * s, fill=255))
        spr = self.fill_tex(spr, c, "linen", "#f3eee4", shade=0.25)
        n = 4
        pw = (w - 2 * e) / n
        for i in range(n):
            x0 = e + i * pw
            p = self.shape(w, h, lambda d, s, x0=x0: d.rounded_rectangle([(x0 + pw * 0.08) * s, (e * 1.2) * s, (x0 + pw * 0.92) * s, h * 0.38 * s], radius=h * 0.1 * s, fill=255))
            spr = self.fill_tex(spr, p, "linen", ["#c9b394", "#e6dccb", "#b79d7c", "#e6dccb"][i], shade=0.3)
        throw = self.shape(w, h, lambda d, s: d.rectangle([w * 0.62 * s, h * 0.45 * s, w * 0.8 * s, (h - e) * s], fill=255))
        spr = self.fill_tex(spr, throw, "linen", "#b8a68c", shade=0.15)
        return spr

    def scooter(self, w=20, h=51):
        """Scooter seen from above, front at the top."""
        spr = self.canvas(w, h)
        for y0, y1 in ((0.0, 0.2), (0.8, 1.0)):  # tyres
            t = self.shape(w, h, lambda d, s, y0=y0, y1=y1: d.rounded_rectangle([w * 0.38 * s, h * y0 * s, w * 0.62 * s, h * y1 * s], radius=w * 0.1 * s, fill=255))
            spr = self.fill_tex(spr, t, "plain", "#2b2927")
        body = self.shape(w, h, lambda d, s: d.rounded_rectangle([w * 0.24 * s, h * 0.14 * s, w * 0.76 * s, h * 0.9 * s], radius=w * 0.24 * s, fill=255))
        spr = self.fill_tex(spr, body, "plain", "#d9d4ca", shade=0.35)
        board = self.shape(w, h, lambda d, s: d.rounded_rectangle([w * 0.3 * s, h * 0.3 * s, w * 0.7 * s, h * 0.48 * s], radius=w * 0.08 * s, fill=255))
        spr = self.fill_tex(spr, board, "plain", "#9a958b", shade=0.2)
        seat = self.shape(w, h, lambda d, s: d.rounded_rectangle([w * 0.3 * s, h * 0.5 * s, w * 0.7 * s, h * 0.8 * s], radius=w * 0.16 * s, fill=255))
        spr = self.fill_tex(spr, seat, "plain", "#5b4636", shade=0.25)
        bar = self.shape(w, h, lambda d, s: d.rounded_rectangle([0, h * 0.17 * s, w * s - 1, h * 0.21 * s], radius=w * 0.05 * s, fill=255))
        spr = self.fill_tex(spr, bar, "plain", "#3a3733")
        lamp = self.shape(w, h, lambda d, s: d.ellipse([w * 0.4 * s, h * 0.12 * s, w * 0.6 * s, h * 0.16 * s], fill=255))
        return self.fill_tex(spr, lamp, "plain", "#f4f1e6")

    # ---------- planting ----------
    def palm(self, r):
        w = h = 2 * r
        spr = self.canvas(w, h)
        d = ImageDraw.Draw(spr)
        n = int(self.rng.integers(8, 12))
        a0 = self.rng.uniform(0, math.tau)
        greens = [(70, 104, 52), (88, 124, 58), (104, 140, 66), (62, 92, 46)]
        for i in range(n):
            ang = a0 + i * math.tau / n + self.rng.uniform(-0.15, 0.15)
            ln = r * self.rng.uniform(0.8, 0.98)
            col = greens[i % len(greens)]
            # rachis with leaflets
            for t in np.linspace(0.12, 1.0, 22):
                px, py = r + math.cos(ang) * ln * t, r + math.sin(ang) * ln * t
                lw = (1 - t) * r * 0.32 + 1.2
                for side in (-1, 1):
                    la = ang + side * 1.05
                    qx, qy = px + math.cos(la) * lw, py + math.sin(la) * lw
                    d.line([(px * SS, py * SS), (qx * SS, qy * SS)], fill=col + (255,), width=int(2.2 * SS))
            d.line([(r * SS, r * SS), ((r + math.cos(ang) * ln) * SS, (r + math.sin(ang) * ln) * SS)], fill=(150, 160, 96, 255), width=int(1.2 * SS))
        cr = r * 0.12
        d.ellipse([(r - cr) * SS, (r - cr) * SS, (r + cr) * SS, (r + cr) * SS], fill=(96, 78, 50, 255))
        return spr

    def shrub(self, r, hue=0):
        w = h = 2 * r
        spr = self.canvas(w, h)
        d = ImageDraw.Draw(spr)
        pals = [[(58, 86, 44), (78, 110, 54), (98, 132, 64), (122, 150, 76)],
                [(52, 80, 52), (70, 102, 64), (92, 126, 78), (116, 146, 90)],
                [(76, 96, 46), (98, 120, 56), (124, 144, 70), (150, 164, 88)]][hue % 3]
        for layer, col in enumerate(pals):
            for _ in range(10 - layer * 2):
                ang, dist = self.rng.uniform(0, math.tau), self.rng.uniform(0, r * (0.6 - layer * 0.1))
                cx, cy = r + math.cos(ang) * dist - layer * 1.2, r + math.sin(ang) * dist - layer * 1.2
                lr = r * self.rng.uniform(0.25, 0.42) * (1 - layer * 0.12)
                d.ellipse([(cx - lr) * SS, (cy - lr) * SS, (cx + lr) * SS, (cy + lr) * SS], fill=col + (255,))
        # leaf veins / speckle
        arr = np.array(spr, np.float32)
        nz = self.noise(arr.shape[0], arr.shape[1], 2, 0.08)
        arr[..., :3] *= (1 + nz)[..., None]
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    def pot_plant(self, r):
        w = h = 2 * r
        spr = self.canvas(w, h)
        pot = self.shape(w, h, lambda d, s: d.ellipse([w * 0.18 * s, h * 0.18 * s, w * 0.82 * s, h * 0.82 * s], fill=255))
        spr = self.fill_tex(spr, pot, "ceramic", "#d9cbb4", shade=0.3)
        sh = self.shrub(r * 0.95, hue=1)
        spr.alpha_composite(sh, (int((w * SS - sh.width) / 2), int((h * SS - sh.height) / 2)))
        return spr

    # ---------- dispatcher ----------
    def draw(self, base, items):
        P = self.plan
        k = self.k
        for it in items:
            kind = it[0]
            if kind in ("palm", "shrub", "pot_plant", "toilet", "lounger", "lounge_chair", "basin_round", "table_round", "chair", "scooter"):
                cx, cy = P.px(it[1], it[2])
            else:
                x0, y0 = P.px(it[1], it[2])
                x1, y1 = P.px(it[3], it[4])
                cx, cy, W, H = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
            if kind == "rug":
                self.place(base, self.rug(W, H, it[5] if len(it) > 5 else "#d9cfbb"), cx, cy, shadow=0.0)
            elif kind == "sofa":
                rot = it[5]
                ww, hh = (H, W) if rot in (90, 270) else (W, H)
                self.place(base, self.sofa(ww, hh), cx, cy, rot, 0.35, 1.2)
            elif kind == "chair":
                cw, ch, rot = it[3] * k, it[4] * k, it[5]
                frame = it[6] if len(it) > 6 else None
                self.place(base, self.chair(cw, ch, frame=frame), cx, cy, rot, 0.3)
            elif kind == "table":
                self.place(base, self.table(W, H, it[5]), cx, cy, 0, 0.3)
            elif kind == "island":
                self.place(base, self.table(W, H, "#ebe4d6", "marble"), cx, cy, 0, 0.32)
            elif kind == "table_round":
                r = it[3] * k
                self.place(base, self.table_round(r, it[4] if len(it) > 4 else "#9c7350"), cx, cy, 0, 0.3)
            elif kind == "ottoman":
                self.place(base, self.ottoman(W, H), cx, cy, 0, 0.3)
            elif kind == "console":
                self.place(base, self.joinery(W, H, 1, it[5] if len(it) > 5 else "#5e4533"), cx, cy, 0, 0.25)
            elif kind == "tall_units":
                self.place(base, self.joinery(W, H, it[5]), cx, cy, 0, 0.3)
            elif kind == "counter":
                rot = it[5]
                ww, hh = (H, W) if rot in (90, 270) else (W, H)
                self.place(base, self.counter(ww, hh, it[6] if len(it) > 6 else ()), cx, cy, rot, 0.2)
            elif kind == "bed":
                rot = it[5]
                ww, hh = (H, W) if rot in (90, 270) else (W, H)
                self.place(base, self.bed(ww, hh), cx, cy, rot, 0.35, 1.2)
            elif kind == "nightstand":
                self.place(base, self.nightstand(W, H), cx, cy, 0, 0.3)
            elif kind == "desk":
                rot = it[5]
                ww, hh = (H, W) if rot in (90, 270) else (W, H)
                self.place(base, self.joinery(ww, hh, 1, "#7a5a40"), cx, cy, rot, 0.25)
            elif kind == "vanity":
                rot = it[5]
                ww, hh = (H, W) if rot in (90, 270) else (W, H)
                self.place(base, self.vanity(ww, hh, it[6] if len(it) > 6 else 1), cx, cy, rot, 0.2)
            elif kind == "toilet":
                self.place(base, self.toilet(11 * k, 16 * k), cx, cy, it[3], 0.25)
            elif kind == "basin_round":
                self.place(base, self.basin_round(it[3] * k), cx, cy, 0, 0.25)
            elif kind == "shower":
                rot = it[5]
                ww, hh = (H, W) if rot in (90, 270) else (W, H)
                self.place(base, self.shower(ww, hh), cx, cy, rot, 0.0)
            elif kind == "lounger":
                self.place(base, self.lounger(19 * k, 54 * k), cx, cy, it[3], 0.3)
            elif kind == "lounge_chair":
                self.place(base, self.lounge_chair(21 * k, 21 * k), cx, cy, it[3], 0.3)
            elif kind == "daybed":
                rot = it[5]
                ww, hh = (H, W) if rot in (90, 270) else (W, H)
                self.place(base, self.daybed(ww, hh), cx, cy, rot, 0.3)
            elif kind == "scooter":
                self.place(base, self.scooter(20 * k, 51 * k), cx, cy, it[3], 0.35)
            elif kind == "palm":
                self.place(base, self.palm(it[3] * k), cx, cy, 0, 0.4, 2.2)
            elif kind == "shrub":
                self.place(base, self.shrub(it[3] * k, int(it[4]) if len(it) > 4 else 0), cx, cy, 0, 0.35, 1.2)
            elif kind == "pot_plant":
                self.place(base, self.pot_plant(it[3] * k), cx, cy, 0, 0.35, 1.2)
        return base
