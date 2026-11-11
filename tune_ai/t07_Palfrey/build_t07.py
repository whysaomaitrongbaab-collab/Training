#!/usr/bin/env python3
"""build_t07.py - t07 Palfrey dataset builder (pass1 + pass0 + pass2.4), every house, current GT.

Written 2026-11-11 from the read-only t07 survey. It does the work of four older stages:
t04 build_dataset_t03.gather_all_rows (pass1), t05 pass0_derive + pass0_material_list_batch (pass0),
build_t05_night.build_pass24 (pass2.4) and build_4pass (folds). It never reads a stored t04/t05 jsonl.
Read-only on json_แก้ไขแล้ว/, rawjson_ยังไม่ได้แก้ไขโดนคน/ and image/ (Rule 1); writes only below --root.

    python build_t07.py                            # default set (siamplan included, D2)
    python build_t07.py --exclude-source siamplan  # variant B (111 houses)
    python build_t07.py --root <dir>               # write somewhere else (tests); default = this folder
    python build_t07.py --selftest                 # pure helpers only, no data

Decisions D1-D13 (2026-11-11) are implemented, not re-decided. Choices this file made where the
decisions were silent (all reported in build_report.md):
  - label top-level keys are written in KEYS.json order (= the prompt example order), not GT order
  - plan rows get the GRID MASTER of their own building: master.building == plan.building, else the
    master's file tag (หน้า00b_gridline_<tag>) in the plan file name, else the หน้า00 master
  - the nested D5 scrub is sanitize_labels.scrub (one rule set); sanitize_labels.py then runs as the
    second net and has to change nothing
  - pass0 cap: water-filling per view class (classes smaller than the cap stay whole), rows inside a
    class ordered by sha256(id); pass2.4 ids end in ::<subtask>_arm24
2026-11-11 evening (Makham: "send the grid master ONE PAGE AT A TIME, beam plan first, then footing ... so Qwen
hallucinates less"):
  - gridline rows are now page-by-page (grid_incremental.py): one image + "GRID SO FAR" tail (what earlier pages
    gave) -> only the lines/levels THIS page adds. Page order: beam plan, footing plan, roof frame, other plans,
    then sections/elevations (levels). A line is added at the first page whose printed dimension rows connect it to
    what is already known (GT dimension_chains give the page of every dimension row). Origin and dummy primes are
    renumbered by CODE (merge_delta), never by the model. Masters without dimension_chains (7) or whose ids do not
    follow the spec's mechanical naming (about 9) get NO gridline rows - mixing the old one-shot format in would
    teach two behaviours. Plan rows keep the full GT master as their GRID MASTER tail (unchanged).
2026-11-11 afternoon (two decided changes that the first build had not applied):
  - gridline labels carry an optional slim grid.z_levels [{id, level_m, type}] - only entries whose own
    page (the GT entry's source page) is among that row's images, level_m numeric, type in
    datum/named/dummy (see slim_levels); the GRID MASTER tail on plan rows stays x_lines + y_lines
  - about half of the pass0 rows of houses with a usable index page get the "SHEET LIST" tail (see
    SHEET_LIST_format.md); which half = parity of sha256(row id); the 400-row cap is unchanged

Output (under --root): data_raw/{train,val}_fold{0..3}.jsonl -> sanitize -> data/ (the trainer reads
data/), manifest.json, build_report.md. Image paths are relative to the Training root.
"""
import argparse
import ast
import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent                     # tune_ai/t07_Palfrey
TR = HERE.parents[1]                                       # Training repo root
GT_ROOT = TR / "json_แก้ไขแล้ว"
RAW_ROOT = TR / "rawjson_ยังไม่ได้แก้ไขโดนคน"
IMG_ROOT = TR / "image"
TOKENIZER = TR / "tune_ai" / "t03" / "ผล_t03_run" / "lora" / "tokenizer.json"   # Qwen3.6, keeps \p{M}
CALIB_JSONL = TR / "tune_ai" / "t05_Courser" / "train_fold0.jsonl"
CALIB_EXPECT = 39220                                       # t05 train_fold0.log preflight
WORKER_PY = Path(os.environ.get("PURSON_WORKER_PY") or
                 TR.parents[1] / "งานสมบูรณ์" / "Constistant" / "server" / "purson-worker" / "worker.py")

sys.path.insert(0, str(HERE))
import sanitize_labels as SL  # noqa: E402  (same folder; the second net, and the D5 rule set)
import grid_incremental as G  # noqa: E402  (same folder; the page-by-page grid master rules, shared with the worker)

PROMPTS_DIR = HERE                                         # D12: PURSON_PROMPTS_DIR = tune_ai/t07_Palfrey
KEYS = json.loads((HERE / "pass2" / "KEYS.json").read_text(encoding="utf-8"))
assert (KEYS["gridline.grid"] == ["x_lines", "y_lines", "z_levels"]
        and KEYS["gridline.grid.z_levels"] == ["id", "level_m", "type"]), \
    "KEYS.json nested allowlist for z_levels is missing or changed"
HOUSE_DIR_RE = re.compile(r"(\d+)(บ้าน_(?:เล็ก|ใหญ่)_\d+ชั้น_\d+)")
PAGE_RE = re.compile(r"หน้า(\d+)([ab]?)")
PLAN_PATTERNS = ("beam_plan", "footing_plan", "roof_frame_plan", "etc_plan", "plan")
PLAN_SUBTASKS = {                                          # = t04 build_dataset_t03.py (column under footing)
    "plan_footing": {"types": {"footing", "pile", "pile_cap", "pedestal", "column"}},
    "plan_beam": {"types": {"beam", "tie_beam", "steel_member"},
                  "type_regex": r"(rafter|purlin|ridge|hip|valley|truss)"},
    "plan_slab": {"types": {"slab", "precast_plank_detail", "precast_plank_placement_detail"}},
}
SUBTASK_PATTERN = {"gridline": "grid_master", "plan_footing": "footing_plan", "plan_beam": "beam_plan",
                   "plan_slab": "etc_plan", "section": "section", "schedule": "schedule", "notes": "notes"}
TRAINED = ("gridline", "plan_footing", "plan_beam", "plan_slab", "section", "schedule", "notes")
TAIL_MARK = "\n\nGRID MASTER (resolved axes for this building)\n"
SHEET_MARK = "\n\nSHEET LIST (from this drawing set's index page)\n"   # pass0 tail, SHEET_LIST_format.md
Z_TYPES = ("datum", "named", "dummy")                      # the gridline prompt's z_levels vocabulary
# GT ids that are NOT a printed label: the bare number ("+0.40", "@2.05", "±0.00" - old GT convention) and
# lower-case snake slugs ("roof_ridge", "reference"); the prompt says number-only -> id null
Z_ID_NUMBER = re.compile(r"[@+\-−±]?\s*\d+(?:[.,]\d+)?")
Z_ID_SLUG = re.compile(r"[a-z][a-z_]*")
assert SHEET_MARK == SL.SHEET_MARK, "SHEET_MARK differs between build_t07.py and sanitize_labels.py"
assert G.MARK == SL.GRID_SO_FAR_MARK, "GRID SO FAR mark differs between grid_incremental.py and sanitize_labels.py"
EMPTY_STEPS_PER_MASTER = 2     # pages that add nothing: keep this many per master (teaches "nothing new" - the anti-hallucination row)
OLD_HINT = "### สิ่งที่เครื่องตรวจภาพ"
MAX_LENGTH, CAP_TOK = 47104, 6912
LIMIT = 0.95 * MAX_LENGTH
PASS0_CAP = 400
N_FOLDS, TRAIN_FOLDS = 5, (0, 1, 2, 3)
SEC_PER_ROW = (8.05, 10.13)                                # t05 measured s per row-epoch (fold0 / fold3)
SETUP_MIN = 45
EPOCHS = 1                                                 # D7

EXCLUDED_FOLDERS = {("raw", 50): ("บ้าน_เล็ก_1ชั้น_14", "same 133-page drawing set as corrected บ้าน_เล็ก_1ชั้น_13, "
                                  "extracted twice with conflicting labels (D1)")}
HOLDOUT_FOLDERS = {("raw", 58): ("บ้าน_เล็ก_1ชั้น_20", "t05 test house บ้านไทยพอเพียง3 (byte-identical PDF); "
                                 "never in any fold (D1)")}
EXPECTED = {(): (168, 40, 128), ("siamplan",): (111, 40, 71)}   # houses / corrected / raw-only
BENCH_TOKENS = ("83b8e52c", "dpt13226", "dpt13244", "dpt13250")
BENCH_INFO = ("ไทยพอเพียง3", "ไทยพอเพียง 3", "ไทยเป็นสุข3", "ไทยเป็นสุข 3")

# D8 groups by bare name (C/R numbers mapped through the survey's houses.csv)
FAMILIES = [
    ("ไทยพอเพียง C39 C40 R59-R64", ["บ้าน_เล็ก_1ชั้น_16", "บ้าน_เล็ก_1ชั้น_17", "บ้าน_เล็ก_1ชั้น_21",
                                     "บ้าน_เล็ก_1ชั้น_22", "บ้าน_เล็ก_2ชั้น_24", "บ้าน_เล็ก_2ชั้น_25",
                                     "บ้าน_เล็ก_2ชั้น_26", "บ้าน_เล็ก_2ชั้น_27"]),
    ("บ้านสำเร็จรูป C19 C23 C28 C29", ["บ้าน_เล็ก_2ชั้น_08", "บ้าน_เล็ก_1ชั้น_08", "บ้าน_เล็ก_2ชั้น_09",
                                        "บ้าน_เล็ก_2ชั้น_10"]),
    ("C04 C17 R73", ["บ้าน_เล็ก_2ชั้น_02", "บ้าน_เล็ก_2ชั้น_04", "บ้าน_เล็ก_2ชั้น_28"]),
    ("C05 C26 R76", ["บ้าน_เล็ก_2ชั้น_03", "บ้าน_เล็ก_2ชั้น_05", "บ้าน_เล็ก_2ชั้น_29"]),
    ("ห่วงใยไทยประชาสุขใจ C18 C24 R69", ["บ้าน_เล็ก_1ชั้น_12", "บ้าน_เล็ก_1ชั้น_11", "บ้าน_เล็ก_1ชั้น_23"]),
    ("C08 C09", ["บ้าน_เล็ก_1ชั้น_03", "บ้าน_เล็ก_1ชั้น_04"]),
    ("R66 R68", ["บ้าน_ใหญ่_2ชั้น_10", "บ้าน_ใหญ่_2ชั้น_12"]),
    ("_scope R72~01", ["บ้าน_เล็ก_1ชั้น_25", "บ้าน_เล็ก_1ชั้น_01"]),
    ("_scope R73~02", ["บ้าน_เล็ก_2ชั้น_28", "บ้าน_เล็ก_2ชั้น_02"]),
    ("_scope R76~03", ["บ้าน_เล็ก_2ชั้น_29", "บ้าน_เล็ก_2ชั้น_03"]),
    ("_scope R69~11", ["บ้าน_เล็ก_1ชั้น_23", "บ้าน_เล็ก_1ชั้น_11"]),
    ("_scope R63~R62", ["บ้าน_เล็ก_2ชั้น_26", "บ้าน_เล็ก_2ชั้น_25"]),
    ("_scope R68~R66", ["บ้าน_ใหญ่_2ชั้น_12", "บ้าน_ใหญ่_2ชั้น_10"]),
    ("_scope R74 R75~R71", ["บ้าน_ใหญ่_3ชั้น_04", "บ้าน_ใหญ่_4ชั้น_01", "บ้าน_ใหญ่_2ชั้น_13"]),
    ("_scope R92~R90 R91", ["บ้าน_เล็ก_1ชั้น_31", "บ้าน_เล็ก_1ชั้น_32", "บ้าน_เล็ก_1ชั้น_33"]),
    ("_scope R52~R51", ["บ้าน_เล็ก_1ชั้น_16", "บ้าน_เล็ก_1ชั้น_17"]),
    ("_scope OBEC R159~R125 (weaker: same family)", ["บ้าน_ใหญ่_1ชั้น_16", "บ้าน_ใหญ่_1ชั้น_09"]),
    ("_scope OBEC R161~R123 (weaker: same family)", ["บ้าน_ใหญ่_1ชั้น_17", "บ้าน_ใหญ่_1ชั้น_07"]),
    ("_scope OBEC R163~R128 (weaker: same family)", ["บ้าน_ใหญ่_2ชั้น_21", "บ้าน_ใหญ่_1ชั้น_11"]),
]

