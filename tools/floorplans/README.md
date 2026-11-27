# Rendered floor plans

Generates the rendered 2D plans in `assets/floorplans/` from the architect's CAD PDF
(Villa Matteo, *Luas Bangunan*, design development 05.01.2026, sheets A.01.01–A.01.03).

```
pip install pymupdf scipy pillow numpy
python3 tools/floorplans/plans.py "<path to 2026_0109_PDF_Villa_Matteo_Luas_Bangunan.pdf>" assets/floorplans
python3 tools/floorplans/plans.py <pdf> assets/floorplans 4     # one villa only
```

Output per villa: `villa-N-{ground,second,rooftop}.webp` (web, 1400 px), `villa-N-all-floors.webp`
(the three floors side by side), and in `hires/` 300 dpi PNGs (1:100 at 300 dpi) plus a
`villa-N-all-floors.pdf` board for print.

- `render.py` reads the vector drawing, sorts paths by CAD layer (walls, furniture, hatch, …),
  fills rooms with materials, adds shadows and labels, and draws the title block.
- `plans.py` holds the crop and the room/material/label definitions for each villa and floor.
  When the architect issues a new PDF with the same sheet layout, rerun the command; if rooms
  move, adjust the coordinates (PDF points on the A3 sheet) in `plans.py`.
