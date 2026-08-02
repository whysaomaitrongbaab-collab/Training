"""Calibrate a meters-to-pixels transform for one drawing page, using
Gemini to read the pixel position of a handful of known grid intersections
(not one bbox per element -- far less hallucination-prone), then a plain
per-axis least-squares affine fit averaged across all of them. Everything
else in this prototype still positions elements from grid pos_m; this
module is the one bridge from "meters we trust" to "pixels on the actual
scanned page".
"""
import io
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from PIL import Image

from resolve_grid import resolve

VIEW_BBOX_PROMPT_TEMPLATE = """This image is {width}x{height} pixels (width x height), \
origin (0,0) at the top-left corner, x increasing rightward, y increasing downward.

This drawing sheet may contain MORE THAN ONE plan view side by side (for example a \
footing/column plan next to a separate beam plan). Find the bounding box of the ONE plan \
view whose caption/title (a heading, usually underlined, printed near or below the view) \
contains the words "ฐานราก" and/or "เสา" (a footing/column plan) -- for example a caption \
like "แปลนฐานรากแผ่ และฐานรากเสาเข็ม". If there is more than one view on the sheet, pick \
only this one and ignore every other view (e.g. a beam/framing plan), even though it may \
have the same-looking grid line labels.

The bounding box must include that view's entire grid (every grid line circle/label, every \
footing/column symbol, and its dimension chains) but must NOT include any other view.

Return ONLY valid JSON in exactly this shape, with real pixel numbers for this image's \
actual dimensions given above (NOT a normalized 0-1000 scale):
{{"bbox": {{"x0": <number>, "y0": <number>, "x1": <number>, "y1": <number>}}}}
(x0,y0) = top-left corner of the bounding box, (x1,y1) = bottom-right corner.
"""

CALIBRATION_PROMPT_TEMPLATE = """This image is {width}x{height} pixels (width x height), \
origin (0,0) at the top-left corner, x increasing rightward, y increasing downward.

This drawing sheet may contain MORE THAN ONE plan view side by side (for example a \
footing/column plan next to a separate beam plan), and different views on the same sheet \
often reuse the SAME grid line labels (1/2/3, D/C/B/A) independently -- each view has its \
own grid, drawn at a different position on the page. You must work only within the view \
whose title (printed as a caption/heading, usually underlined, somewhere near or below \
that view) contains the words "ฐานราก" and/or "เสา" (footing/column plan) -- for example a \
caption like "แปลนฐานรากแผ่ และฐานรากเสาเข็ม". Do NOT use a beam plan, framing plan, or any \
other view that happens to share the same grid labels elsewhere on the sheet.

Within that one footing/column view only: at every structural grid intersection there is \
a printed footing and/or column symbol (typically a small square, often hatched or \
cross-hatched). Grid reference lines (thin dash-dot lines) run through these symbols but \
the symbols themselves -- NOT the dimension text, NOT the grid line's numbered circle \
label at the edge of the sheet, NOT the dimension chain above/beside the drawing, and NOT \
any matching-looking symbol in a *different* view on the same page -- are what you must \
locate.

Find the exact pixel center of the footing/column symbol printed at each of these grid \
positions, all within that same footing/column view:
{point_list}

Report the pixel coordinates of the CENTER OF THE SYMBOL ITSELF (the actual drawn square/\
hatched mark on the floor plan), in this image's actual pixel dimensions given above (NOT \
a normalized 0-1000 scale -- real pixel numbers, e.g. a symbol near the left edge of a \
{width}px-wide image should have a small pixel_x, not a 0-1000 value).

Return ONLY valid JSON in exactly this shape, one entry per grid position listed above:
{{"points": [
  {{"grid_ref": "<id>", "pixel_x": <number>, "pixel_y": <number>}},
  ...
]}}
"""

GENERATION_CONFIG = {
    "temperature": 0,
    "max_output_tokens": 4096,
    "response_format": {"type": "text", "mime_type": "application/json"},
}

DEFAULT_CALIBRATION_REFS = ("D1", "D3", "A1", "A3")  # the 4 corners of the named grid


def _strip_markdown_fence(text):
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped[3:]
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    return stripped.strip()


def _split_grid_ref(grid_ref):
    """"D1" -> ("D", "1"), same row/column split rule as resolve_grid.resolve."""
    for i, ch in enumerate(grid_ref):
        if ch.isdigit():
            return grid_ref[:i], grid_ref[i:]
    raise ValueError(f"grid_ref {grid_ref!r} has no digit -- can't split into row/column ids")


def _require_api_key():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set (checked process env and .env). Get a key from "
            "https://aistudio.google.com/ and add it to the repo root .env file."
        )
    return api_key


