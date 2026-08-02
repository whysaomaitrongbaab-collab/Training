"""Refine approximate (Gemini-calibrated) pixel positions of footing/
column symbols using classical CV, instead of asking a VLM to read exact
pixel coordinates.

Two complementary techniques, both classical/deterministic:

- `snap_to_symbol_center`: for ONE rough position, crop a small local
  window, find the dark blob (the symbol's own printed outline) nearest
  the window center, and return ITS bounding-box center. This corrects
  each point independently from its own true image content -- it does
  NOT inherit bias from any other point, which is what actually fixes
  absolute position (template matching against one reference point only
  fixes RELATIVE spacing between occurrences; it can't know the true
  offset of the reference point itself, since that's exactly what's
  unknown).
- `find_all_matches` / template matching: still useful as a coarse
  "does a symbol-shaped blob exist near here at all" sanity check, kept
  for that purpose (see `refine_with_template_matching`), but
  `snap_to_symbol_center` is the one actually used for final marker
  placement in render_overlay.py.
"""
import cv2
import numpy as np


def crop_window(image_gray, center_xy, radius):
    x, y = center_xy
    h, w = image_gray.shape
    x0, y0 = max(0, int(round(x - radius))), max(0, int(round(y - radius)))
    x1, y1 = min(w, int(round(x + radius))), min(h, int(round(y + radius)))
    return image_gray[y0:y1, x0:x1], (x0, y0)