# final-verify regexes, written from D5 independently of sanitize_labels (a third look)
V_HOUSE = re.compile(r"บ้าน_(?:เล็ก|ใหญ่)_\d+ชั้น_\d+")
V_DATE = re.compile(r"(?<!\d)20\d\d-\d\d-\d\d(?!\d)")
V_HIST = re.compile(r"(?i:op_?fix|by[_ ]user|added[_ ]by|batch[- _]derived|reviewer|claude_output|rawjson_)"
                    r"|json_แก้ไขแล้ว|CORRECTED_|NORMALIZED|MERGED_|CASCADE_|RETRACTED|RESOLVED_|REASSESSED")
V_KEY = re.compile(r'"(?:png|doc_page|source_image|source_pages|grid_source)"\s*:')


# ── prompt loaders: copied verbatim from Constistant server/purson-worker/worker.py ────────────────
# (check_worker_parity() executes the worker's own defs against this folder and compares)
def load_common_block():
    txt = (PROMPTS_DIR / "_common.md").read_text(encoding="utf-8")
    m = re.search(r"## BLOCK START\n(.*?)\n## BLOCK END", txt, re.DOTALL)
    body = m.group(1).strip() if m else txt.strip()
    g = re.search(r"<!-- GLOSSARY START -->\n(.*?)\n<!-- GLOSSARY END -->\n", body, re.DOTALL)
    return body.replace(g.group(0), "").strip() if g else body


def load_prompt_file(path):
    txt = path.read_text(encoding="utf-8")
    m = re.search(r"## PROMPT START\n(.*?)(?:\n## PROMPT END|\Z)", txt, re.DOTALL)
    return m.group(1).strip() if m else txt.strip()


COMMON = load_common_block()
PASS0_PROMPT = load_prompt_file(PROMPTS_DIR / "pass0" / "prompt.md")


def subtask_prompt(subtask):
    f = PROMPTS_DIR / "pass2" / subtask / f"prompt_{subtask}.md"
    if not f.exists():
        return None
    return COMMON + "\n\n" + load_prompt_file(f)


PROMPTS = {s: subtask_prompt(s) for s in TRAINED}


def check_worker_parity():
    """run worker.py's loader defs on this prompt folder + check the tail/hint code it uses"""
    if not WORKER_PY.exists():
        return f"SKIPPED (worker.py not found at {WORKER_PY})"
    src = WORKER_PY.read_text(encoding="utf-8")
    tree = ast.parse(src)
    ns = {"re": re, "Path": Path, "PROMPTS_DIR": PROMPTS_DIR}
    defs = [n for n in tree.body if isinstance(n, ast.FunctionDef)
            and n.name in ("load_common_block", "load_prompt_file", "subtask_prompt")]
    assert len(defs) == 3, "worker.py loader defs not found"
    exec(compile(ast.Module(body=defs, type_ignores=[]), str(WORKER_PY), "exec"), ns)
    ns["COMMON"] = ns["load_common_block"]()
    w_pat = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                 and any(getattr(t, "id", None) == "SUBTASK_PATTERN" for t in n.targets))
    assert w_pat == SUBTASK_PATTERN, f"SUBTASK_PATTERN differs from worker.py: {w_pat}"
    for s in TRAINED:
        assert ns["subtask_prompt"](s) == PROMPTS[s], f"prompt {s} differs from the worker's assembly"
    for s in ("plan_column", "material_list", "soil_boring_log"):
        assert ns["subtask_prompt"](s) is None, f"untrained subtask {s} has a prompt file"
    assert ns["load_prompt_file"](PROMPTS_DIR / "pass0" / "prompt.md") == PASS0_PROMPT
    for needle in ('slim = {"grid": {k: grid.get(k) for k in ("x_lines", "y_lines") if k in grid}}',
                   '"\\n\\nGRID MASTER (resolved axes for this building)\\n"',
                   "json.dumps(slim, ensure_ascii=False)", 'prompt += "\\n\\n" + hint'):
        assert needle in src, f"worker.py no longer contains {needle!r}"
    return f"OK ({WORKER_PY.name}: 7 prompts + pass0 identical, SUBTASK_PATTERN equal, tail/hint code present)"


def check_prompts_clean():
    bad = {}
    for name, text in [*PROMPTS.items(), ("pass0", PASS0_PROMPT)]:
        assert text, f"prompt {name} missing"
        hits = [k for k, rx in SL.GATE.items() if rx.search(text)]
        hits += [k for k, rx in (("verify_house", V_HOUSE), ("verify_date", V_DATE), ("verify_hist", V_HIST),
                                 ("verify_key", V_KEY)) if rx.search(text)]
        if "{{" in text:
            hits.append("{{")
        if hits:
            bad[name] = hits
    assert not bad, f"forbidden text inside model-visible prompts: {bad}"


# ── small pure helpers ───────────────────────────────────────────────────────────────────────────
def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def page_key(name):
    m = PAGE_RE.search(name)
    return (int(m.group(1)), m.group(2)) if m else None


def page_png(bare, pk):
    return f"image/{bare}/{bare}_หน้า{pk[0]:02d}{pk[1]}.png"


def strip_assigned(obj):          # t04 build_dataset_t03.py, verbatim behaviour
    if isinstance(obj, dict):
        return {k: strip_assigned(v) for k, v in obj.items() if k != "element_name_assigned"}
    if isinstance(obj, list):
        return [strip_assigned(x) for x in obj]
    return obj


def type_matches(t, cfg):
    if not isinstance(t, str):
        return False
    return t in cfg["types"] or bool(cfg.get("type_regex") and re.search(cfg["type_regex"], t))


def allow(doc, sub, dropped):
    """D5 allowlist, written in KEYS.json order (= prompt example order)"""
    keep = KEYS[sub]
    dropped.update(f"{sub}.{k}" for k in doc if k not in keep)
    return {k: doc[k] for k in keep if k in doc}


def key_census(obj, c):
    if isinstance(obj, dict):
        for k, v in obj.items():
            c[k] += 1
            key_census(v, c)
    elif isinstance(obj, list):
        for v in obj:
            key_census(v, c)
    return c


def slim_lines(lines, st):
    """D4: keep id, pos_m, type (that order); drop lines whose pos_m is not a number"""
    out = []
    for ln in lines if isinstance(lines, list) else []:
        if not isinstance(ln, dict):
            st["grid_line_not_dict"] += 1
            continue
        if not is_num(ln.get("pos_m")):
            st["grid_line_pos_m_not_number"] += 1
            continue
        out.append({k: ln[k] for k in ("id", "pos_m", "type") if k in ln})
    return out


def gridline_images(bare, doc, st):
    """D4: page key from every source_pages entry (str or {'page':..}), same house, existing png,
    dedupe, page order, first 4"""
    keys = set()
    for s in doc.get("source_pages") or []:
        ref = s.get("page") if isinstance(s, dict) else s
        pk = page_key(ref) if isinstance(ref, str) else None
        if pk is None:
            st["gridline_source_unparsable"] += 1
            continue
        other = V_HOUSE.findall(ref)
        if other and any(o != bare for o in other):
            st["gridline_source_names_other_house"] += 1
        keys.add(pk)
    out = []
    for pk in sorted(keys):
        rel = page_png(bare, pk)
        if (TR / rel).exists():
            out.append(rel)
        else:
            st["gridline_source_png_missing"] += 1
    return out[:4]


def slim_levels(levels, visible, st):
    """GT grid.z_levels -> [{id, level_m, type}] for ONE gridline row. visible = page keys of that row's
    images. An entry is kept only if (a) level_m is a number, (b) its own source page is among the images
    (never teach the model to write a level it cannot see), (c) its id passes the leak gate. type outside
    datum/named/dummy (old GT: beam_top, floor, landing, ridge) is mapped to named when the level has a
    printed id, else dummy - the prompt only knows those three. Exact duplicates are dropped. GT order kept."""
    out, seen = [], set()
    for e in levels if isinstance(levels, list) else []:
        if not isinstance(e, dict):
            st["z_entry_not_dict"] += 1
            continue
        if not is_num(e.get("level_m")):
            st["z_entry_level_not_number"] += 1
            continue
        refs = e.get("source_image")
        pks = [pk for pk in (page_key(r) for r in (refs if isinstance(refs, list) else [refs]) if isinstance(r, str)) if pk]
        if not pks:
            st["z_entry_no_source_page"] += 1
            continue
        if not any(pk in visible for pk in pks):
            st["z_entry_source_page_not_in_images"] += 1
            continue
        lid = e.get("id")
        lid = lid if isinstance(lid, str) and lid.strip() else None
        if lid is not None and SL.BAD.search(lid):
            st["z_entry_id_flagged"] += 1
            continue
        if lid is not None and Z_ID_NUMBER.fullmatch(lid.strip()):
            st["z_id_number_only_to_null"] += 1
            lid = None
        elif lid is not None and Z_ID_SLUG.fullmatch(lid.strip()):
            st["z_id_slug_to_null"] += 1
            lid = None
        typ = e.get("type")
        if typ not in Z_TYPES:
            st[f"z_type_mapped:{typ}"] += 1
            typ = "named" if lid is not None else "dummy"
        elif typ == "named" and lid is None:                 # the prompt: named = a labelled level; no label = dummy
            st["z_type_named_without_id_to_dummy"] += 1
            typ = "dummy"
        ent = {"id": lid, "level_m": e["level_m"], "type": typ}
        key = json.dumps(ent, ensure_ascii=False)
        if key in seen:
            st["z_entry_duplicate"] += 1
            continue
        seen.add(key)
        out.append(ent)
    return out


def sheet_list_of(docs, st):
    """pass0 SHEET LIST of one house: the lowest-numbered index page whose sections carry `sheet_range`
    -> (file name, [{"title", "sheet_range"}]) in index order. Only those two fields (printed on the index
    page; never doc_page numbers); entries without a title are dropped; a missing/blank sheet_range is None."""
    for name, doc, pk in sorted(docs, key=lambda x: (x[2], x[0])):
        secs = doc.get("sections")
        if doc.get("pattern") != "index" or not isinstance(secs, list) \
                or not any(isinstance(s, dict) and "sheet_range" in s for s in secs):
            continue
        out = []
        for s in secs:
            t = s.get("title") if isinstance(s, dict) else None
            if not isinstance(t, str) or not t.strip():
                st["sheet_list_entry_dropped_no_title"] += 1
                continue
            r = s.get("sheet_range")
            if r is not None and not (isinstance(r, str) and r.strip()):
                st["sheet_list_range_not_string_or_blank"] += 1
            out.append({"title": t, "sheet_range": r if isinstance(r, str) and r.strip() else None})
        if out:
            return name, out
    return None, None


def sheet_tail(entries):
    return SHEET_MARK + json.dumps(entries, ensure_ascii=False)


def grid_tail(gridline_label):
    grid = gridline_label["grid"]                           # worker.py, character for character
    slim = {"grid": {k: grid.get(k) for k in ("x_lines", "y_lines") if k in grid}}
    return TAIL_MARK + json.dumps(slim, ensure_ascii=False)


def master_for(masters, doc, fname):
    """the GRID MASTER of the plan's own building (D4): building field, then file tag, then หน้า00"""
    if not masters:
        return None, "no_master"
    if len(masters) == 1:
        return masters[0], "only_master"
    b = doc.get("building")
    hits = [m for m in masters if isinstance(b, str) and b and m["building"] == b]
    if len(hits) == 1:
        return hits[0], "by_building_field"
    hits = [m for m in masters if m["tag"] and m["tag"] in fname]
    if len(hits) == 1:
        return hits[0], "by_file_tag"
    main = [m for m in masters if m["pk"] == (0, "")]
    assert len(main) == 1, f"no single หน้า00 master for {fname}"
    return main[0], "default_main_master"