def _call_gemini_json(image_source, prompt, model):
    """Send one image + text prompt to Gemini and return the parsed JSON
    response. `image_source` is anything the SDK's image `data` field
    accepts directly: a `pathlib.Path`, or an in-memory `io.BytesIO` (used
    for a cropped sub-image that was never written to disk).
    """
    client = genai.Client(api_key=_require_api_key())
    interaction = client.interactions.create(
        model=model,
        input=[
            {"type": "text", "text": prompt},
            {"type": "image", "data": image_source, "mime_type": "image/png"},
        ],
        generation_config=GENERATION_CONFIG,
    )
    text_output = ""
    for step in interaction.steps:
        if step.type == "model_output" and step.content:
            for part in step.content:
                if part.type == "text":
                    text_output += part.text
    if not text_output:
        raise RuntimeError("Gemini returned no text output.")
    return json.loads(_strip_markdown_fence(text_output))


def _rescale_if_normalized(points_by_ref, refs, image_width, image_height):
    """Gemini vision models have historically defaulted to a normalized
    0-1000 coordinate space for spatial answers unless told otherwise. The
    prompts here ask for real pixels, but detect and correct for the
    normalized convention anyway in case the model reverts to it.
    """
    all_vals = [v for ref in refs for v in points_by_ref[ref]]
    looks_normalized = image_width > 1000 and image_height > 1000 and all(0 <= v <= 1000 for v in all_vals)
    if not looks_normalized:
        return points_by_ref
    return {ref: (px * image_width / 1000, py * image_height / 1000) for ref, (px, py) in points_by_ref.items()}


def find_view_bbox(image_source, image_width, image_height, model="models/gemini-2.5-flash"):
    """Ask Gemini for the pixel bounding box of the footing/column plan
    view on a sheet that may contain multiple look-alike views. Returns
    (x0, y0, x1, y1) in this image's pixel space.
    """
    prompt = VIEW_BBOX_PROMPT_TEMPLATE.format(width=image_width, height=image_height)
    data = _call_gemini_json(image_source, prompt, model)
    b = data["bbox"]
    x0, y0, x1, y1 = b["x0"], b["y0"], b["x1"], b["y1"]
    looks_normalized = image_width > 1000 and image_height > 1000 and all(0 <= v <= 1000 for v in (x0, y0, x1, y1))
    if looks_normalized:
        x0, x1 = x0 * image_width / 1000, x1 * image_width / 1000
        y0, y1 = y0 * image_height / 1000, y1 * image_height / 1000
    return (x0, y0, x1, y1)


def crop_to_view(image_path, bbox, padding_frac=0.03):
    """Crop the source image to `bbox` (padded outward by padding_frac of
    its own width/height, clamped to the image edges) and return
    (cropped_image_bytes, crop_width, crop_height, (offset_x, offset_y)).
    Cropping out the confusable second view before calibration is what
    stops Gemini from occasionally reading a point in the wrong view --
    it can't confuse a view that isn't in frame.
    """
    with Image.open(image_path) as im:
        img_w, img_h = im.size
        x0, y0, x1, y1 = bbox
        pad_x = (x1 - x0) * padding_frac
        pad_y = (y1 - y0) * padding_frac
        x0 = max(0, x0 - pad_x)
        y0 = max(0, y0 - pad_y)
        x1 = min(img_w, x1 + pad_x)
        y1 = min(img_h, y1 + pad_y)
        cropped = im.crop((round(x0), round(y0), round(x1), round(y1)))
        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        buf.seek(0)
        return buf, cropped.width, cropped.height, (round(x0), round(y0))


def find_calibration_points(image_source, image_width, image_height, refs, model="models/gemini-2.5-flash"):
    """Ask Gemini for the pixel position of each named grid intersection in
    `refs` (2 or more), within `image_source` (a Path or in-memory image --
    see _call_gemini_json). Returns {ref: (pixel_x, pixel_y), ...} in that
    image's own pixel space, already rescaled out of Gemini's normalized
    0-1000 coordinate space if it used one.
    """
    point_list = "\n".join(
        f'{i}. Grid position "{ref}": where grid line "{_split_grid_ref(ref)[1]}" meets '
        f'grid line "{_split_grid_ref(ref)[0]}".'
        for i, ref in enumerate(refs, start=1)
    )
    prompt = CALIBRATION_PROMPT_TEMPLATE.format(width=image_width, height=image_height, point_list=point_list)
    data = _call_gemini_json(image_source, prompt, model)

    points_by_ref = {p["grid_ref"]: (p["pixel_x"], p["pixel_y"]) for p in data["points"]}
    missing = [ref for ref in refs if ref not in points_by_ref]
    if missing:
        raise RuntimeError(f"Gemini didn't return all requested points, missing {missing}: {data}")

    return _rescale_if_normalized(points_by_ref, refs, image_width, image_height)