def snap_to_symbol_center(image_gray, rough_xy, search_radius=35, min_blob_area=40, max_blob_area_frac=0.6):
    """Look within `search_radius` px of `rough_xy` for the dark-outlined
    symbol's own bounding box and return its center in full-image pixel
    coordinates. Falls back to `rough_xy` unchanged if no plausible blob
    is found (e.g. the rough guess was too far off for the symbol to be
    in the search window at all) -- callers should treat that as "could
    not refine this point", not silently trust a fallback as if refined.

    Returns (refined_xy, was_refined: bool).
    """
    window, (ox, oy) = crop_window(image_gray, rough_xy, search_radius)
    if window.size == 0:
        return rough_xy, False

    # Otsu threshold: symbols are printed as black lines/hatching on a
    # white background, so a simple global threshold on this small window
    # reliably separates "ink" from "paper" without manual tuning.
    _, binary = cv2.threshold(window, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Close small gaps in the outline/hatching so the symbol forms one
    # connected blob rather than several fragments.
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    window_area = window.shape[0] * window.shape[1]
    window_cx, window_cy = window.shape[1] / 2, window.shape[0] / 2

    best = None
    best_dist = None
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_blob_area or area > window_area * max_blob_area_frac:
            continue
        bx, by, bw, bh = cv2.boundingRect(c)
        cx, cy = bx + bw / 2, by + bh / 2
        dist = (cx - window_cx) ** 2 + (cy - window_cy) ** 2
        if best_dist is None or dist < best_dist:
            best_dist, best = dist, (cx, cy)

    if best is None:
        return rough_xy, False
    return (best[0] + ox, best[1] + oy), True


def crop_template(image_gray, center_xy, half_size=28):
    """Crop a (2*half_size)x(2*half_size) patch centered on center_xy."""
    x, y = center_xy
    h, w = image_gray.shape
    x0, y0 = max(0, int(round(x - half_size))), max(0, int(round(y - half_size)))
    x1, y1 = min(w, int(round(x + half_size))), min(h, int(round(y + half_size)))
    return image_gray[y0:y1, x0:x1]


def find_all_matches(image_gray, template_gray, threshold=0.6, min_distance=20):
    """cv2.matchTemplate + greedy non-max suppression. Returns a list of
    (x, y) pixel centers of every match scoring >= threshold, strongest
    first, with no two closer together than min_distance.
    """
    if template_gray.size == 0:
        return []
    result = cv2.matchTemplate(image_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    th, tw = template_gray.shape
    ys, xs = np.where(result >= threshold)
    scored = sorted(zip(xs.tolist(), ys.tolist(), result[ys, xs].tolist()), key=lambda t: -t[2])

    kept = []
    for x, y, score in scored:
        cx, cy = x + tw / 2, y + th / 2
        if all((cx - kx) ** 2 + (cy - ky) ** 2 >= min_distance ** 2 for kx, ky in kept):
            kept.append((cx, cy))
    return kept


DEFAULT_SEARCH_RADII = (25, 35, 50, 70, 90)  # tried smallest-first; stop at the first radius that finds a symbol


def snap_to_symbol_center_progressive(image_gray, rough_xy, radii=DEFAULT_SEARCH_RADII):
    """Try snap_to_symbol_center at increasing search radii, stopping at
    the first one that finds a plausible symbol. Gemini's rough-position
    error varies point to point within a single run (observed on real
    data: some points need a 35px window, others need 70px before the
    true symbol is even inside the search window) -- starting small and
    growing only as needed avoids the failure mode of a single fixed
    radius that's either too small for the worst points or, if made
    uniformly large, wrongly latches onto a neighboring symbol/mark for
    the well-calibrated points instead of scanning wider only when it
    has to.
    """
    for radius in radii:
        refined_xy, ok = snap_to_symbol_center(image_gray, rough_xy, search_radius=radius)
        if ok:
            return refined_xy, True
    return rough_xy, False


def refine_positions(image_gray, rough_positions_by_ref, radii=DEFAULT_SEARCH_RADII):
    """Apply snap_to_symbol_center_progressive independently to every ref
    in rough_positions_by_ref. Returns (refined_by_ref, unmatched_refs) --
    unmatched refs (no symbol found at any radius tried) keep their rough
    position, unchanged.
    """
    refined = {}
    unmatched = []
    for ref, xy in rough_positions_by_ref.items():
        new_xy, ok = snap_to_symbol_center_progressive(image_gray, xy, radii=radii)
        refined[ref] = new_xy
        if not ok:
            unmatched.append(ref)
    return refined, unmatched


if __name__ == "__main__":
    # Pure self-check: synthesize a small canvas with 3 identical square
    # "symbols" at known pixel positions plus a stray thin line crossing
    # near one of them (simulating a grid dash-dot line, which real
    # symbols sit on top of). Verify snap_to_symbol_center corrects each
    # rough (deliberately offset) guess to within 1px of its TRUE center
    # independently -- unlike template matching, no shared bias between
    # points -- and that a ref with no real symbol nearby is reported as
    # unrefined rather than silently snapped to noise.
    canvas = np.full((300, 300), 255, dtype=np.uint8)
    true_centers = {"A": (60, 60), "B": (200, 60), "C": (60, 220)}
    half = 10
    for cx, cy in true_centers.values():
        cv2.rectangle(canvas, (cx - half, cy - half), (cx + half, cy + half), 0, thickness=2)
        cv2.line(canvas, (cx - half, cy - half), (cx + half, cy + half), 0, thickness=1)
    # A thin line crossing straight through B's symbol, like a real dash-dot
    # grid reference line passing through a footing mark.
    cv2.line(canvas, (150, 60), (250, 60), 180, thickness=1)

    rough = {"A": (67, 53), "B": (191, 66), "C": (54, 213), "D": (150, 150)}
    refined, unmatched = refine_positions(canvas, rough, radii=(25,))

    for ref, (tx, ty) in true_centers.items():
        rx, ry = refined[ref]
        assert abs(rx - tx) <= 1 and abs(ry - ty) <= 1, f"{ref}: refined {refined[ref]} not close to true {(tx, ty)}"
    assert unmatched == ["D"]
    assert refined["D"] == rough["D"]

    # Progressive growth: a rough guess too far off for a small radius to
    # reach the symbol at all should still get found once the radius grows
    # enough, without needing the caller to guess the right radius upfront.
    far_rough = {"A": (90, 90)}  # 30px+ from true (60,60) on both axes
    refined_small, unmatched_small = refine_positions(canvas, far_rough, radii=(15,))
    assert unmatched_small == ["A"]  # too small a radius alone: can't reach it

    refined_progressive, unmatched_progressive = refine_positions(canvas, far_rough, radii=(15, 50))
    assert unmatched_progressive == []
    rx, ry = refined_progressive["A"]
    assert abs(rx - 60) <= 1 and abs(ry - 60) <= 1

    print("symbol_template_match.py self-check: all assertions passed")
