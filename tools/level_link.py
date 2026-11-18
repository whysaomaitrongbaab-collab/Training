#!/usr/bin/env python3
"""level_link.py - the level pass: which plan views sit at which height (report only, no model, writes nothing)

    python tools/level_link.py <house-folder> [--md out.md]

Spec section 4b. Reads the house's level master (`*หน้า00_level.json`) and every plan view file
(beam_plan / footing_plan / roof_frame_plan / etc_plan / column_plan), joins each view's `floor_level` to the
level master and prints, per floor: its level, the storey height above it, and the views that sit on it.

Storey height = the next floor's level_m minus this floor's, for a B*/F* floor that has a next entry. A roof
code (RF*) has none: the step RF -> RF2 is a frame standing on a roof slab, not a storey.

Flags (these are the reason the pass exists, a view that cannot be given a height must be visible):
  view_floor_not_in_level_master   a plan view names a floor code the level master has no level for
  floor_without_plan_view          the level master has a floor that no plan view uses
  title_floor_mismatch             `ชั้นที่ N` in view_title says one floor, `floor_level` says another
  no_level_master                  the house has no level master file at all (nothing to join)
"""
import argparse
import glob
import json
import os
import re
import sys

PLAN = {'beam_plan', 'footing_plan', 'roof_frame_plan', 'etc_plan', 'column_plan', 'plan'}
TITLE_N = re.compile(r'ชั้น(?:ที่)?\s*(\d+)')


def load(path):
    try:
        return json.load(open(path, encoding='utf-8'))
    except (OSError, ValueError):
        return None


def heights(floors):
    """floor_level -> storey height (m) or None."""
    out = {}
    for i, f in enumerate(floors):
        code = f['floor_level']
        nxt = floors[i + 1] if i + 1 < len(floors) else None
        out[code] = round(nxt['level_m'] - f['level_m'], 3) if nxt and not code.startswith('RF') else None
    return out


def link(house_dir):
    lm_files = glob.glob(os.path.join(house_dir, '*หน้า00_level.json'))
    floors = []
    if lm_files:
        doc = load(lm_files[0]) or {}
        floors = (doc.get('level') or {}).get('floors') or []
    flags, views = [], []
    if not floors:
        flags.append(('no_level_master', os.path.basename(os.path.normpath(house_dir))))
    by_code = {f['floor_level']: f for f in floors}
    for path in sorted(glob.glob(os.path.join(house_dir, '*.json'))):
        d = load(path)
        if not isinstance(d, dict) or d.get('pattern') not in PLAN:
            continue
        code, title = d.get('floor_level'), str(d.get('view_title') or '')
        m = TITLE_N.search(title)
        check = 'none'
        if m and code:
            check = 'ok' if code == f'F{m.group(1)}' else 'MISMATCH'
        name = os.path.basename(path)
        if check == 'MISMATCH':
            flags.append(('title_floor_mismatch', f'{name}: title says F{m.group(1)}, floor_level {code}'))
        if floors and code not in by_code:
            flags.append(('view_floor_not_in_level_master', f'{name}: floor_level {code!r}'))
        views.append({'file': name, 'pattern': d['pattern'], 'floor_level': code, 'view_title': title,
                      'title_check': check, 'level_m': by_code.get(code, {}).get('level_m')})
    used = {v['floor_level'] for v in views}
    for f in floors:
        if f['floor_level'] not in used:
            flags.append(('floor_without_plan_view', f['floor_level']))
    return floors, views, flags


def render(house_dir, floors, views, flags):
    h = heights(floors)
    L = [f'# level link: {os.path.basename(os.path.normpath(house_dir))}', '']
    if floors:
        L += ['| floor | level_m | storey height | plan views on it |', '|---|---|---|---|']
        for f in floors:
            c = f['floor_level']
            on = [f"{v['pattern']} ({re.search(r'หน้า(\d+)', v['file']).group(1) if re.search(r'หน้า(\d+)', v['file']) else '?'})"
                  for v in views if v['floor_level'] == c]
            L.append(f"| {c} | {f['level_m']:+.2f} | {('%.2f' % h[c]) if h[c] is not None else '-'} | {', '.join(on) or '-'} |")
    L += ['', f'plan views read: {len(views)}  |  floors in level master: {len(floors)}  |  flags: {len(flags)}']
    for k, v in flags:
        L.append(f'- FLAG {k}: {v}')
    return '\n'.join(L) + '\n'


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('house')
    ap.add_argument('--md')
    a = ap.parse_args(argv[1:])
    floors, views, flags = link(a.house)
    text = render(a.house, floors, views, flags)
    if a.md:
        open(a.md, 'w', encoding='utf-8').write(text)
    sys.stdout.reconfigure(encoding='utf-8')
    print(text)
    return 1 if any(k == 'no_level_master' for k, _ in flags) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