def _fit_line_least_squares(pairs):
    """Ordinary least squares fit of pixel = m*meter + c over a list of
    (meter, pixel) pairs. With exactly 2 distinct meter values this reduces
    to the same result as solving the two points directly; with more points
    it averages out per-point read noise.
    """
    n = len(pairs)
    sum_m = sum(m for m, _ in pairs)
    sum_p = sum(p for _, p in pairs)
    sum_mm = sum(m * m for m, _ in pairs)
    sum_mp = sum(m * p for m, p in pairs)
    denom = n * sum_mm - sum_m * sum_m
    if denom == 0:
        raise ValueError("Calibration points must include at least two distinct meter values on this axis")
    slope = (n * sum_mp - sum_m * sum_p) / denom
    intercept = (sum_p - slope * sum_m) / n
    return slope, intercept


def compute_transform(ref_m_list, ref_px_list):
    """Fit an independent per-axis affine map (scale + offset, no rotation/
    skew) from N >= 2 (meters, pixels) point correspondences, via ordinary
    least squares per axis (averages out per-point noise when N > 2).
    ref_m_list/ref_px_list: parallel lists of (x_m, y_m) / (pixel_x, pixel_y)
    tuples, same length, same point order.
    Returns {"sx", "ox", "sy", "oy"} such that pixel = meter * s + o per axis.
    """
    if len(ref_m_list) != len(ref_px_list):
        raise ValueError("ref_m_list and ref_px_list must be the same length")
    if len(ref_m_list) < 2:
        raise ValueError("Need at least 2 calibration points")

    x_pairs = [(m[0], px[0]) for m, px in zip(ref_m_list, ref_px_list)]
    y_pairs = [(m[1], px[1]) for m, px in zip(ref_m_list, ref_px_list)]
    sx, ox = _fit_line_least_squares(x_pairs)
    sy, oy = _fit_line_least_squares(y_pairs)
    return {"sx": sx, "ox": ox, "sy": sy, "oy": oy}


def meter_to_pixel(x_m, y_m, transform):
    return (x_m * transform["sx"] + transform["ox"], y_m * transform["sy"] + transform["oy"])


def _median(values):
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2


UNRELIABLE_SPREAD_PX = 100  # a ref whose reads disagree by more than this across attempts gets flagged


def find_calibration_points_consensus(image_source, image_width, image_height, refs, model="models/gemini-2.5-flash", attempts=3):
    """Call find_calibration_points multiple times (Gemini's exact-pixel
    reads for this task have been observed to vary noticeably between
    separate calls, even at temperature=0) and take the per-axis, per-ref
    median across attempts -- resistant to a single outlier call in a way
    a single call or a mean never is. Returns (points_by_ref, unreliable_refs)
    where unreliable_refs lists any ref whose reads disagreed by more than
    UNRELIABLE_SPREAD_PX across attempts, so the caller can warn about it.
    """
    all_attempts = [
        find_calibration_points(image_source, image_width, image_height, refs, model=model)
        for _ in range(attempts)
    ]
    points_by_ref = {}
    unreliable_refs = []
    for ref in refs:
        xs = [a[ref][0] for a in all_attempts]
        ys = [a[ref][1] for a in all_attempts]
        points_by_ref[ref] = (_median(xs), _median(ys))
        if max(xs) - min(xs) > UNRELIABLE_SPREAD_PX or max(ys) - min(ys) > UNRELIABLE_SPREAD_PX:
            unreliable_refs.append(ref)
    return points_by_ref, unreliable_refs


