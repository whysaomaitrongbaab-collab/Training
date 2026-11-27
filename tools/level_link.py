#!/usr/bin/env python3
"""level_link.py - the level pass: which plan views sit at which height (report only, no model, writes nothing)

    python tools/level_link.py <house-folder> [--md out.md] [--level-master ../logic_test_out/<house>/level_marks.json]
    python tools/level_link.py --demo                                  # self-check (temp files only)

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


def read_floors(path):
    """a level master file -> floors: the spec file (`{level: {floors}}`) or level_marks.py output (`{level_master: ...}`).
    Floors whose level_m is unknown (level_marks leaves a tie empty) are dropped here - they cannot give a height."""
    doc = load(path) or {}
    doc = doc.get('level_master', doc)
    floors = [f for f in (doc.get('level') or {}).get('floors') or [] if isinstance(f.get('level_m'), (int, float))]
    return sorted(floors, key=lambda f: f['level_m'])


def link(house_dir, level_master=None):
    lm_files = [level_master] if level_master else glob.glob(os.path.join(house_dir, '*หน้า00_level.json'))
    floors = read_floors(lm_files[0]) if lm_files else []
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


def demo():
    import tempfile

    def put(path, obj):
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(obj, fh, ensure_ascii=False)

    with tempfile.TemporaryDirectory() as d:
        spec = os.path.join(d, 'x_หน้า00_level.json')          # spec file, floors out of order on purpose
        put(spec, {'level': {'floors': [{'floor_level': 'F2', 'level_m': 3.5}, {'floor_level': 'F1', 'level_m': 0.0},
                                        {'floor_level': 'RF', 'level_m': 6.8}]}})
        lm = os.path.join(d, 'level_marks.json')                 # level_marks.py output, one tie left empty
        put(lm, {'level_master': {'level': {'floors': [{'floor_level': 'F1', 'level_m': 2.0},
                                                       {'floor_level': 'F1M', 'level_m': None},
                                                       {'floor_level': 'F2', 'level_m': 9.0}]}}})
        put(os.path.join(d, 'x_หน้า05.json'), {'pattern': 'beam_plan', 'floor_level': 'F2', 'view_title': 'แปลนคานชั้นที่ 2'})
        assert [f['floor_level'] for f in read_floors(spec)] == ['F1', 'F2', 'RF']
        assert heights(read_floors(spec)) == {'F1': 3.5, 'F2': 3.3, 'RF': None}   # a roof code has no storey height
        assert [f['floor_level'] for f in read_floors(lm)] == ['F1', 'F2']        # unknown level: cannot give a height
        assert read_floors(os.path.join(d, 'missing.json')) == []
        floors, views, flags = link(d)                           # the house's own level master
        assert [(v['floor_level'], v['level_m'], v['title_check']) for v in views] == [('F2', 3.5, 'ok')]
        assert ('floor_without_plan_view', 'F1') in flags and not any(k == 'no_level_master' for k, _ in flags)
        floors, views, flags = link(d, lm)                       # --level-master wins over the house's file
        assert views[0]['level_m'] == 9.0 and len(floors) == 2
        assert link(os.path.join(d, 'empty'))[2][0][0] == 'no_level_master'
    print('level_link demo OK')
    return 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('house', nargs='?')
    ap.add_argument('--md')
    ap.add_argument('--level-master', help='use this level master instead of the house\'s own *หน้า00_level.json '
                                           '(e.g. ../logic_test_out/<house>/level_marks.json from level_marks.py)')
    ap.add_argument('--demo', action='store_true')
    a = ap.parse_args(argv[1:])
    if a.demo:
        return demo()
    if not a.house:
        ap.error('house folder needed (or --demo)')
    floors, views, flags = link(a.house, a.level_master)
    text = render(a.house, floors, views, flags)
    if a.md:
        open(a.md, 'w', encoding='utf-8').write(text)
    sys.stdout.reconfigure(encoding='utf-8')
    print(text)
    return 1 if any(k == 'no_level_master' for k, _ in flags) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
