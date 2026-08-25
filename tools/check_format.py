#!/usr/bin/env python3
"""Format checker for primary_rawjson_schema.md section 0 (FORMAT LOCK).

Usage:
    python tools/check_format.py                       # every house under rawjson_ยังไม่ได้แก้ไขโดนคน/
    python tools/check_format.py <folder> [<folder>..] # specific house folder(s)

Exits 1 if any check fails, so it can gate an op1 run. Written 2026-08-02 after
houses 01-11 drifted apart and had to be repaired in bulk (สิ่งที่ต้องแก้.md items 59-63).
"""
import json, sys, os, re, glob, collections

# section 1 of primary_rawjson_schema.md. 'bbs_schedule' and 'soil_boring_log' added 2026-08-04
# (14 -> 16); keep this set and that table in step, the checker is what actually enforces it.
PATTERNS = {'plan', 'section', 'schedule', 'notes', 'index', 'material_list', 'site_plan',
            'side_profile', 'gridline', 'title', 'symbol', 'roof_plan', 'misc',
            'bbs_schedule', 'soil_boring_log', 'unknown'}
WRAPPER = ['png', 'doc_page', 'discipline', 'sheet_code', 'sheet_name', 'pattern',
           'confidence_score', 'confidence_flags', 'warnings']
# section 2, pinned 2026-08-21. 'architecture' is the wrong spelling of 'architectural'
# (an audit found 182 files one way, 157 the other). Anything genuinely outside goes to misc.
DISCIPLINES = {'structural', 'architectural', 'sanitary', 'electrical', 'mechanical',
               'boq', 'material_list', 'general', 'front_matter', 'regulatory', 'misc'}
# section 4a, added 2026-08-21: a notes file uses ONLY sections[] + notes{}.
# Every other container/topic key is a defect (55 files carried six different names).
NOTES_ONEOFF = {'notes_sections', 'spec_notes', 'notes_text', 'raw_text', 'notes_general',
                'reference_standard', 'concrete_strength', 'steel_grade',
                'precast_plank_spec', 'general_requirements', 'footing_bearing_notes'}
# section 4, added 2026-08-21: the grid master records every printed dimension.
GRID_ARRAYS = ('z_levels', 'dimension_chains', 'unassigned_dimensions')
# section 1 warning: a structural roof-FRAMING sheet is pattern 'plan', never 'roof_plan'
# -- Constistant's buildElements() reads only 'plan', so roof beams filed under
# 'roof_plan' have never reached a BOQ.
STRUCT_TYPES = {'beam', 'column', 'rafter', 'steel_member', 'tie_beam', 'slab'}
# arrays named after a KIND of drawing element (section 0.1). 'sections'/'columns'/'details' are
# deliberately absent: they legitimately mean document sections / table headers / detail callouts.
ELEMENT_KIND_ARRAYS = {'beams', 'columns_structural', 'slabs', 'footing_types',
                       'column_sections', 'structural_elements',
                       'slab_markers', 'reference_markers', 'door_window_schedule'}
# element_types that are annotation clusters; their auto ids are fine, but they still need ids
NUMERIC_KEYS = ('count', 'dia_mm', 'spacing_mm', 'level_m', 'span_m', 'width_mm', 'height_mm', 'thickness_mm')
OBJECT_KEYS = ('main_bar', 'stirrup', 'rebar', 'steel_section')
POINT_TYPES = {'footing', 'column', 'pile', 'pile_cap', 'pedestal'}
PACKED_SIZE_KEYS = ('size_m', 'section_mm', 'footing_size_m', 'plan_size_m', 'cap_plan_dims_m')

POINT_REF = re.compile(r"^([A-Zก-ฮ]{1,3}'*)(\d+'*)$")
DASHED_POINT = re.compile(r"^[A-Zก-ฮ]{1,3}'*-\d+'*$")
GRID_WORD = re.compile(r'\bgrid(line)?\s*[0-9A-Zก-ฮ]|\bdummy\s*[0-9A-Zก-ฮ]', re.I)
PACKED = re.compile(r'^[\d.]+\s*[xX×]\s*[\d.]+$')
REF_KEYS = ('grid_ref', 'grid_ref_start', 'grid_ref_end', 'grid_refs')


def walk(node, fn):
    if isinstance(node, dict):
        for k, v in node.items():
            fn(k, v)
            walk(v, fn)
    elif isinstance(node, list):
        for v in node:
            walk(v, fn)


def load_grid(house_dir):
    rows, cols = set(), set()
    for g in glob.glob(os.path.join(house_dir, '*หน้า00*gridline*.json')):
        try:
            grid = json.load(open(g, encoding='utf-8')).get('grid', {})
        except Exception:
            continue
        rows |= {e['id'] for e in grid.get('y_lines', []) if 'id' in e}
        cols |= {str(e['id']) for e in grid.get('x_lines', []) if 'id' in e}
    return rows, cols