def strat_cap(rows, cls_of, cap):
    """water-filling: per-class quota c (classes <= c stay whole), leftover 1 each to the largest
    classes; inside a class rows go by sha256(id). Deterministic."""
    by = defaultdict(list)
    for r in rows:
        by[cls_of(r)].append(r)
    for k in by:
        by[k].sort(key=lambda r: sha256_text(r["id"]))
    if len(rows) <= cap:
        return [r for k in sorted(by) for r in by[k]], {k: (len(v), len(v)) for k, v in sorted(by.items())}
    lo, hi = 0, max(len(v) for v in by.values())
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if sum(min(len(v), mid) for v in by.values()) <= cap:
            lo = mid
        else:
            hi = mid - 1
    quota = {k: min(len(v), lo) for k, v in by.items()}
    spare = cap - sum(quota.values())
    for k in sorted((k for k in by if len(by[k]) > lo), key=lambda k: (-len(by[k]), k))[:spare]:
        quota[k] += 1
    keep = [r for k in sorted(by) for r in by[k][:quota[k]]]
    return keep, {k: (len(by[k]), quota[k]) for k in sorted(by)}


def build_groups(houses, families):
    parent = {h: h for h in houses}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    evidence, missing = defaultdict(list), []
    for name, members in families:
        present = [m for m in members if m in parent]
        missing += [(name, m) for m in members if m not in parent]
        for m in present[1:]:
            a, b = find(present[0]), find(m)
            if a != b:
                parent[max(a, b)] = min(a, b)
        if len(present) > 1:
            evidence[present[0]].append(name)
    groups = defaultdict(list)
    for h in sorted(houses):
        groups[find(h)].append(h)
    out = []
    for g in sorted(groups.values(), key=lambda g: g[0]):
        ev = sorted({e for h in g for e in evidence.get(h, [])})
        out.append({"members": g, "evidence": ev})
    return out, missing


def assign_folds(groups, rows_of_house, k=N_FOLDS):
    """D8: deterministic greedy - biggest group first, into the fold with the fewest rows"""
    totals, fold_of = [0] * k, {}
    order = sorted(groups, key=lambda g: (-sum(rows_of_house.get(h, 0) for h in g["members"]), g["members"][0]))
    for g in order:
        i = min(range(k), key=lambda j: (totals[j], j))
        for h in g["members"]:
            fold_of[h] = i
        g["fold"] = i
        totals[i] += sum(rows_of_house.get(h, 0) for h in g["members"])
    return fold_of, totals


# ── houses (D1, D2) ──────────────────────────────────────────────────────────────────────────────
def enumerate_houses(exclude_sources):
    found, exclusions, holdouts = {}, [], []
    for tree, root in (("corrected", GT_ROOT), ("raw", RAW_ROOT)):
        seen = {}
        for d in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name):
            m = HOUSE_DIR_RE.fullmatch(d.name)
            if not m:
                exclusions.append({"tree": tree, "folder": d.name, "house": None, "reason": "not a house folder"})
                continue
            no, bare = int(m.group(1)), m.group(2)
            assert bare not in seen, f"duplicate house {bare} in {tree}: {seen[bare]['folder']} / {d.name}"
            scope_doc = None
            if (d / "_scope.json").exists():
                scope_doc = json.loads((d / "_scope.json").read_text(encoding="utf-8"))
            design = (scope_doc or {}).get("house_design")
            whole = json.dumps(scope_doc, ensure_ascii=False).lower() if scope_doc else ""
            siam = isinstance(design, str) and "siamplan" in design.lower()
            assert siam == ("siamplan" in whole), f"siamplan mentioned outside house_design only: {d.name}"
            seen[bare] = {"tree": tree, "folder": d.name, "no": no, "house": bare, "dir": d,
                          "files": sorted(f.name for f in d.glob("*.json") if not f.name.startswith("_")),
                          "scope": (scope_doc or {}).get("scope") or "full",
                          "source": "siamplan" if siam else "non-siamplan"}
        found[tree] = seen
    houses = {}
    for bare, info in found["corrected"].items():
        assert bare in found["raw"], f"corrected house {bare} has no raw copy"
        assert info["files"], f"corrected house {bare} has no data JSON"
        r = found["raw"][bare]
        exclusions.append({"tree": "raw", "folder": r["folder"], "house": bare,
                           "reason": f"superseded: the json_แก้ไขแล้ว copy {info['folder']} wins (D1)"})
        houses[bare] = info
    for bare, info in found["raw"].items():
        if bare in found["corrected"]:
            continue
        key = ("raw", info["no"])
        if not info["files"]:
            exclusions.append({"tree": "raw", "folder": info["folder"], "house": bare, "reason": "no data JSON (D1)"})
        elif key in EXCLUDED_FOLDERS:
            assert EXCLUDED_FOLDERS[key][0] == bare, f"folder number moved: {key} is {bare}"
            exclusions.append({"tree": "raw", "folder": info["folder"], "house": bare, "reason": EXCLUDED_FOLDERS[key][1]})
        elif key in HOLDOUT_FOLDERS:
            assert HOLDOUT_FOLDERS[key][0] == bare, f"folder number moved: {key} is {bare}"
            holdouts.append({"tree": "raw", "folder": info["folder"], "house": bare, "reason": HOLDOUT_FOLDERS[key][1]})
        else:
            houses[bare] = info
    for k, (bare, _) in [*EXCLUDED_FOLDERS.items(), *HOLDOUT_FOLDERS.items()]:
        assert found["raw"].get(bare, {}).get("no") == k[1], f"{bare} is not raw folder {k[1]}"
    all_houses = dict(sorted(houses.items()))
    n_siam = sum(1 for h in all_houses.values() if h["source"] == "siamplan")
    assert n_siam == 57 and all(h["tree"] == "raw" for h in all_houses.values() if h["source"] == "siamplan"), \
        f"expected 57 siamplan raw-only houses, found {n_siam}"
    for bare in list(houses):
        if houses[bare]["source"] in exclude_sources:
            info = houses.pop(bare)
            exclusions.append({"tree": info["tree"], "folder": info["folder"], "house": bare,
                               "reason": f"--exclude-source {info['source']} (D2 variant)"})
    houses = dict(sorted(houses.items()))
    n_c = sum(1 for h in houses.values() if h["tree"] == "corrected")
    got = (len(houses), n_c, len(houses) - n_c)
    want = EXPECTED[tuple(sorted(exclude_sources))]
    assert got == want, f"house count {got} != expected {want} (D1) - stop and explain before training"
    for bare in houses:
        assert (IMG_ROOT / bare).is_dir(), f"image/{bare}/ missing"
    for bare in BENCH_TOKENS + tuple(h["house"] for h in holdouts):
        assert bare not in houses, f"bench/held-out house {bare} in the house set"
    return houses, all_houses, exclusions, holdouts


# ── rows ─────────────────────────────────────────────────────────────────────────────────────────
def make_row(bare, stem, kind, sub, images, text, label):
    return {"id": f"{bare}::{stem}::{kind}", "house": bare, "subtask": sub,
            "messages": [{"role": "user", "content": [{"type": "image", "image": p} for p in images]
                          + [{"type": "text", "text": text}]},
                         {"role": "assistant", "content": [{"type": "text",
                                                            "text": json.dumps(label, ensure_ascii=False)}]}]}