def calibrate(image_path, image_width, image_height, grid, refs=DEFAULT_CALIBRATION_REFS, model="models/gemini-2.5-flash", attempts=3, crop_to_target_view=True):
    """End-to-end: (optionally) crop the page down to just the target
    footing/column view so a look-alike second view on the same sheet
    can't be confused for it, ask Gemini for every ref's pixel position
    `attempts` times within that crop (median-consensus across calls,
    since single-call reads have been observed to vary), resolve every
    ref's meter position from the gridline master, fit the transform by
    least squares across all of them, then translate the fitted pixel
    offsets back into the ORIGINAL full image's pixel space (the crop was
    only ever an input to Gemini -- the returned transform always maps
    meters to pixel coordinates on the original, uncropped page image, so
    callers can draw directly on it). Raises if any ref doesn't resolve on
    this house's grid -- that's a caller bug (picked a ref that doesn't
    exist on this sheet), not a Gemini error. Prints a warning (not an
    error) if any ref's reads disagreed too much across attempts to trust
    the median.
    """
    ref_m_by_ref = {ref: resolve(ref, grid) for ref in refs}
    unresolved = [ref for ref, m in ref_m_by_ref.items() if m is None]
    if unresolved:
        raise ValueError(f"Calibration refs must resolve on this house's grid: {unresolved}")

    if crop_to_target_view:
        bbox = find_view_bbox(Path(image_path), image_width, image_height, model=model)
        image_source, crop_w, crop_h, (offset_x, offset_y) = crop_to_view(image_path, bbox)
    else:
        image_source, crop_w, crop_h, (offset_x, offset_y) = Path(image_path), image_width, image_height, (0, 0)

    pixels_by_ref, unreliable_refs = find_calibration_points_consensus(
        image_source, crop_w, crop_h, refs, model=model, attempts=attempts
    )
    if unreliable_refs:
        print(
            f"WARNING: calibration reads for {unreliable_refs} disagreed by more than "
            f"{UNRELIABLE_SPREAD_PX}px across {attempts} attempts -- overlay accuracy may be off."
        )
    # Translate crop-space pixel reads back to the original image's pixel space.
    pixels_by_ref = {ref: (px + offset_x, py + offset_y) for ref, (px, py) in pixels_by_ref.items()}

    ref_m_list = [ref_m_by_ref[ref] for ref in refs]
    ref_px_list = [pixels_by_ref[ref] for ref in refs]
    return compute_transform(ref_m_list, ref_px_list)


if __name__ == "__main__":
    # Pure-function self-check: no Gemini call, no image I/O.

    # 2-point case: exact solve, same as the original single-pair math.
    transform = compute_transform(
        ref_m_list=[(0.0, 0.0), (10.0, 5.0)],
        ref_px_list=[(100.0, 200.0), (500.0, 400.0)],
    )
    assert transform["sx"] == 40.0  # (500-100)/(10-0)
    assert transform["ox"] == 100.0
    assert transform["sy"] == 40.0  # (400-200)/(5-0)
    assert transform["oy"] == 200.0
    assert meter_to_pixel(0.0, 0.0, transform) == (100.0, 200.0)
    assert meter_to_pixel(10.0, 5.0, transform) == (500.0, 400.0)
    assert meter_to_pixel(4.0, 2.0, transform) == (100.0 + 4 * 40.0, 200.0 + 2 * 40.0)

    # 4-point case with noisy pixel reads: least squares should land close
    # to the true underlying transform (sx=100, ox=50, sy=60, oy=80),
    # closer than any single noisy pair would, without needing every point
    # to agree exactly.
    true_sx, true_ox, true_sy, true_oy = 100.0, 50.0, 60.0, 80.0
    corners_m = [(0.0, 0.0), (7.0, 0.0), (0.0, 9.5), (7.0, 9.5)]
    noise = [(+3, -2), (-4, +1), (+1, +3), (-2, -2)]  # small synthetic per-point pixel noise
    corners_px = [
        (x_m * true_sx + true_ox + dx, y_m * true_sy + true_oy + dy)
        for (x_m, y_m), (dx, dy) in zip(corners_m, noise)
    ]
    fitted = compute_transform(corners_m, corners_px)
    assert abs(fitted["sx"] - true_sx) < 1.0
    assert abs(fitted["ox"] - true_ox) <= 2.0
    assert abs(fitted["sy"] - true_sy) < 1.0
    assert abs(fitted["oy"] - true_oy) <= 2.0

    assert _median([1, 2, 3]) == 2
    assert _median([1, 2, 3, 4]) == 2.5
    assert _median([5]) == 5

    # Consensus logic: monkeypatch find_calibration_points (in this same
    # module's global namespace -- find_calibration_points_consensus looks
    # it up there at call time) to simulate 3 separate Gemini calls, one of
    # which is a bad outlier for ref "B". The median should shrug it off,
    # and "B" should be flagged unreliable.
    fake_attempts = [
        {"A": (100.0, 200.0), "B": (300.0, 400.0)},
        {"A": (102.0, 198.0), "B": (305.0, 402.0)},
        {"A": (99.0, 201.0), "B": (900.0, 950.0)},  # outlier for B only
    ]
    call_count = {"n": 0}

    def _fake_find(image_path, w, h, refs, model="models/gemini-2.5-flash"):
        result = fake_attempts[call_count["n"]]
        call_count["n"] += 1
        return result

    _original_find = globals()["find_calibration_points"]
    globals()["find_calibration_points"] = _fake_find
    try:
        points, unreliable = find_calibration_points_consensus(
            "unused.png", 1000, 1000, ["A", "B"], attempts=3
        )
    finally:
        globals()["find_calibration_points"] = _original_find

    assert points["A"] == (100.0, 200.0)  # median of (100,102,99)/(200,198,201)
    assert unreliable == ["B"]  # B's spread (300 vs 900 = 600px) exceeds the threshold, A's doesn't

    print("pixel_calibration.py self-check: all assertions passed")