def check_house(house_dir):
    fails = collections.defaultdict(list)
    soft = []
    rows, cols = load_grid(house_dir)
    for path in sorted(glob.glob(os.path.join(house_dir, '*.json'))):
        name = os.path.basename(path)
        if name.startswith('_'):
            continue
        try:
            doc = json.load(open(path, encoding='utf-8'))
        except Exception as e:
            fails['parse'].append(f'{name}: {e}')
            continue

        for k in WRAPPER:
            if k not in doc:
                fails['wrapper fields'].append(f'{name}: missing {k}')
        if doc.get('pattern') not in PATTERNS:
            fails['pattern in 16'].append(f'{name}: {doc.get("pattern")!r}')
        if doc.get('discipline') not in DISCIPLINES:
            fails['discipline vocabulary'].append(f'{name}: {doc.get("discipline")!r}')
        # section 2: source_image on every file; the grid master uses source_pages instead
        img_key = 'source_pages' if doc.get('pattern') == 'gridline' else 'source_image'
        if img_key not in doc:
            fails['wrapper fields'].append(f'{name}: missing {img_key}')
        if 'phase_note' in doc:
            fails['phase_note left'].append(name)
        for k in doc:
            if k in ELEMENT_KIND_ARRAYS and isinstance(doc[k], list) and doc[k]:
                fails['element-kind array'].append(f'{name}: {k}')
        if doc.get('pattern') == 'gridline' and 'x_lines' in doc:
            fails['grid not nested'].append(name)
        if doc.get('pattern') == 'gridline' and 'หน้า00' in name:
            miss = [a for a in GRID_ARRAYS if a not in (doc.get('grid') or {})]
            if miss:
                # needs the source sheets re-read; an empty array would be a false
                # "read it, found nothing" claim (section 4), so this is never auto-filled
                fails['grid master missing 2026-08-21 arrays'].append(f'{name}: {",".join(miss)}')
        if doc.get('pattern') == 'notes':
            bad = sorted(k for k in doc if k in NOTES_ONEOFF)
            if bad:
                fails['notes one-off container key'].append(f'{name}: {bad}')
        if doc.get('pattern') == 'roof_plan' and doc.get('discipline') == 'structural':
            marked = [e for e in (doc.get('elements') or [])
                      if isinstance(e, dict) and e.get('element_type') in STRUCT_TYPES
                      and (e.get('grid_ref') or e.get('grid_refs') or e.get('grid_ref_start'))]
            if marked:
                fails['structural roof framing must be pattern plan'].append(
                    f'{name}: {len(marked)} marked structural elements')

        def scan(k, v):
            if k in ('main_bar', 'stirrup', 'tie', 'tie_bar') and isinstance(v, str):
                fails['rebar is a string'].append(f'{name}: {k}={v[:40]!r}')
            if k in ('tie', 'tie_bar'):
                fails['stirrup misnamed'].append(f'{name}: {k}')
            if k in OBJECT_KEYS and isinstance(v, list):
                fails['rebar/steel as array (use bar_layers/spans_m)'].append(f'{name}: {k}')
            if k in NUMERIC_KEYS and isinstance(v, (str, list)):
                fails['numeric field wrong type'].append(f'{name}: {k}={str(v)[:35]!r}')
            if k == 'grid_ref' and isinstance(v, list):
                fails['grid_ref is an array'].append(f'{name}')
            if k in PACKED_SIZE_KEYS and isinstance(v, str) and PACKED.match(v):
                fails['packed size string'].append(f'{name}: {k}={v!r}')
            if k in REF_KEYS:
                for x in (v if isinstance(v, list) else [v]):
                    if not isinstance(x, str):
                        continue
                    t = x.strip()
                    if DASHED_POINT.match(t):
                        fails['dashed point ref'].append(f'{name}: {t!r}')
                    if GRID_WORD.search(t):
                        fails["'grid' word in ref"].append(f'{name}: {t[:45]!r}')
                    m = POINT_REF.match(t)
                    if m and rows:
                        g1, g2 = m.group(1), m.group(2)
                        # Usually rows (y_lines) are letters and cols (x_lines) are digits, so
                        # g1-in-rows/g2-in-cols is the common case. But the spec only says
                        # "usually" (section 4) — a house can letter its x_lines and number its
                        # y_lines instead (confirmed for real on house 19, cross-checked against
                        # both the architecture and structural sheets). Accept either axis
                        # assignment rather than hardcoding which one carries letters.
                        matches_usual = g1 in rows and g2 in cols
                        matches_swapped = g1 in cols and g2 in rows
                        if not (matches_usual or matches_swapped):
                            fails['ref not in grid master'].append(f'{name}: {t!r}')
        walk(doc, scan)

        elements = doc.get('elements') or []
        by_id = collections.defaultdict(set)
        for e in elements:
            if isinstance(e, dict):
                # section 0.2: identity required on every top-level elements[] entry
                # (nested cross-ref sub-lists inside an element are exempt)
                if 'element_id' not in e:
                    fails['element missing element_id'].append(f'{name}')
                if 'element_type' not in e:
                    fails['element missing element_type'].append(f'{name}')
            if isinstance(e, dict) and e.get('element_id'):
                by_id[e['element_id']].add(e.get('element_id_printed_as') or e['element_id'])
        for eid, originals in by_id.items():
            if len(originals) > 1:
                fails['element_id collision'].append(f'{name}: {eid} <- {sorted(originals)}')

        if doc.get('pattern') == 'plan' and 'footing' in name:
            groups = collections.defaultdict(list)
            for e in elements:
                if isinstance(e, dict) and e.get('element_type') in POINT_TYPES:
                    groups[e.get('element_id')].append(e)
            for eid, g in groups.items():
                if len(g) < 2:
                    continue
                # allowed exception: entries differing by real per-position provenance.
                # confidence_flags counts too - each position can carry its own reason for doubt
                # (e.g. one footing inferred from a repeating module, another read off the sheet).
                distinct = {(x.get('confidence_score'), x.get('note'), x.get('offset_note'),
                             tuple(x.get('confidence_flags') or [])) for x in g}
                if len(distinct) == len(g):
                    soft.append(f'{os.path.basename(house_dir)[:2]} {name}: {eid} x{len(g)} '
                                f'(kept apart - differing confidence/note, allowed by section 0.10)')
                else:
                    fails['footing not merged'].append(f'{name}: {eid} x{len(g)}')
    return fails, soft