class Builder:
    def __init__(self):
        self.st = Counter()            # routing/skip counters
        self.scrub = Counter()         # sanitize_labels.scrub stats
        self.dropped_keys = Counter()  # top-level keys removed by the allowlist
        self.lost_nested = Counter()   # nested key occurrences removed by the scrub
        self.leak_before = Counter()   # rows whose label had a gate hit before the scrub
        self.master_route = Counter()
        self.notes_elements_dropped = [0, 0]
        self.p0_classes = {}
        self.z_rows = Counter()        # gridline rows (with images) by z outcome
        self.z_gt_entries = self.z_kept_entries = 0
        self.sheet_list_houses = {}    # house -> (index file the SHEET LIST came from, entries)
        self.full_tails = defaultdict(set)   # house -> GRID MASTER tails of its FULL ground-truth masters (plan-row tails)
        self.inc = Counter()           # page-by-page gridline counters (incremental_rows)
        self.inc_masters = []          # one dict per master that produced rows

    def incremental_rows(self, bare, mstem, doc, lab, pat_of_page):
        """page-by-page gridline rows of ONE master (rules: grid_incremental.py). lab = the cleaned full master label.
        Returns [] (and counts why) when the master cannot be cut honestly - it then has NO gridline rows at all."""
        inc = self.inc
        inc["masters_seen"] += 1
        g = doc.get("grid") if isinstance(doc.get("grid"), dict) else {}
        chains = g.get("dimension_chains") if isinstance(g.get("dimension_chains"), list) else []
        if not chains:
            inc["skip_no_dimension_chains"] += 1
            return []
        gt = {"x": lab["grid"]["x_lines"], "y": lab["grid"]["y_lines"]}
        keyset = lambda ls: {(l["id"], round(l["pos_m"], 3), l["type"]) for l in ls}  # noqa: E731
        for ax in ("x", "y"):
            if any(l.get("type") not in ("named", "dummy") for l in gt[ax]):
                inc["skip_line_without_named_or_dummy_type"] += 1
                return []
            named = [l["pos_m"] for l in gt[ax] if l["type"] == "named"]
            if keyset(G.reprime(gt[ax])) != keyset(gt[ax]) or (named and abs(min(named)) > G.EPS):
                inc["skip_gt_ids_or_origin_not_the_spec_rule"] += 1
                return []
        by_page = defaultdict(list)                          # page -> its dimension rows (axis + from/to pairs)
        for c in chains:
            src = c.get("source_image") if isinstance(c, dict) else None
            pk = page_key(src) if isinstance(src, str) else None
            if c.get("axis") not in ("x", "y") or not pk or not (TR / page_png(bare, pk)).exists():
                inc["chain_rows_dropped_page_not_usable"] += 1
                continue
            by_page[pk].append({"axis": c["axis"], "segments": [(s.get("from"), s.get("to")) for s in c.get("segments") or []
                                                                 if isinstance(s, dict)]})
        zl = g.get("z_levels")
        levels, zpages = {}, set()
        for e in zl if isinstance(zl, list) else []:
            refs = e.get("source_image") if isinstance(e, dict) else None
            for r in refs if isinstance(refs, list) else [refs]:
                k = page_key(r) if isinstance(r, str) else None
                if k and (TR / page_png(bare, k)).exists():
                    zpages.add(k)
        for k in zpages:
            levels[k] = slim_levels(zl, {k}, Counter())      # per-page throwaway counters; the master-level numbers come from row_levels
        src_pages = set()
        for s in doc.get("source_pages") or []:
            ref = s.get("page") if isinstance(s, dict) else s
            k = page_key(ref) if isinstance(ref, str) else None
            if k and (TR / page_png(bare, k)).exists():
                src_pages.add(k)
        allp = set(by_page) | zpages | src_pages
        if not allp:
            inc["skip_no_page_with_an_image"] += 1
            return []
        order = G.page_order([(min(pat_of_page[p], key=G.class_rank) if pat_of_page.get(p) else None, p) for p in allp])
        steps, left = G.derive_steps([{"page": p, "chains": by_page.get(p, [])} for _, p in order], gt, levels)
        has = lambda s: any(s["delta"][k] for k in ("x_lines", "y_lines", "z_levels"))  # noqa: E731
        # independent replay with the plain merge function (what the worker does): must reproduce every state shown
        # and end on the ground-truth lines the pages reached
        st, renum = G.new_state(), 0
        for s in steps:
            if G.state_json(st) != G.state_json(s["state_before"]):
                inc["skip_replay_state_mismatch"] += 1
                return []
            st, cnt = G.merge_delta(st, s["delta"])
            renum += cnt.get("known_lines_renumbered", 0)
        reached = {ax: [l for l in gt[ax] if l["id"] not in set(left[ax])] for ax in ("x", "y")}
        for ax, key in (("x", "x_lines"), ("y", "y_lines")):
            if keyset(G.reprime(G.reorigin(reached[ax]))) != keyset(st[key]):
                inc["skip_replay_final_differs_from_gt"] += 1
                return []
        self.row_levels(doc, set(zpages))                    # master-level z numbers for the report (entry counters -> self.st)
        n_gt = len(gt["x"]) + len(gt["y"])
        n_left = len(left["x"]) + len(left["y"])
        empties = sorted((i for i, s in enumerate(steps, 1) if not has(s)),
                         key=lambda i: sha256_text(f"{bare}::{mstem}::s{i:02d}"))[:EMPTY_STEPS_PER_MASTER]
        keep = {i for i, s in enumerate(steps, 1) if has(s)} | set(empties)
        conf = doc.get("confidence_score") if is_num(doc.get("confidence_score")) else None
        rows = []
        for i, s in enumerate(steps, 1):
            if i not in keep:
                continue
            grid = {"x_lines": s["delta"]["x_lines"], "y_lines": s["delta"]["y_lines"]}
            if s["delta"]["z_levels"]:
                grid["z_levels"] = s["delta"]["z_levels"]
            # confidence_flags are the master's audit notes, not a property of one page - not copied onto page rows
            label = self.clean({"pattern": "grid_master", "grid": grid, "confidence_score": conf,
                                "confidence_flags": [], "warnings": []}, "gridline", "pass1")
            text = PROMPTS["gridline"] + G.tail(s["state_before"])
            rows.append(make_row(bare, f"{mstem}__s{i:02d}", "gridline", "gridline", [page_png(bare, s["page"])], text, label))
            inc["rows_nonempty" if has(s) else "rows_empty_kept"] += 1
        inc["masters_used"] += 1
        inc["steps_total"] += len(steps)
        inc["steps_nonempty"] += sum(1 for s in steps if has(s))
        inc["steps_empty_dropped"] += sum(1 for i, s in enumerate(steps, 1) if not has(s) and i not in keep)
        inc["gt_lines"] += n_gt
        inc["gt_lines_no_page_adds_them"] += n_left
        inc["known_lines_renumbered_by_code"] += renum
        inc["named_lines_left_of_the_origin"] += sum(1 for s in steps for ax in ("x_lines", "y_lines")
                                                     for l in s["delta"][ax] if l["type"] == "named" and l["pos_m"] < 0)
        self.inc_masters.append({"house": bare, "master": mstem, "steps": len(steps),
                                 "nonempty": sum(1 for s in steps if has(s)), "rows": len(rows),
                                 "gt_lines": n_gt, "left_over": n_left})
        return rows

    def clean(self, label, sub, kind):
        """D5 nested scrub (sanitize_labels.scrub) + element-count guard"""
        before = json.dumps(label, ensure_ascii=False)
        self.leak_before.update((kind, h) for h in SL._hits(before))
        out = SL.scrub(label, self.scrub)
        assert SL.n_elements(out) == SL.n_elements(label), f"{sub}: scrub removed elements"
        c0, c1 = key_census(label, Counter()), key_census(out, Counter())
        self.lost_nested.update({f"{sub}.{k}": v - c1[k] for k, v in c0.items() if v > c1[k]})
        return out

    def row_levels(self, doc, visible):
        """slim z_levels for one gridline row + the row-level and entry-level counters of the 2026-11-11 report"""
        gt = (doc.get("grid") or {}).get("z_levels")
        zst = Counter()
        z = slim_levels(gt, visible, zst)
        self.st.update(zst)                                  # entry-level counters (z_entry_*, z_type_mapped:*)
        self.z_gt_entries += len(gt) if isinstance(gt, list) else 0
        self.z_kept_entries += len(z)
        if z:
            self.z_rows["with_z" + ("_partial" if sum(v for k, v in zst.items() if k.startswith("z_entry_")) else "_all_entries")] += 1
        elif not isinstance(gt, list):
            self.z_rows["no_z_gt_has_no_z_levels"] += 1
        elif not gt:
            self.z_rows["no_z_gt_z_levels_empty"] += 1
        elif zst["z_entry_source_page_not_in_images"]:
            self.z_rows["no_z_levels_page_not_among_row_images"] += 1
        elif zst["z_entry_level_not_number"]:
            self.z_rows["no_z_no_numeric_level_m"] += 1
        else:
            self.z_rows["no_z_other"] += 1
        return z

    def house_rows(self, h):
        bare, d = h["house"], h["dir"]
        docs = []
        for name in h["files"]:
            doc = json.loads((d / name).read_text(encoding="utf-8"))
            assert isinstance(doc, dict), f"{d.name}/{name} is not a JSON object"
            pk = page_key(name)
            assert pk and name.startswith(f"{bare}_หน้า"), f"unexpected GT file name {d.name}/{name}"
            docs.append((name, doc, pk))
        # grid masters (one per หน้า00 / หน้า00b file)
        masters = []
        pat_of_page = defaultdict(set)                      # page -> patterns of the (non-master) files on it
        for name, doc, pk in docs:
            if pk and doc.get("pattern") not in ("grid_master", "gridline"):
                pat_of_page[pk].add(doc.get("pattern"))
        for name, doc, pk in docs:
            if doc.get("pattern") in ("grid_master", "gridline"):
                # the FULL master (x/y only) - what plan rows carry as their GRID MASTER tail; the gridline rows
                # themselves are page-by-page (incremental_rows)
                grid = {"x_lines": slim_lines((doc.get("grid") or {}).get("x_lines"), self.st),
                        "y_lines": slim_lines((doc.get("grid") or {}).get("y_lines"), self.st)}
                lab = self.clean({"pattern": "grid_master", "grid": grid,
                                  "confidence_score": doc.get("confidence_score") if is_num(doc.get("confidence_score")) else None,
                                  "confidence_flags": list(doc["confidence_flags"]) if isinstance(doc.get("confidence_flags"), list) else [],
                                  "warnings": []}, "gridline", "pass1")
                tag = name[:-5].split("_gridline_", 1)[1] if "_gridline_" in name else None
                masters.append({"name": name, "stem": name[:-5], "pk": pk, "label": lab, "tail": grid_tail(lab),
                                "building": doc.get("building"), "tag": tag, "doc": doc})
                self.full_tails[bare].add(grid_tail(lab))
        assert sum(1 for m in masters if m["pk"] == (0, "")) <= 1, f"{bare}: several หน้า00 masters"
        pass1 = []
        for m in masters:
            pass1 += self.incremental_rows(bare, m["stem"], m["doc"], m["label"], pat_of_page)
        for name, doc, pk in docs:
            pat, disc, stem = doc.get("pattern"), doc.get("discipline"), name[:-5]
            if pat in ("grid_master", "gridline"):
                continue
            img = page_png(bare, pk)
            if pat in PLAN_PATTERNS and disc == "structural":
                views = doc.get("views")
                assert not (isinstance(views, list) and any(isinstance(v, dict) and v.get("elements") for v in views)), \
                    f"{bare}/{name}: views[].elements on a plan file - the allowlist would drop them"
                if isinstance(views, list) and views and all(isinstance(v, str) for v in views):
                    self.st["plan_files_string_views (t04 views bug)"] += 1
                if not (TR / img).exists():
                    self.st["skip_plan_no_image"] += 1
                    continue
                master, how = master_for(masters, doc, name)
                tail = master["tail"] if master else ""
                els = doc.get("elements") if isinstance(doc.get("elements"), list) else []
                made = 0
                for sub, cfg in PLAN_SUBTASKS.items():
                    fe = [e for e in els if isinstance(e, dict) and type_matches(e.get("element_type"), cfg)]
                    if not fe:
                        continue
                    lab = strip_assigned({**doc, "elements": fe, "pattern": SUBTASK_PATTERN[sub]})
                    lab = self.clean(allow(lab, sub, self.dropped_keys), sub, "pass1")
                    pass1.append(make_row(bare, stem, sub, sub, [img], PROMPTS[sub] + tail, lab))
                    self.master_route[how] += 1
                    made += 1
                if not made:
                    self.st["skip_plan_no_matching_elements"] += 1
            elif pat in ("section", "schedule", "notes"):
                if not (TR / img).exists():
                    self.st["skip_no_image"] += 1
                    continue
                if pat == "notes" and isinstance(doc.get("elements"), list) and doc["elements"]:
                    self.notes_elements_dropped[0] += 1
                    self.notes_elements_dropped[1] += len(doc["elements"])
                lab = self.clean(allow(strip_assigned(doc), pat, self.dropped_keys), pat, "pass1")
                pass1.append(make_row(bare, stem, pat, pat, [img], PROMPTS[pat], lab))
            elif pat == "material_list":
                self.st["not_pass1_material_list"] += 1
            else:
                self.st[f"not_pass1_pattern:{pat}"] += 1
        # pass2.4 (D6): single-image plan rows + current-format _hint25.txt, same text part (worker parity)
        pass24 = []
        for r in pass1:
            if not r["subtask"].startswith("plan_"):
                continue
            imgs = [c["image"] for c in r["messages"][0]["content"] if c["type"] == "image"]
            if len(imgs) != 1:
                continue
            hp = TR / imgs[0].replace(".png", "_hint25.txt")
            if not hp.exists():
                continue
            hint = hp.read_text(encoding="utf-8")                   # verbatim, like worker crop_for_task
            if hint.startswith(OLD_HINT):
                self.st["skip_pass24_old_format_hint"] += 1
                continue
            if not hint:
                self.st["skip_pass24_empty_hint"] += 1
                continue
            if SL.BAD.search(hint):
                self.st["pass24_hint_with_gate_hit"] += 1
            text = r["messages"][0]["content"][-1]["text"] + "\n\n" + hint
            _, stem, sub = r["id"].split("::")
            pass24.append({**r, "id": f"{bare}::{stem}::{sub}_arm24",
                           "messages": [{"role": "user", "content": [{"type": "image", "image": imgs[0]},
                                                                     {"type": "text", "text": text}]},
                                        r["messages"][1]]})
        pass0 = self.pass0_rows(h, docs) if h["scope"] == "full" else []
        return pass1, pass0, pass24

    def pass0_rows(self, h, docs):
        """port of t05 pass0_derive + pass0_material_list_batch, D6 guards, no script-note warnings"""
        bare = h["house"]
        direct = {"grid_master": "gridline", "gridline": "gridline", "footing_plan": "plan_footing",
                  "beam_plan": "plan_beam", "roof_frame_plan": "plan_beam", "section": "section",
                  "schedule": "schedule", "notes": "notes", "material_list": "material_list", "title": "title",
                  "index": "index", "symbol": "symbol", "misc": "misc", "site_plan": "site_plan",
                  "side_profile": "side_profile", "roof_plan": "roof_plan"}
        type_to_plan = {"beam": "plan_beam", "tie_beam": "plan_beam", "rafter": "plan_beam", "purlin": "plan_beam",
                        "slab": "plan_slab", "precast_plank_detail": "plan_slab", "footing": "plan_footing",
                        "pile_cap": "plan_footing", "pile": "plan_footing", "pedestal": "plan_footing",
                        "column": "plan_column"}

        def elements_of(d):
            els = list(d["elements"]) if isinstance(d.get("elements"), list) else []
            for v in d["views"] if isinstance(d.get("views"), list) else []:
                if isinstance(v, dict) and isinstance(v.get("elements"), list):
                    els += v["elements"]
            return [e for e in els if isinstance(e, dict)]

        def views_for(pat, d):
            gl = any(e.get("grid_refs") or e.get("grid_ref_start") for e in elements_of(d)) or pat == "side_profile"
            if pat in direct:
                return [{"subtask": direct[pat], "where": "full", "also_gridline": gl}]
            if pat in ("etc_plan", "plan"):
                subs = sorted({type_to_plan[e.get("element_type")] for e in elements_of(d)
                               if e.get("element_type") in type_to_plan})
                return [{"subtask": s, "where": "full", "also_gridline": gl} for s in subs] or None
            return None

        def building_of(fname):
            for t in ("สุขา", "ศาลา", "โรงจอด"):
                if t in fname:
                    return t
            return "main"

        # SHEET LIST tail (2026-11-11): this house's index page, appended to about half of its pass0 rows
        sl_name, sl_entries = sheet_list_of(docs, self.st)
        sl_tail = None
        if sl_entries:
            sl_tail = sheet_tail(sl_entries)
            if SL.BAD.search(sl_tail):                        # house name / file name / edit history -> no tail
                self.st["pass0_sheet_list_house_dropped_flagged_text"] += 1
                sl_tail = None
            else:
                self.sheet_list_houses[bare] = (sl_name, len(sl_entries))
        else:
            self.st["pass0_sheet_list_house_without_usable_index"] += 1

        pages = defaultdict(list)
        for name, doc, pk in docs:
            pages[pk].append((name, doc))
        rows = []
        for pk in sorted(pages):
            items = pages[pk]
            if pk[0] == 0:
                self.st["pass0_skip_page_00"] += 1
                continue
            img = page_png(bare, pk)
            if not (TR / img).exists():
                self.st["pass0_skip_no_image"] += 1
                continue
            if len(items) > 1:
                lab = self.material_list_label(items)
                if lab is None:
                    self.st["pass0_skip_multi_file_page"] += 1
                    continue
                self.st["pass0_material_list_2sheet"] += 1
            else:
                name, d = items[0]
                if re.search(r"_view\d", name):
                    self.st["pass0_skip_only_viewN_fragment"] += 1
                    continue
                vs = views_for(d.get("pattern"), d)
                if vs is None:
                    self.st["pass0_skip_pattern_underivable"] += 1
                    continue
                lab = {"sheet_code": d.get("sheet_code"), "sheet_name": d.get("sheet_name"),
                       "discipline": d.get("discipline"), "building": building_of(name), "views": vs,
                       "confidence_score": 1.0, "warnings": []}
            lab = self.clean(allow(lab, "pass0", self.dropped_keys), "pass0", "pass0")
            stem = f"หน้า{pk[0]:02d}{pk[1]}"
            text = PASS0_PROMPT
            if sl_tail:                                       # even parity of sha256(row id) -> with the list
                with_list = int(sha256_text(f"{bare}::{stem}::pass0"), 16) % 2 == 0
                self.st["pass0_candidate_rows_sheet_list_" + ("yes" if with_list else "no")] += 1
                if with_list:
                    text += sl_tail
            rows.append(make_row(bare, stem, "pass0", "pass0", [img], text, lab))
        return rows

    @staticmethod
    def material_list_label(items):
        """t05 rule: exactly 2 files, both material_list, sheet numbers readable and different
        (lower sheet = right half). The t05 warnings were script notes -> none here (D6)."""
        if len(items) != 2 or any(d.get("pattern") != "material_list" for _, d in items):
            return None
        parsed = []
        for _, d in items:
            m = re.search(r"(\d+)\s*/\s*(\d+)", d.get("sheet_code") or "")
            if not m:
                return None
            parsed.append((int(m.group(1)), d))
        if parsed[0][0] == parsed[1][0]:
            return None
        lo = min(parsed, key=lambda x: x[0])[1]
        return {"sheet_code": lo.get("sheet_code"), "sheet_name": lo.get("sheet_name"),
                "discipline": lo.get("discipline") or "material_list", "building": "main",
                "views": [{"subtask": "material_list", "where": "right", "also_gridline": False},
                          {"subtask": "material_list", "where": "left", "also_gridline": False}],
                "confidence_score": 0.85, "warnings": []}


