# Rendered floor plans

Generates the rendered 2D plans in `assets/floorplans/` from the architect's CAD PDF
(Villa Matteo, *Luas Bangunan*, design development 05.01.2026, sheets A.01.01–A.01.03).

```
pip install pymupdf scipy pillow numpy
python3 tools/floorplans/plans.py "<path to 2026_0109_PDF_Villa_Matteo_Luas_Bangunan.pdf>" assets/floorplans
python3 tools/floorplans/plans.py <pdf> assets/floorplans 4     # one villa only
```

Output per villa (A1–A4, as in the brochure and price list): `villa-aN-{ground,second,rooftop}.webp` (web, 1400 px), `villa-aN-all-floors.webp`
(the three floors side by side), and in `hires/` 300 dpi PNGs (1:100 at 300 dpi) plus a
`villa-aN-all-floors.pdf` board for print.

- `render.py` reads the vector drawing, sorts paths by CAD layer (walls, furniture, hatch, …),
  fills rooms with materials, adds shadows and labels, and draws the title block.
- `decor.py` draws the furniture, fixtures and planting (sofas, beds, tables and chairs, kitchen,
  sanitaryware, loungers, palms and shrubs) as textured top-view sprites with soft shadows,
  placed at the positions of the CAD furniture.
- `plans.py` holds the crop and the room/material/label/furniture definitions for each villa and floor.
  Rooms are numbered on the plan and listed in the legend under the title.
  When the architect issues a new PDF with the same sheet layout, rerun the command; if rooms
  move, adjust the coordinates (PDF points on the A3 sheet) in `plans.py`.

## Materials

Matched to the Auraya renders and brochure ("lime plaster, textured paint, natural stone and Ulin wood",
"travertine bathrooms"): cream marble in French (Versailles) pattern, 30x30 / 30x60 / 60x60 / 60x90 cm,
inside and on the terrace, sunbed and roof (honed outside), greige terrazzo in bathrooms, shower and powder room, pale aqua pool and
jacuzzi, grey stone stairs, grey pavers at the parking, tropical planting in the gardens, walnut kitchen
units and wardrobes, a teak table on the roof. Materials are defined in `Plan.material()` in `render.py`
and assigned per room in `plans.py`.

Sheets carry no built-area figures (the drawing totals differ from the 145 m² used in marketing);
room sizes come from the drawing. The rooftop jacuzzi is labelled as an optional add-on.