def main(argv):
    targets = argv[1:]
    if not targets:
        base = 'rawjson_ยังไม่ได้แก้ไขโดนคน'
        # house folders only: they start with the 2-digit house number (00file_... is the spec dir)
        targets = sorted(d for d in glob.glob(os.path.join(base, '*'))
                         if os.path.isdir(d) and os.path.basename(d)[:2].isdigit()
                         and not os.path.basename(d).startswith('00'))
    else:
        # A target that doesn't exist, or exists but has no .json files (e.g. the caller
        # forgot the 'rawjson_ยังไม่ได้แก้ไขโดนคน/' prefix), used to silently check 0 files
        # and still print "ALL CHECKS PASS" -- a false pass. Found 2026-08-09: houses
        # 12-18's logged verification commands all used a bare folder name and were
        # vacuous; house 15's real pattern:'detail_view' / tie_bar defects went uncaught
        # as a direct result. Fail loudly instead of silently checking nothing.
        bad_targets = [t for t in targets if not glob.glob(os.path.join(t, '*.json'))]
        if bad_targets:
            for t in bad_targets:
                reason = 'no such directory' if not os.path.isdir(t) else 'no .json files in it'
                print(f'ERROR: target {t!r} has {reason} -- did you forget the '
                      f"'rawjson_ยังไม่ได้แก้ไขโดนคน/' prefix?", file=sys.stderr)
            return 1
    total = collections.defaultdict(list)
    soft_all = []
    for t in targets:
        f, s = check_house(t)
        for k, v in f.items():
            total[k].extend(v)
        soft_all.extend(s)

    print(f'checked {len(targets)} house folder(s)\n')
    order = ['parse', 'wrapper fields', 'pattern in 16', 'discipline vocabulary',
             'phase_note left', 'element-kind array',
             'grid not nested', 'grid master missing 2026-08-21 arrays',
             'notes one-off container key', 'structural roof framing must be pattern plan',
             'rebar is a string', 'stirrup misnamed',
             'rebar/steel as array (use bar_layers/spans_m)', 'numeric field wrong type',
             'grid_ref is an array', 'element missing element_id', 'element missing element_type',
             'packed size string', 'dashed point ref', "'grid' word in ref", 'ref not in grid master',
             'element_id collision', 'footing not merged']
    for k in order:
        v = total.get(k, [])
        print(f'  {"PASS" if not v else "FAIL " + str(len(v)):>9s}  {k}')
        for line in v[:5]:
            print(f'              {line}')
        if len(v) > 5:
            print(f'              ... and {len(v) - 5} more')

    if soft_all:
        print(f'\n  NOTE  {len(soft_all)} allowed non-merges (section 0.10 exception):')
        for line in soft_all[:8]:
            print(f'          {line}')
        if len(soft_all) > 8:
            print(f'          ... and {len(soft_all) - 8} more')

    bad = sum(len(v) for v in total.values())
    print(f'\n  {"ALL CHECKS PASS" if bad == 0 else str(bad) + " PROBLEM(S) FOUND"}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