# ── tokens (t05 trainer preflight arithmetic) ─────────────────────────────────────────────────────
class TokenCounter:
    def __init__(self):
        from tokenizers import Tokenizer
        self.tok = Tokenizer.from_file(str(TOKENIZER))
        self.tok.no_truncation()
        self.tok.no_padding()
        self.sizes = {}

    def size(self, rel):
        if rel not in self.sizes:
            from PIL import Image
            with Image.open(TR / rel) as im:
                self.sizes[rel] = im.size
        return self.sizes[rel]

    def row(self, r):
        vis = txt = 0
        for c in r["messages"][0]["content"]:
            if c["type"] == "image":
                w, h = self.size(c["image"])
                vis += min(w * h // 1024, CAP_TOK)
            else:
                txt += len(self.tok.encode(c["text"], add_special_tokens=False).ids)
        a = r["messages"][1]["content"]
        gt = "".join(x.get("text", "") for x in a) if isinstance(a, list) else a
        txt += len(self.tok.encode(gt, add_special_tokens=False).ids)
        return vis + txt, vis

    def calibrate(self):
        best, tot, n = 0, 0, 0
        for line in open(CALIB_JSONL, encoding="utf-8"):
            if line.strip():
                t, _ = self.row(json.loads(line))
                best, tot, n = max(best, t), tot + t, n + 1
        assert best == CALIB_EXPECT, f"token count does not reproduce the t05 preflight: {best} != {CALIB_EXPECT}"
        return best, tot / n


# ── write / sanitize / verify ────────────────────────────────────────────────────────────────────
def write_jsonl(p, rows):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def run_sanitizer(raw_files, out_dir):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    cmd = [sys.executable, "-B", str(HERE / "sanitize_labels.py")]
    st = subprocess.run(cmd + ["--selftest"], capture_output=True, text=True, encoding="utf-8", env=env)
    assert st.returncode == 0 and "selftest ok" in st.stdout, f"sanitize selftest failed:\n{st.stdout}{st.stderr}"
    r = subprocess.run(cmd + [str(f) for f in raw_files] + ["--out", str(out_dir)],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    out = r.stdout + r.stderr
    assert r.returncode == 0, f"sanitize gate failed (exit {r.returncode}):\n{out}"
    after = re.findall(r"หลังล้าง \(แถวที่เจอ\): (.*)", out)
    passed = out.count("ด่าน: ผ่าน")
    assert len(after) == len(raw_files) and all(a.strip() == "0" for a in after), f"sanitize: leaks remain\n{out}"
    assert passed == len(raw_files) and "ด่าน: ไม่ผ่าน" not in out, f"sanitize gate not passed\n{out}"
    assert "ข้อมูลประกอบ" not in out, f"sanitize reports keys outside the allowlist / plan patterns\n{out}"
    return "selftest ok; " + f"{passed}/{len(raw_files)} files ด่าน: ผ่าน, หลังล้าง 0", out


def verify(data_dir, folds_of, groups, holdouts, counter, full_tails):
    from PIL import Image
    res, problems = {}, []
    rows_by_id, split, n_text = {}, {}, 0          # one parsed copy per id; files compared by line digest
    for p in sorted(Path(data_dir).glob("*.jsonl")):
        ids, hs = [], set()
        for line in open(p, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            ids.append(r["id"])
            hs.add(r["house"])
            dg = sha256_text(line)
            if r["id"] in rows_by_id:
                if rows_by_id[r["id"]][0] != dg:
                    problems.append(f"{r['id']}: differs between files")
            else:
                rows_by_id[r["id"]] = (dg, r)
        if len(ids) != len(set(ids)):
            problems.append(f"{p.name}: duplicate ids")
        split[p.stem] = (set(ids), hs)
    allrows = [rows_by_id[i][1] for i in sorted(rows_by_id)]
    res["unique_rows"] = len(allrows)
    # train/val per fold
    every = set(rows_by_id)
    for k in TRAIN_FOLDS:
        (ti, th), (vi, vh) = split[f"train_fold{k}"], split[f"val_fold{k}"]
        if th & vh:
            problems.append(f"fold{k}: houses in both train and val: {sorted(th & vh)[:3]}")
        if ti & vi:
            problems.append(f"fold{k}: ids in both train and val")
        if ti | vi != every:
            problems.append(f"fold{k}: train+val is not the full row set")
        if any(folds_of[h] != k for h in vh) or any(folds_of[h] == k for h in th):
            problems.append(f"fold{k}: house fold assignment mismatch")
    # groups
    for g in groups:
        if len({folds_of[h] for h in g["members"]}) != 1:
            problems.append(f"group split across folds: {g['members']}")
    # holdout / bench
    banned = [h["house"] for h in holdouts]
    for r in allrows:
        imgs = [c["image"] for c in r["messages"][0]["content"] if c["type"] == "image"]
        blob = r["id"] + " " + " ".join(imgs)
        if r["house"] in banned or any(b in blob for b in banned):
            problems.append(f"held-out house in {r['id']}")
    # per row
    hits, keys_bad, pat_bad, grid_bad, tail_ok, tail_no_grid_row = Counter(), Counter(), Counter(), 0, 0, 0
    info_hits = Counter()
    z_rows = z_entries = p0_list = p0_list_bad = 0
    # plan rows carry the FULL ground-truth master as their tail (gridline rows are page-by-page deltas now, so their
    # labels are no longer a master) - the builder hands over the tails of every full master it built
    tails_of_house = full_tails
    inc_rows = defaultdict(list)                       # (house, master stem) -> [(step, user text after the prompt, label)]
    images = set()
    for r in allrows:
        texts = [("user", c["text"]) for c in r["messages"][0]["content"] if c["type"] == "text"]
        assert [m["role"] for m in r["messages"]] == ["user", "assistant"], r["id"]
        assert r["messages"][0]["content"][-1]["type"] == "text" and len(texts) == 1, f"{r['id']}: not one text part last"
        a = r["messages"][1]["content"]
        assert isinstance(a, list) and len(a) == 1 and a[0]["type"] == "text", r["id"]
        texts.append(("assistant", a[0]["text"]))
        n_text += len(texts)
        try:
            lab = json.loads(a[0]["text"])
        except ValueError:
            problems.append(f"{r['id']}: assistant text is not JSON")
            continue
        sub = r["subtask"]
        allow_sub = "pass0" if sub == "pass0" else sub
        extra = [k for k in lab if k not in KEYS[allow_sub]]
        if extra:
            keys_bad.update(f"{sub}.{k}" for k in extra)
        if sub in SUBTASK_PATTERN and sub != "pass0" and lab.get("pattern") != SUBTASK_PATTERN[sub]:
            pat_bad[f"{sub}:{lab.get('pattern')}"] += 1
        if sub == "gridline":
            n_img = sum(1 for c in r["messages"][0]["content"] if c["type"] == "image")
            gt_text = texts[0][1]
            if n_img != 1:
                problems.append(f"{r['id']}: a gridline row must carry exactly one page image (has {n_img})")
            if not gt_text.startswith(PROMPTS["gridline"] + G.MARK):
                problems.append(f"{r['id']}: gridline text is not the prompt + the GRID SO FAR tail")
            else:
                _, stemstep, _kind = r["id"].split("::")
                stem, step = stemstep.rsplit("__s", 1)
                inc_rows[(r["house"], stem)].append((int(step), gt_text[len(PROMPTS["gridline"]):], lab))
            for ax in ("x_lines", "y_lines"):
                for ln in lab["grid"][ax]:
                    if set(ln) - {"id", "pos_m", "type"} or not is_num(ln.get("pos_m")):
                        grid_bad += 1
            if lab["warnings"] != [] or list(lab["grid"]) not in (["x_lines", "y_lines"], ["x_lines", "y_lines", "z_levels"]):
                grid_bad += 1
            if "z_levels" in lab["grid"]:                    # slim levels: exactly id, level_m, type in that order
                zl = lab["grid"]["z_levels"]
                if not (isinstance(zl, list) and zl):
                    grid_bad += 1
                for e in zl if isinstance(zl, list) else []:
                    if not (isinstance(e, dict) and list(e) == ["id", "level_m", "type"] and is_num(e["level_m"])
                            and e["type"] in Z_TYPES and (e["id"] is None or (isinstance(e["id"], str) and e["id"].strip()))
                            and (e["type"] != "named" or e["id"] is not None)
                            and not (isinstance(e["id"], str) and (Z_ID_NUMBER.fullmatch(e["id"].strip())
                                                                   or Z_ID_SLUG.fullmatch(e["id"].strip())))):
                        grid_bad += 1
                z_rows += 1
                z_entries += len(zl) if isinstance(zl, list) else 0
        if sub == "pass0":
            t = texts[0][1]
            if not t.startswith(PASS0_PROMPT):
                problems.append(f"{r['id']}: pass0 text does not start with the pass0 prompt")
            i = t.find(SHEET_MARK)
            if i >= 0:
                p0_list += 1
                try:
                    lst = json.loads(t[i + len(SHEET_MARK):])
                    ok = (i == len(PASS0_PROMPT) and isinstance(lst, list) and lst
                          and t[i:] == SHEET_MARK + json.dumps(lst, ensure_ascii=False)
                          and all(isinstance(x, dict) and list(x) == ["title", "sheet_range"] and isinstance(x["title"], str)
                                  and x["title"].strip() and (x["sheet_range"] is None or isinstance(x["sheet_range"], str))
                                  for x in lst))
                except ValueError:
                    ok = False
                if not ok:
                    problems.append(f"{r['id']}: SHEET LIST tail malformed")
                    p0_list_bad += 1
        if sub.startswith("plan_"):
            t = texts[0][1]
            i = t.find(TAIL_MARK)
            if i >= 0:
                end = json.JSONDecoder().raw_decode(t, i + len(TAIL_MARK))[1]
                if r["house"] in tails_of_house:
                    if t[i:end] in tails_of_house[r["house"]]:
                        tail_ok += 1
                    else:
                        problems.append(f"{r['id']}: GRID MASTER tail is not one of this house's gridline labels")
                else:
                    tail_no_grid_row += 1
        for who, t in texts:
            for name, rx in (("house_name", V_HOUSE), ("iso_date", V_DATE), ("history", V_HIST), ("forbidden_key", V_KEY)):
                if rx.search(t):
                    hits[f"{who}/{name}"] += 1
            for b in BENCH_TOKENS:
                if b in t:
                    hits[f"{who}/bench:{b}"] += 1
            for b in BENCH_INFO:
                if b in t:
                    info_hits[f"{who}/{b}"] += 1
        for c in r["messages"][0]["content"]:
            if c["type"] == "image":
                images.add(c["image"])
    # replay every master's kept rows in step order with the plain merge function: each row's GRID SO FAR tail must
    # equal the state the earlier rows produce (dropped empty steps change nothing, so skipping them is safe)
    replay_rows = replay_bad = 0
    for (house, stem), rs in sorted(inc_rows.items()):
        state = G.new_state()
        for step, tail_text, lab in sorted(rs, key=lambda x: x[0]):
            replay_rows += 1
            if tail_text != G.tail(state):
                replay_bad += 1
                problems.append(f"{house}::{stem}__s{step:02d}: GRID SO FAR tail != the state the earlier rows build")
                break
            state, _ = G.merge_delta(state, lab["grid"])
    res["gridline_replay"] = {"masters": len(inc_rows), "rows": replay_rows, "bad": replay_bad}
    bad_img = []
    for rel in sorted(images):
        p = TR / rel
        try:
            with Image.open(p) as im:
                im.verify()
        except Exception as e:  # noqa: BLE001
            bad_img.append(f"{rel}: {type(e).__name__}")
    res.update({"text_parts_scanned": n_text, "regex_hits": dict(hits), "keys_outside_allowlist": dict(keys_bad),
                "plan_pattern_not_normalized": dict(pat_bad), "gridline_shape_violations": grid_bad,
                "plan_tails_matching_house_gridline": tail_ok, "plan_tails_without_gridline_row": tail_no_grid_row,
                "gridline_rows_with_z_levels": z_rows, "z_level_entries": z_entries,
                "pass0_rows_with_sheet_list": p0_list, "pass0_sheet_list_malformed": p0_list_bad,
                "images_checked": len(images), "images_bad": bad_img, "bench_design_names_info": dict(info_hits)})
    problems += [f"regex hit {k} x{v}" for k, v in hits.items()]
    problems += [f"key outside allowlist {k} x{v}" for k, v in keys_bad.items()]
    problems += [f"plan pattern {k} x{v}" for k, v in pat_bad.items()]
    problems += (["gridline label shape violations"] if grid_bad else []) + bad_img
    # length gate
    lens = []
    for r in allrows:
        t, v = counter.row(r)
        lens.append((t, v, r["id"], r["subtask"]))
    lens.sort(reverse=True)
    over = [x for x in lens if x[0] >= LIMIT]
    problems += [f"row over 0.95*MAX_LENGTH: {x[2]} {x[0]}" for x in over]
    res["length"] = {"limit": LIMIT, "max": lens[0][0], "top10": [{"id": x[2], "subtask": x[3], "tokens": x[0],
                                                                   "visual": x[1]} for x in lens[:10]],
                     "over_limit": len(over), "margin_pct_vs_max_length": round((MAX_LENGTH - lens[0][0]) / MAX_LENGTH * 100, 1)}
    by_sub = defaultdict(list)
    for t, _, _, s in lens:
        by_sub[s].append(t)
    res["length"]["per_subtask"] = {s: {"n": len(v), "max": max(v), "p99": sorted(v)[int(0.99 * (len(v) - 1))],
                                        "median": int(statistics.median(v)), "mean": round(statistics.mean(v))}
                                    for s, v in sorted(by_sub.items())}
    res["length"]["mean_all"] = round(statistics.mean(x[0] for x in lens))
    return res, problems


def heldout_page_overlap(all_rows, holdout):
    """INFO only: rows whose image is a near-duplicate page (dHash16 <= 20) of the held-out house,
    from the survey's fp_pairs.json when it is still on disk"""
    p = Path(os.environ.get("T07_FP_PAIRS", r"D:\Temp\claude\3049db1b73f5b7d5\4f8e489b-7af8-462e-bb6e-2dab7cb6cab0"
                                            r"\scratchpad\t07survey\fp_pairs.json"))
    if not p.exists():
        return {"status": f"skipped ({p} not found)"}
    near, ident = set(), set()
    for x in json.load(open(p, encoding="utf-8")):
        if holdout not in (x["a"], x["b"]) or x["a"].startswith("BENCH") or x["b"].startswith("BENCH"):
            continue
        other, idx = (x["b"], 1) if x["a"] == holdout else (x["a"], 0)
        for pr in x["pairs"]:
            near.add((other, pr[idx]))
            if pr[2] == 0:
                ident.add((other, pr[idx]))
    n_near = n_id = 0
    for r in all_rows:
        pages = [(r["house"], page_key(c["image"])[0]) for c in r["messages"][0]["content"] if c["type"] == "image"]
        n_near += any(pg in near for pg in pages)
        n_id += any(pg in ident for pg in pages)
    return {"status": f"from {p.name} (survey, read-only)", "rows_with_near_dup_page": n_near,
            "rows_with_identical_dhash_page": n_id, "houses": sorted({h for h, _ in near})}


# ── report ───────────────────────────────────────────────────────────────────────────────────────
def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def kind_of(r):
    return "pass0" if r["subtask"] == "pass0" else "pass2.4" if r["id"].endswith("_arm24") else "pass1"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--exclude-source", action="append", default=[], choices=["siamplan"])
    ap.add_argument("--root", default=str(HERE), help="output root (data_raw/, data/, manifest.json, build_report.md)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    root = Path(a.root).resolve()
    excl_src = tuple(sorted(set(a.exclude_source)))

    check_prompts_clean()
    parity = check_worker_parity()
    print(f"prompts: clean · worker parity: {parity}")
    counter = TokenCounter()
    calib_max, calib_mean = counter.calibrate()
    print(f"token calibration: t05 train_fold0 longest row = {calib_max:,} (expected {CALIB_EXPECT:,}) ✓")

    houses, all_houses, exclusions, holdouts = enumerate_houses(excl_src)
    print(f"houses: {len(houses)} ({sum(h['tree'] == 'corrected' for h in houses.values())} corrected + "
          f"{sum(h['tree'] == 'raw' for h in houses.values())} raw-only) · exclusions {len(exclusions)} · held out {len(holdouts)}")

    b = Builder()
    pass1, pass0_all, pass24 = [], [], []
    for bare in houses:
        p1, p0, p24 = b.house_rows(houses[bare])
        pass1 += p1
        pass0_all += p0
        pass24 += p24
    p0_class = lambda r: "+".join(v["subtask"] for v in json.loads(r["messages"][1]["content"][0]["text"])["views"])  # noqa: E731
    pass0, p0_quota = strat_cap(pass0_all, p0_class, PASS0_CAP)
    rows = sorted(pass1 + pass0 + pass24, key=lambda r: r["id"])
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate row ids"

    rows_of_house = Counter(r["house"] for r in rows)
    groups, missing_members = build_groups(list(houses), FAMILIES)
    folds_of, fold_totals = assign_folds(groups, rows_of_house)

    # write data_raw/ and data/
    raw_dir, data_dir = root / "data_raw", root / "data"
    for dd in (raw_dir, data_dir):
        dd.mkdir(parents=True, exist_ok=True)
        for old in dd.glob("*.jsonl"):
            old.unlink()
    raw_files = []
    for k in TRAIN_FOLDS:
        for split, keep in (("train", lambda r, k=k: folds_of[r["house"]] != k),
                            ("val", lambda r, k=k: folds_of[r["house"]] == k)):
            p = raw_dir / f"{split}_fold{k}.jsonl"
            write_jsonl(p, [r for r in rows if keep(r)])
            raw_files.append(p)
    san_summary, san_out = run_sanitizer(raw_files, data_dir)
    changed = sum(1 for p in raw_files for x, y in zip(open(p, encoding="utf-8"), open(data_dir / p.name, encoding="utf-8"))
                  if x != y)
    print(f"sanitize: {san_summary} · rows changed by the second net: {changed}")

    res, problems = verify(data_dir, folds_of, groups, holdouts, counter, b.full_tails)
    overlap = heldout_page_overlap(rows, holdouts[0]["house"]) if holdouts else {}

    # siamplan-excluded variant, computed on the same rows (fold assignment redone)
    if not excl_src:
        keep_h = {h for h, i in houses.items() if i["source"] != "siamplan"}
        vrows = [r for r in rows if r["house"] in keep_h]
        vgroups, _ = build_groups(sorted(keep_h), FAMILIES)
        vfolds, vtot = assign_folds(vgroups, Counter(r["house"] for r in vrows))
        variant = {"houses": len(keep_h), "corrected": sum(houses[h]["tree"] == "corrected" for h in keep_h),
                   "raw_only": sum(houses[h]["tree"] == "raw" for h in keep_h), "rows": len(vrows),
                   "rows_per_kind": dict(sorted(Counter(kind_of(r) for r in vrows).items())),
                   "rows_per_subtask": dict(sorted(Counter(r["subtask"] for r in vrows).items())),
                   "fold_rows": vtot, "groups": len(vgroups),
                   "train_val_per_fold": {k: [sum(1 for r in vrows if vfolds[r["house"]] != k),
                                              sum(1 for r in vrows if vfolds[r["house"]] == k)] for k in TRAIN_FOLDS}}
    else:
        variant = {"note": "this build IS the excluded variant"}

    # manifest
    per_house = defaultdict(lambda: {"pass1": Counter(), "pass0": 0, "pass2.4": 0})
    for r in rows:
        k = kind_of(r)
        if k == "pass1":
            per_house[r["house"]]["pass1"][r["subtask"]] += 1
        else:
            per_house[r["house"]][k] += 1
    outputs = {f"{d.name}/{p.name}": sha256_file(p) for d in (raw_dir, data_dir) for p in sorted(d.glob("*.jsonl"))}
    manifest = {
        "round": "t07 Palfrey", "builder": "build_t07.py", "exclude_source": list(excl_src),
        "parameters": {"pass0_cap": PASS0_CAP, "n_folds": N_FOLDS, "train_folds": list(TRAIN_FOLDS),
                       "max_length": MAX_LENGTH, "length_limit_0.95": LIMIT, "max_image_tokens": CAP_TOK,
                       "tokenizer": str(TOKENIZER.relative_to(TR)).replace("\\", "/"), "epochs_for_estimate": EPOCHS},
        "houses": {h: {"fold": folds_of[h], "tree": houses[h]["tree"], "folder": houses[h]["folder"],
                       "scope": houses[h]["scope"], "source": houses[h]["source"],
                       "rows": {"pass1": dict(sorted(per_house[h]["pass1"].items())), "pass0": per_house[h]["pass0"],
                                "pass2.4": per_house[h]["pass2.4"]}} for h in houses},
        "exclusions": exclusions, "holdouts": holdouts,
        "groups": [{"fold": g["fold"], "members": g["members"], "evidence": g["evidence"]}
                   for g in groups if len(g["members"]) > 1],
        "group_members_not_in_house_set": [{"evidence": e, "house": m} for e, m in missing_members],
        "fold_rows": fold_totals, "siamplan_excluded_variant": variant, "outputs_sha256": outputs,
        "change_2026_11_11_z_levels_and_sheet_list": change_stats(rows, b, res),
        "gridline_page_by_page": dict(sorted(b.inc.items())),
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n",
                                        encoding="utf-8", newline="\n")

    write_report(root, houses, rows, pass0_all, p0_quota, b, groups, folds_of, fold_totals, res, problems,
                 san_summary, changed, parity, calib_max, calib_mean, overlap, variant, exclusions, holdouts, outputs,
                 excl_src)
    print(f"rows: {len(rows)} = pass1 {len(pass1)} + pass0 {len(pass0)} (of {len(pass0_all)}) + pass2.4 {len(pass24)}")
    for k in TRAIN_FOLDS:
        print(f"  fold{k}: train {sum(1 for r in rows if folds_of[r['house']] != k)} · "
              f"val {sum(1 for r in rows if folds_of[r['house']] == k)}")
    print(f"length: max {res['length']['max']:,} tokens (limit {LIMIT:,.0f}) · over {res['length']['over_limit']}")
    for x in res["length"]["top10"]:
        print(f"   {x['tokens']:>6,}  {x['subtask']:<12} {x['id']}")
    for name, sha in outputs.items():
        print(f"  sha256 {sha}  {name}")
    if problems:
        print("VERIFY FAILED:")
        for p in problems[:50]:
            print("  -", p)
        return 1
    print("verify: all checks passed")
    return 0


def write_report(root, houses, rows, pass0_all, p0_quota, b, groups, folds_of, fold_totals, res, problems,
                 san_summary, changed, parity, calib_max, calib_mean, overlap, variant, exclusions, holdouts, outputs,
                 excl_src):
    L = []
    kinds = Counter(kind_of(r) for r in rows)
    L.append("# t07 Palfrey - build report (build_t07.py)\n")
    L.append(f"Variant: {'siamplan EXCLUDED' if excl_src else 'default (siamplan included, D2)'} · "
             f"{len(houses)} houses · {len(rows)} unique rows "
             f"(pass1 {kinds['pass1']}, pass0 {kinds['pass0']}, pass2.4 {kinds['pass2.4']}). "
             f"Gate: {'FAILED - see Problems' if problems else 'all checks passed'}. Everything below is MEASURED "
             f"by this run unless it says INFERRED.\n")
    L.append("## Houses\n")
    hc = Counter((h["tree"], h["scope"], h["source"]) for h in houses.values())
    L.append(table(["tree", "scope", "source", "houses"], [[*k, v] for k, v in sorted(hc.items())]))
    ex = Counter(e["reason"].split(":")[0] if e["reason"].startswith("superseded") else e["reason"] for e in exclusions)
    L.append("\nExclusions (folder level):\n")
    L.append(table(["reason", "folders"], sorted(ex.items())))
    L.append("\nHeld out (never in any fold): " + ", ".join(f"{h['folder']} - {h['reason']}" for h in holdouts) + "\n")
    L.append("## Rows per subtask and kind\n")
    sk = Counter((r["subtask"], kind_of(r)) for r in rows)
    L.append(table(["subtask", "kind", "rows", "houses"],
                   [[s, k, v, len({r["house"] for r in rows if r["subtask"] == s and kind_of(r) == k})]
                    for (s, k), v in sorted(sk.items())]))
    L.append(f"\npass0: {len(pass0_all)} hazard-guarded rows from full-coverage houses, capped to "
             f"{kinds['pass0']} (water-filling, classes at or under the quota kept whole):\n")
    L.append(table(["view class", "available", "kept"], [[k, n, q] for k, (n, q) in p0_quota.items()]))
    L.append("\n## Folds (5 group-folds, folds 0-3 trained; fold 4 houses are in every train split)\n")
    fr = []
    for k in range(N_FOLDS):
        hs = sorted(h for h in houses if folds_of[h] == k)
        tr = sum(1 for r in rows if folds_of[r["house"]] != k)
        va = sum(1 for r in rows if folds_of[r["house"]] == k)
        lo, hi = (tr * s * EPOCHS / 3600 + SETUP_MIN / 60 for s in SEC_PER_ROW)
        fr.append([k, len(hs), fold_totals[k], tr if k in TRAIN_FOLDS else "-", va if k in TRAIN_FOLDS else "-",
                   f"{lo:.1f}-{hi:.1f} h" if k in TRAIN_FOLDS else "-"])
    L.append(table(["fold", "houses", "rows in fold", "train rows", "val rows", "est. wall time (INFERRED)"], fr))
    L.append(f"\nWall time = train rows x {SEC_PER_ROW[0]}-{SEC_PER_ROW[1]} s per row-epoch (t05 fold0/fold3 measured) "
             f"x EPOCHS={EPOCHS} + {SETUP_MIN} min setup. INFERRED. Mean row length: t07 "
             f"{res['length']['mean_all']:,} tokens vs t05 train_fold0 {calib_mean:,.0f}, so per-row time may scale "
             f"by about {res['length']['mean_all'] / calib_mean:.2f}x (INFERRED).\n")
    sub_fold = []
    for s in sorted({r["subtask"] for r in rows}):
        sub_fold.append([s] + [sum(1 for r in rows if r["subtask"] == s and folds_of[r["house"]] == k) for k in range(N_FOLDS)])
    L.append("Rows per subtask in each fold (= the val split for folds 0-3):\n")
    L.append(table(["subtask"] + [f"fold{k}" for k in range(N_FOLDS)], sub_fold))
    L.append("\nHouses per fold:\n")
    for k in range(N_FOLDS):
        L.append(f"- fold{k}: " + ", ".join(sorted(h for h in houses if folds_of[h] == k)))
    L.append("\nGroups with more than one house (union-find over D8 evidence):\n")
    L.append(table(["fold", "members", "evidence"], [[g["fold"], " ".join(g["members"]), "; ".join(g["evidence"])]
                                                      for g in groups if len(g["members"]) > 1]))
    L.append("\n## Length gate (t05 trainer preflight arithmetic)\n")
    L.append(f"Calibration: t05 train_fold0 longest row = {calib_max:,} tokens, the logged preflight value. "
             f"Limit 0.95 x {MAX_LENGTH:,} = {LIMIT:,.0f}. Longest t07 row {res['length']['max']:,} "
             f"({res['length']['margin_pct_vs_max_length']}% below MAX_LENGTH), rows over the limit: "
             f"{res['length']['over_limit']}.\n")
    L.append(table(["subtask", "rows", "max", "p99", "median", "mean"],
                   [[s, v["n"], v["max"], v["p99"], v["median"], v["mean"]] for s, v in res["length"]["per_subtask"].items()]))
    L.append("\nTop 10 rows:\n")
    L.append(table(["tokens", "visual", "subtask", "id"], [[x["tokens"], x["visual"], x["subtask"], x["id"]]
                                                           for x in res["length"]["top10"]]))
    L.append("\n## What the build removed\n")
    L.append("Top-level keys dropped by the KEYS.json allowlist (label count):\n")
    L.append(table(["subtask.key", "labels"], b.dropped_keys.most_common(40)))
    L.append(f"\nnotes labels that carried a top-level `elements` list (not in the notes prompt, so dropped): "
             f"{b.notes_elements_dropped[0]} labels, {b.notes_elements_dropped[1]} non-structural elements.\n")
    L.append("Nested D5 scrub (sanitize_labels.scrub): " + ", ".join(f"{k} {v}" for k, v in sorted(b.scrub.items())) + "\n")
    L.append("Nested key occurrences removed by the scrub (top 30, subtask.key):\n")
    L.append(table(["subtask.key", "removed"], b.lost_nested.most_common(30)))
    L.append("\nLabel rows with a sanitize gate hit BEFORE the scrub (kind, marker):\n")
    L.append(table(["kind", "marker", "rows"], [[k, m, v] for (k, m), v in sorted(b.leak_before.items())]))
    L.append("\nRouting / skip counters:\n")
    L.append(table(["counter", "n"], sorted(b.st.items())))
    L.append("\nGRID MASTER selection for plan rows: " + ", ".join(f"{k} {v}" for k, v in sorted(b.master_route.items())) + "\n")
    L.extend(incremental_report(rows, b, res))
    L.extend(change_report(rows, b, res))
    L.append("## Gates\n")
    L.append(f"- worker parity: {parity}")
    L.append(f"- sanitize_labels.py (second net): {san_summary}; rows it changed: {changed}")
    L.append(f"- final verify on data/: {res['unique_rows']} unique rows, {res['text_parts_scanned']} text parts, "
             f"{res['images_checked']} images opened (bad {len(res['images_bad'])}); regex hits {res['regex_hits'] or 0}; "
             f"keys outside allowlist {res['keys_outside_allowlist'] or 0}; plan pattern not normalized "
             f"{res['plan_pattern_not_normalized'] or 0}; gridline shape violations {res['gridline_shape_violations']}; "
             f"plan tails equal to a FULL ground-truth master of the same house {res['plan_tails_matching_house_gridline']} "
             f"(plan rows of houses with no master at all: {res['plan_tails_without_gridline_row']}); "
             f"gridline page-by-page replay: {res['gridline_replay']['rows']} rows of {res['gridline_replay']['masters']} masters, "
             f"bad {res['gridline_replay']['bad']}")
    L.append(f"- held-out page overlap (INFO, survey fingerprints): {json.dumps(overlap, ensure_ascii=False)}")
    L.append(f"- bench design names in text (INFO): {res['bench_design_names_info'] or 0}")
    L.append(f"- siamplan-excluded variant: {json.dumps(variant, ensure_ascii=False)}")
    L.append("\n## Problems\n")
    L.append("\n".join(f"- {p}" for p in problems) if problems else "none")
    L.append("\n## Output sha256\n")
    L.append(table(["file", "sha256"], sorted(outputs.items())))
    (root / "build_report.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


def incremental_report(rows, b, res):
    """numbers of the 2026-11-11 evening change: the gridline pass is page-by-page (grid_incremental.py)"""
    i = b.inc
    gl = [r for r in rows if r["subtask"] == "gridline"]
    L = ["## 2026-11-11 evening: gridline is page-by-page (grid_incremental.py)\n"]
    L.append("One page image + the GRID SO FAR tail per row; the label is only what THIS page adds. Order: beam plan, footing "
             "plan, roof frame, other plans, then sections/elevations. The old rows (up to 4 images, whole master in one "
             "answer) are gone from the data; the old build is kept in `data_20261111_0146/` / `build_report_20261111_0146.md`.\n")
    L.append(table(["measured", "value"], [
        ["masters seen", i["masters_seen"]],
        ["masters cut into page rows", i["masters_used"]],
        ["skipped: no dimension_chains in the master (no per-page evidence)", i["skip_no_dimension_chains"]],
        ["skipped: ids / origin do not follow the spec's mechanical rule", i["skip_gt_ids_or_origin_not_the_spec_rule"]],
        ["skipped: a line without a named/dummy type", i["skip_line_without_named_or_dummy_type"]],
        ["skipped: no page with an image", i["skip_no_page_with_an_image"]],
        ["skipped: replay mismatch (must be 0)", i["skip_replay_state_mismatch"] + i["skip_replay_final_differs_from_gt"]],
        ["pages (steps) over all used masters", i["steps_total"]],
        ["steps that add something", i["steps_nonempty"]],
        [f"rows written: adding rows / empty rows kept (max {EMPTY_STEPS_PER_MASTER} per master)",
         f"{i['rows_nonempty']} / {i['rows_empty_kept']}"],
        ["empty steps not written", i["steps_empty_dropped"]],
        ["ground-truth x/y lines in those masters", i["gt_lines"]],
        ["of those, no page connects them to the known grid (not in any label)", i["gt_lines_no_page_adds_them"]],
        ["times the CODE renumbered a line the model had already given (origin shift or primes)",
         i["known_lines_renumbered_by_code"]],
        ["named lines given with a negative pos_m (revealed left of the origin)", i["named_lines_left_of_the_origin"]],
        ["chain rows ignored (page has no usable image / axis)", i["chain_rows_dropped_page_not_usable"]],
    ]))
    r = res["gridline_replay"]
    L.append(f"\nReplay (verify): {r['rows']} rows of {r['masters']} masters re-merged in step order with `merge_delta`; "
             f"every row's GRID SO FAR tail equals the state the earlier rows build - bad: {r['bad']}.\n")
    ln = res["length"]["per_subtask"].get("gridline")
    if ln:
        L.append(f"gridline rows now {ln['n']} (old build: 171), tokens per row: max {ln['max']:,} · p99 {ln['p99']:,} · "
                 f"median {ln['median']:,} · mean {ln['mean']:,} (old build max 34,503).\n")
    by_m = sorted(b.inc_masters, key=lambda m: -m["rows"])[:5]
    L.append("Masters with the most rows: " + "; ".join(f"{m['house']} {m['master']} ({m['rows']} rows / {m['steps']} pages)" for m in by_m) + "\n")
    L.append("Decisions made here (att1235): the proportion-measuring step of the old prompt is dropped (a line that no "
             "printed dimension reaches is not added); confidence_flags on page rows are `[]` (the master's audit notes are "
             "not a property of one page); plan rows keep the full ground-truth master as their GRID MASTER tail; folds are "
             "recomputed from the new per-house row counts.\n")
    return L


def change_stats(rows, b, res):
    """numbers of the 2026-11-11 afternoon change (gridline z_levels + pass0 SHEET LIST), from the FINAL rows"""
    gl = [r for r in rows if r["subtask"] == "gridline"]
    p0 = [r for r in rows if r["subtask"] == "pass0"]
    p0_text = lambda r: r["messages"][0]["content"][-1]["text"]  # noqa: E731
    zk = {k: v for k, v in b.st.items() if k.startswith("z_entry_")}
    return {
        "gridline_rows": len(gl),
        "gridline_rows_with_z": res["gridline_rows_with_z_levels"],
        "gridline_rows_without_z": len(gl) - res["gridline_rows_with_z_levels"],
        "z_row_outcomes": dict(sorted(b.z_rows.items())),
        "z_entries_in_gt_of_built_rows": b.z_gt_entries, "z_entries_kept": b.z_kept_entries,
        "z_entries_dropped_by_reason": dict(sorted(zk.items())),
        "z_types_mapped": dict(sorted((k.split(":", 1)[1], v) for k, v in b.st.items() if k.startswith("z_type_mapped:"))),
        "z_ids_set_to_null": {"number_only": b.st["z_id_number_only_to_null"], "slug": b.st["z_id_slug_to_null"]},
        "z_type_named_without_id_to_dummy": b.st["z_type_named_without_id_to_dummy"],
        "z_duplicates_dropped": b.st["z_entry_duplicate"],
        "pass0_rows": len(p0),
        "pass0_houses_with_sheet_list": len(b.sheet_list_houses),
        "pass0_rows_in_houses_with_list": sum(1 for r in p0 if r["house"] in b.sheet_list_houses),
        "pass0_rows_with_sheet_list": sum(1 for r in p0 if SHEET_MARK in p0_text(r)),
        "pass0_houses_without_usable_index": b.st["pass0_sheet_list_house_without_usable_index"],
        "pass0_houses_dropped_flagged_text": b.st["pass0_sheet_list_house_dropped_flagged_text"],
        "pass0_candidate_rows_before_cap": {"with_list": b.st["pass0_candidate_rows_sheet_list_yes"],
                                            "without_list": b.st["pass0_candidate_rows_sheet_list_no"]},
        "sheet_list_source": {h: {"index_file": f, "entries": n} for h, (f, n) in sorted(b.sheet_list_houses.items())},
    }


def change_report(rows, b, res):
    c = change_stats(rows, b, res)
    L = ["## 2026-11-11 afternoon: gridline z_levels (slim) + pass0 SHEET LIST\n"]
    L.append("Before this change (first build, 2026-11-11 01:46; its data is kept in `data_20261111_0146/` and "
             "`data_raw_20261111_0146/`, its report in `build_report_20261111_0146.md`): gridline rows with z 0, pass0 rows "
             "with the sheet list 0, longest gridline row 34,503 tokens, longest pass0 row 8,961, 3,573 rows, same "
             "houses, same folds (row counts per house do not change, so the fold assignment does not).\n")
    L.append(f"gridline rows {c['gridline_rows']}: **{c['gridline_rows_with_z']} carry `z_levels`**, "
             f"{c['gridline_rows_without_z']} do not. GT z entries on those rows' masters: "
             f"{c['z_entries_in_gt_of_built_rows']}, kept in labels: {c['z_entries_kept']} "
             f"(an entry stays only if its own source page is among the row's images, level_m is a number, "
             f"id passes the leak gate).\n")
    L.append("Rows by z outcome:\n")
    L.append(table(["outcome", "gridline rows"], c["z_row_outcomes"].items()))
    L.append("\nEntries dropped (entry level, before the row decision):\n")
    L.append(table(["reason", "entries"], c["z_entries_dropped_by_reason"].items() or [["none", 0]]))
    L.append(f"\ntype mapped to the prompt's datum/named/dummy (old GT vocabulary): {c['z_types_mapped'] or 'none'} "
             f"(named when the level has a printed id, dummy otherwise). id set to null because it was the bare "
             f"number or a snake_case slug, not a printed label (the prompt says number-only -> null): "
             f"{c['z_ids_set_to_null']}; `named` with no id (after that, or in GT) changed to `dummy`, because the "
             f"prompt says named = a labelled level: {c['z_type_named_without_id_to_dummy']}. "
             f"Exact duplicates dropped after that: {c['z_duplicates_dropped']}.\n")
    L.append(f"pass0: {c['pass0_rows']} rows (cap 400 unchanged), **{c['pass0_rows_with_sheet_list']} carry the SHEET LIST tail**; "
             f"{c['pass0_houses_with_sheet_list']} houses have a usable index page, "
             f"{c['pass0_rows_in_houses_with_list']} of the kept rows belong to them (about half get the tail: "
             f"even parity of sha256(row id)). Before the cap: {c['pass0_candidate_rows_before_cap']}. "
             f"Full-coverage houses without a usable index page: {c['pass0_houses_without_usable_index']}; "
             f"houses whose list was dropped by the leak gate: {c['pass0_houses_dropped_flagged_text']}.\n")
    L.append("Index page used per house (lowest-numbered index file whose sections carry `sheet_range`):\n")
    L.append(table(["house", "index file", "entries"], [[h, v["index_file"], v["entries"]] for h, v in c["sheet_list_source"].items()]))
    L.append("")
    return L


def selftest():
    import test_grid_incremental                              # the page-by-page grid rules (grid_incremental.py)
    test_grid_incremental.run()
    st = Counter()
    zs = Counter()
    gt = [{"id": "ระดับอ้างอิง", "level_m": 0.0, "type": "datum", "source_image": "image/h/h_หน้า08.png", "note": "x"},
          {"id": "ระดับหลังคาน", "level_m": 3.75, "type": "beam_top", "source_image": "image/h/h_หน้า08.png"},
          {"id": "ระดับหลังคาน", "level_m": 3.75, "type": "named", "source_image": "image/h/h_หน้า05.png"},   # duplicate after mapping
          {"id": None, "level_m": -1.5, "type": "floor", "source_image": "image/h/h_หน้า05.png"},
          {"id": "ระดับใต้ฐานราก", "level_m": -1.5, "type": "named", "source_image": "image/h/h_หน้า22.png"},  # page not shown
          {"id": "ระดับ", "level_m": None, "type": "named", "source_image": "image/h/h_หน้า05.png"},          # not a number
          {"id": "ระดับ", "level_m": 1.0, "type": "named"},                                                 # no source page
          {"id": "op_fix", "level_m": 1.0, "type": "named", "source_image": "image/h/h_หน้า05.png"}]         # leak gate
    assert slim_levels(gt, {(8, ""), (5, "")}, zs) == [
        {"id": "ระดับอ้างอิง", "level_m": 0.0, "type": "datum"}, {"id": "ระดับหลังคาน", "level_m": 3.75, "type": "named"},
        {"id": None, "level_m": -1.5, "type": "dummy"}], slim_levels(gt, {(8, ""), (5, "")}, Counter())
    assert zs == Counter({"z_type_mapped:beam_top": 1, "z_entry_duplicate": 1, "z_type_mapped:floor": 1,
                          "z_entry_source_page_not_in_images": 1, "z_entry_level_not_number": 1,
                          "z_entry_no_source_page": 1, "z_entry_id_flagged": 1}), zs
    assert slim_levels(gt, {(99, "")}, Counter()) == [] and slim_levels(None, {(8, "")}, Counter()) == []
    zi = Counter()
    ids_in = ["+0.40", "@2.05", "±0.00", "-1.20", "roof_ridge", "reference", "ระดับพื้นชั้น 1", "FFL", "ระดับ +0.60"]
    got = slim_levels([{"id": i, "level_m": k, "type": "dummy", "source_image": "image/h/h_หน้า05.png"}
                       for k, i in enumerate(ids_in)], {(5, "")}, zi)
    assert [e["id"] for e in got] == [None] * 6 + ["ระดับพื้นชั้น 1", "FFL", "ระดับ +0.60"], got
    assert zi["z_id_number_only_to_null"] == 4 and zi["z_id_slug_to_null"] == 2, zi
    zn = Counter()
    assert slim_levels([{"id": "+0.40", "level_m": 0.4, "type": "named", "source_image": "image/h/h_หน้า05.png"},
                        {"id": None, "level_m": 0.0, "type": "datum", "source_image": "image/h/h_หน้า05.png"}],
                       {(5, "")}, zn) == [{"id": None, "level_m": 0.4, "type": "dummy"},
                                          {"id": None, "level_m": 0.0, "type": "datum"}], zn
    assert zn["z_type_named_without_id_to_dummy"] == 1 and zn["z_id_number_only_to_null"] == 1, zn
    d = lambda name, doc: (name, doc, page_key(name))  # noqa: E731
    sec = [{"title": "แบบวิศวกรรมโครงสร้าง", "sheet_range": "S-01 ถึง S-08", "doc_page_start": 16}, {"title": " ", "sheet_range": "A"},
           {"title": "หลักเกณฑ์", "doc_page_start": 56}]
    docs = [d("h_หน้า03_index.json", {"pattern": "index", "sections": [{"sheet_no": "A-01", "title": "x"}]}),
            d("h_หน้า05_index.json", {"pattern": "index", "sections": sec}),
            d("h_หน้า02_index.json", {"pattern": "index", "sections": sec[:1]}),
            d("h_หน้า01.json", {"pattern": "title", "sections": sec})]
    sst = Counter()
    name, ents = sheet_list_of(docs, sst)
    assert name == "h_หน้า02_index.json" and ents == [{"title": "แบบวิศวกรรมโครงสร้าง", "sheet_range": "S-01 ถึง S-08"}], (name, ents)
    name, ents = sheet_list_of(docs[:2] + docs[3:], sst)
    assert name == "h_หน้า05_index.json" and ents == [{"title": "แบบวิศวกรรมโครงสร้าง", "sheet_range": "S-01 ถึง S-08"},
                                                      {"title": "หลักเกณฑ์", "sheet_range": None}] and \
        sst["sheet_list_entry_dropped_no_title"] == 1, (name, ents, sst)
    assert sheet_list_of(docs[:1] + docs[3:], Counter()) == (None, None)
    assert sheet_tail(ents) == SHEET_MARK + '[{"title": "แบบวิศวกรรมโครงสร้าง", "sheet_range": "S-01 ถึง S-08"}, ' \
                                            '{"title": "หลักเกณฑ์", "sheet_range": null}]'
    assert slim_lines([{"pos_m": 1, "id": "1", "type": "named", "note": "x"}, {"id": "2", "pos_m": None},
                       {"id": "3", "pos_m": True}, {"id": "4", "pos_m": 2.5}], st) == \
        [{"id": "1", "pos_m": 1, "type": "named"}, {"id": "4", "pos_m": 2.5}]
    assert st["grid_line_pos_m_not_number"] == 2
    assert page_key("x_หน้า00b_gridline_สุขา.json") == (0, "b") and page_key("หน้า7") == (7, "")
    lab = {"grid": {"x_lines": [{"id": "1", "pos_m": 0, "type": "named"}], "y_lines": []}}
    assert grid_tail(lab) == TAIL_MARK + '{"grid": {"x_lines": [{"id": "1", "pos_m": 0, "type": "named"}], "y_lines": []}}'
    ms = [{"pk": (0, ""), "building": "อาคารหลัก", "tag": None}, {"pk": (0, "b"), "building": "สุขา", "tag": "สุขา"}]
    assert master_for(ms, {"building": "สุขา"}, "a.json")[1] == "by_building_field"
    assert master_for(ms, {}, "a_หน้า14_view2_footing_plan_สุขา.json") == (ms[1], "by_file_tag")
    assert master_for(ms, {"building": "อื่น"}, "a.json") == (ms[0], "default_main_master")
    rows = [{"id": f"r{i}", "c": "big"} for i in range(50)] + [{"id": f"s{i}", "c": "rare"} for i in range(3)]
    keep, q = strat_cap(rows, lambda r: r["c"], 20)
    assert len(keep) == 20 and q == {"big": (50, 17), "rare": (3, 3)}, q
    assert strat_cap(rows, lambda r: r["c"], 20)[0] == keep
    g, miss = build_groups(["a", "b", "c", "d"], [("x", ["b", "a"]), ("y", ["c", "a", "zz"])])
    assert [x["members"] for x in g] == [["a", "b", "c"], ["d"]] and miss == [("y", "zz")]
    f, tot = assign_folds(g, {"a": 5, "b": 1, "c": 1, "d": 2}, k=2)
    assert f == {"a": 0, "b": 0, "c": 0, "d": 1} and tot == [7, 2]
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
