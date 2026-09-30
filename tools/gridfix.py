#!/usr/bin/env python3
"""gridfix -- the mechanical half of op_fix (.claude/skills/op_fix/SKILL.md).

    python tools/gridfix.py <staging.json>                    # dry-run: print the plan, write nothing
    python tools/gridfix.py <staging.json> --apply            # write it, only if every check passes
    python tools/gridfix.py <staging.json> --apply --accept-mismatch   # keep a printed chain that doesn't close
    python tools/gridfix.py --selftest

Turns "@<pos_m>" chain ends into named dummy lines (spec section 4 "Dummy grid" + rule 4), re-sequences
primes when a new line lands inside an existing run, carries every rename into the grid refs of every
file in the house, and refuses to write unless each ref still resolves to the same position and no ref
that pointed at nothing gets a position. Writes every file of the house or none.
"""
import copy
import glob
import json
import os
import re
import sys

REF_KEYS = ('grid_ref', 'grid_ref_start', 'grid_ref_end', 'grid_refs',   # same as check_format.py
            'grid_columns', 'grid_rows')   # + the per-page "which lines show here" lists (survey 2026-09-29)
TOK = re.compile(r"([A-Zก-ฮ]{1,3}|\d+)((?:'|′|″|\")*)")
TOL = 0.0005        # "compare to the millimetre" (section 4 rule 4)
NEAR = 0.05         # "within 0.05 m ... keep both and say so in warnings[]"
SEG_TOL = 0.005     # a printed segment vs the two line positions it spans


def norm(i):  # == check_format._line_id
    return str(i).strip().replace('′', "'").replace('″', "''").replace('"', "''")


def split(i):
    n = norm(i)
    b = n.rstrip("'")
    return b, len(n) - len(b)


def is_dummy(l):
    return l.get('type') == 'dummy' or (l.get('type') is None and "'" in norm(l.get('id', '')))


def place(p):
    return f'@{p:g}'


def plan_axis(lines, new_pos, ax, merges=()):
    """lines: master's x_lines/y_lines (mutated in place). new_pos: positions needing a line. merges:
    [{'id', 'into_pos'}] -- a line removed, its refs moved to the line at into_pos.
    Every dummy on the axis ends up with its canonical name (spec section 4 Dummy grid): primed off the main
    grid to its left/above, before the origin it joins the first main grid, primes 1..n in reading order.
    That includes labels Makham gave or confirmed himself (his ruling 2026-09-29: order them, refs follow).
    Returns ({pos: id}, {old_norm_id: new_id}, warnings)."""
    warns, got = [], {}
    num = lambda l: isinstance(l.get('pos_m'), (int, float))
    ids0 = [norm(l['id']) for l in lines if 'id' in l]
    dup0 = sorted({i for i in ids0 if ids0.count(i) > 1})
    if dup0:        # re-sequencing would split them and send every ref to one of the two (review 2026-09-29)
        raise SystemExit(f'{ax}: the master already has id(s) {dup0} twice -- refs to them are ambiguous, resolve by hand first')
    mains = sorted((l for l in lines if not is_dummy(l) and num(l)), key=lambda l: l['pos_m'])
    if not mains:
        raise SystemExit(f'{ax}: no main grid line to name dummies from')
    posless = [l['id'] for l in lines if is_dummy(l) and not num(l)]
    for p in sorted(new_pos):
        hit = [l for l in lines if num(l) and abs(l['pos_m'] - p) <= TOL]
        if hit:
            got[p] = hit[0]          # the line itself: its id may still change below
            continue
        near = [l['id'] for l in lines if num(l) and abs(l['pos_m'] - p) <= NEAR]
        if near:
            warns.append(f'{ax} tick at {p:g} is within {NEAR} m of existing {near} but not the same point -- kept both (section 4 rule 4)')
        got[p] = {'id': f'@{p:g}', 'pos_m': p, 'type': 'dummy', '_new': True}
        lines.append(got[p])
    if posless and any(v.get('_new') for v in got.values()):
        warns.append(f'{ax}: new ticks {sorted(p for p, v in got.items() if v.get("_new"))} on an axis with pos-less dummies '
                     f'{posless} -- if a tick is one of them, merge_lines that dummy into its position')
    merged = {}         # after the placeholders, so into_pos may name a point this run creates (house 06 ข')
    for m in merges:
        src = [l for l in lines if norm(l.get('id', '')) == norm(m['id'])]
        tgt = [l for l in lines if l not in src and num(l) and abs(l['pos_m'] - m['into_pos']) <= TOL]
        if len(src) != 1 or not tgt:
            raise SystemExit(f'{ax} merge {m}: need exactly one line {m["id"]} and a line at {m["into_pos"]}')
        if not is_dummy(src[0]):    # a bare-number rename would reach "2nd floor", "+4.10" in prose refs
            raise SystemExit(f'{ax} merge {m["id"]}: a printed (named) grid line never moves -- merge_lines takes dummies only')
        if any(v is src[0] for v in got.values()):
            raise SystemExit(f'{ax} merge {m["id"]}: a chain of this run ends on the line being removed')
        lines.remove(src[0])
        merged[norm(m['id'])] = tgt[0]
    before = {id(l): norm(l['id']) for l in lines if not l.get('_new')}
    groups = {}
    for l in lines:
        if is_dummy(l) and num(l):
            under = [m for m in mains if m['pos_m'] < l['pos_m']]
            groups.setdefault(norm((under[-1] if under else mains[0])['id']), []).append(l)
    fixed = {norm(l['id']) for l in lines if 'id' in l and not (is_dummy(l) and num(l))}   # printed / pos-less
    want = {b: [b + "'" * k for k in range(1, len(ms) + 1)] for b, ms in groups.items()}
    # house 12: ง' is a PRINTED bubble, so a dummy off ง can't be called ง' -- that base keeps its names, and
    # a base whose rule names hit a kept name (ง' wants ง'''', base ง keeps ง'''') keeps its names too
    skip = {}
    while True:
        kept = fixed | {norm(l['id']) for b in skip for l in groups[b] if not l.get('_new')}
        more = {b: sorted(kept & set(want[b])) for b in groups if b not in skip and kept & set(want[b])}
        if not more:
            break
        skip.update(more)
    stranded = []
    for base, ms in groups.items():
        if base in skip:
            warns.append(f"{ax} base {base}: canonical names {skip[base]} are printed/kept grid ids "
                         f"-- this base keeps its names {[l['id'] for l in ms if not l.get('_new')]}")
            stranded += [(base, l) for l in sorted(ms, key=lambda l: l['pos_m']) if l.get('_new')]
            continue
        for name, l in zip(want[base], sorted(ms, key=lambda l: l['pos_m'])):
            if norm(l['id']) != name:                    # same line written 1" stays 1"
                l['id'] = name
    for base, l in stranded:      # a new tick has no name to keep: next free prime on its root letter, flagged
        root = split(base)[0]
        l['id'] = root + "'" * (1 + max(split(x['id'])[1] for x in lines if 'id' in x and split(x['id'])[0] == root))
        warns.append(f"{ax} new tick at {l['pos_m']:g} (base {base}): its rule name is a printed id, so it is "
                     f"named {l['id']}, the next free prime on {root} -- primes on {root} are out of reading order")
    rename = {}
    for l in lines:
        o = before.get(id(l))
        if o and o != norm(l['id']):
            rename[o] = l['id']
    rename.update({o: t['id'] for o, t in merged.items()})
    ids = [norm(l['id']) for l in lines if 'id' in l]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:                                               # a pos-less dummy can't be sequenced and may clash
        raise SystemExit(f'{ax}: canonical names clash with existing ids {dup}')
    # an untouched axis keeps its order; a pos-less line keeps its slot (its only structured position hint)
    if merges or rename or any(v.get('_new') for v in got.values()):
        key, last = {}, -1e9
        for l in lines:
            last = l['pos_m'] if num(l) else last
            key[id(l)] = (l['pos_m'], 0) if num(l) else (last, 1)
        lines.sort(key=lambda l: key[id(l)])
    return {p: v['id'] for p, v in got.items()}, rename, warns


def ref_tokens(s):
    return [norm(m.group(0)) for m in TOK.finditer(s) if not not_a_ref(s, m)]


# a quoted label inside a prose-ish ref ("box '3 +0.50 3'", "labels '1'/'2'"): its quote marks are not primes.
# An opening ' has no id character (or ') right before it; a closing ' has none right after it.
QSPAN = re.compile(r"(?<![0-9A-Za-zก-๙'])'[^']*'(?![0-9A-Za-zก-๙'])")


def quoted(s, i):
    """True when the token at s[i] sits inside a quoted label, or right after an unmatched opening quote."""
    if any(m.start() <= i < m.end() for m in QSPAN.finditer(s)):
        return True
    j = i - 1
    while j >= 0 and s[j] == "'":
        j -= 1
    return j < i - 1 and (j < 0 or not s[j].isalnum())


def not_a_ref(s, m):
    """Quoted label, or an English possessive ("see view1's warnings" -- house 13, 2026-09-29).
    Only 's ending a word: "1'x2" and "D-C'x1-2" are refs."""
    e = m.end()
    return quoted(s, m.start()) or ("'" in m.group(0) and s[e:e + 1] == 's' and not s[e + 1:e + 2].isalnum())


def rename_str(s, rn):
    return TOK.sub(lambda m: m.group(0) if not_a_ref(s, m) else rn.get(norm(m.group(0)), m.group(0)), s)


def unsure(s, names):
    """Tokens the heuristic may have mis-read that matter to this run: a skipped (quoted/possessive) match
    that is a name in `names`, or letters glued to Thai prose ("แนวข'-ค" reads as นวข') ending in one.
    The position check reads strings the same way, so it can't see these -- a human has to."""
    out = []
    for m in TOK.finditer(s):
        n = norm(m.group(0))
        b, k = split(n)
        if (not_a_ref(s, m) and n in names) or (len(b) > 1 and not b.isdigit() and b[-1] + "'" * k in names):
            out.append(m.group(0))
    return out


def walk_refs(node, fn):
    """Call fn(str) -> str on every grid-ref string under REF_KEYS; returns the new node."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k in REF_KEYS:
                out[k] = [fn(x) if isinstance(x, str) else x for x in v] if isinstance(v, list) else (fn(v) if isinstance(v, str) else v)
            else:
                out[k] = walk_refs(v, fn)
        return out
    if isinstance(node, list):
        return [walk_refs(v, fn) for v in node]
    return node


def all_strings(node, skip=()):
    if isinstance(node, dict):
        for k, v in node.items():
            if k not in skip:
                yield from all_strings(v, skip)
    elif isinstance(node, list):
        for v in node:
            yield from all_strings(v, skip)
    elif isinstance(node, str):
        yield node


# ---- format-preserving write: only values that changed are re-typed; everything else keeps its
# original text (number literals like 4.00, one-line objects), so the diff shows the fix and nothing else.
DEC = json.JSONDecoder()
WS = ' \t\r\n'


def _skip(t, i):
    while i < len(t) and t[i] in WS:
        i += 1
    return i


def _items(t, i):
    """t[i] is '{' or '['. Returns [(key|None, value_start, value_end)]."""
    close = '}' if t[i] == '{' else ']'
    out, i = [], _skip(t, i + 1)
    while t[i] != close:
        key = None
        if close == '}':
            key, i = DEC.raw_decode(t, i)
            i = _skip(t, _skip(t, i) + 1)          # past ':'
        _, e = DEC.raw_decode(t, i)
        out.append((key, i, e))
        i = _skip(t, e)
        if t[i] == ',':
            i = _skip(t, i + 1)
    return out


def _num(v, two):
    if isinstance(v, bool) or v is None or isinstance(v, int):
        return json.dumps(v)
    s = f'{v:.2f}'
    return s if two and float(s) == v else repr(v)


def _inline(v, two):
    if isinstance(v, list):
        return '[' + ', '.join(_inline(x, two) for x in v) + ']'
    if isinstance(v, dict):
        return '{ ' + ', '.join(f'{json.dumps(k, ensure_ascii=False)}: {_inline(x, two)}' for k, x in v.items()) + ' }'
    return json.dumps(v, ensure_ascii=False) if isinstance(v, str) else _num(v, two)


def _flat(x):
    return not isinstance(x, (dict, list)) or (isinstance(x, list) and all(not isinstance(y, (dict, list)) for y in x))


def _ser(v, pad, st):
    if not isinstance(v, (dict, list)) or not v:
        return _inline(v, st['two'])
    if st['compact'] and isinstance(v, dict) and all(_flat(x) for x in v.values()):
        return _inline(v, st['two'])
    if isinstance(v, dict):
        body = [f'{pad}  {json.dumps(k, ensure_ascii=False)}: {_ser(x, pad + "  ", st)}' for k, x in v.items()]
        return '{\n' + ',\n'.join(body) + '\n' + pad + '}'
    return '[\n' + ',\n'.join(pad + '  ' + _ser(x, pad + '  ', st) for x in v) + '\n' + pad + ']'


def _pad_at(t, i):
    j = t.rfind('\n', 0, i) + 1
    k = j
    while k < i and t[k] == ' ':
        k += 1
    return t[j:k]


def _patch(t, s, e, old, new, st):
    """Text for `new`, reusing t[s:e] (the text of `old`) wherever the value is unchanged."""
    if old == new and type(old) is type(new):
        return t[s:e]
    pad = _pad_at(t, s)
    if isinstance(old, dict) and isinstance(new, dict) and old and list(new)[:len(old)] == list(old):
        its = _items(t, s)
        out, last = [], s
        for (k, vs, ve) in its:
            out += [t[last:vs], _patch(t, vs, ve, old[k], new[k], st)]
            last = ve
        extra = [k for k in new if k not in old]
        if extra:
            one_line = '\n' not in t[s:e]
            ip = pad + '  ' if one_line else _pad_at(t, its[0][1])
            sep = ', ' if one_line else ',\n' + ip
            out.append(''.join(sep + f'{json.dumps(k, ensure_ascii=False)}: {_ser(new[k], ip, st)}' for k in extra))
        return ''.join(out) + t[last:e]                    # whitespace + '}'
    if isinstance(old, list) and isinstance(new, list) and old:
        its = _items(t, s)
        used, parts = set(), []
        for i, n in enumerate(new):
            hit = next((j for j, o in enumerate(old) if j not in used and o == n), None)
            o = old[i] if i < len(old) else None
            if hit is None and isinstance(n, dict) and isinstance(o, dict) and i not in used and list(o) == list(n) \
                    and 2 * sum(o[k] == n[k] for k in o) >= len(o):   # same slot, mostly the same -> patch it (a fixed chain)
                hit = i
            if hit is None and isinstance(n, dict):   # same keys, same numbers -> patch in place (a renamed line)
                hit = next((j for j, o in enumerate(old) if j not in used and isinstance(o, dict) and list(o) == list(n)
                            and all(o[k] == n[k] for k in o if not isinstance(o[k], (str, list, dict)))
                            and any(not isinstance(o[k], (str, list, dict)) for k in o)), None)
            if hit is None:
                parts.append(_ser(n, _pad_at(t, its[0][1]) if '\n' in t[s:e] else pad, st))
            else:
                used.add(hit)
                _, vs, ve = its[hit]
                parts.append(_patch(t, vs, ve, old[hit], n, st))
        if '\n' in t[s:e]:
            ip = _pad_at(t, its[0][1])
            return '[\n' + ',\n'.join(ip + x for x in parts) + '\n' + pad + ']'
        return '[' + ', '.join(parts) + ']'
    return _ser(new, pad, st)


def render(obj, path, like, log=print):
    """(text, newline) for obj; `like` is the file's original text, kept wherever the value is unchanged."""
    crlf = b'\r\n' in open(path, 'rb').read()
    bare = re.sub(r'"(?:[^"\\]|\\.)*"', '""', like)          # judge the number style outside string literals
    st = {'compact': re.search(r'\{ "', bare) is not None, 'two':re.search(r':\s*-?\d+\.\d0\b', bare) is not None}
    s = _skip(like, 0)
    _, e = DEC.raw_decode(like, s)
    txt = like[:s] + _patch(like, s, e, json.loads(like), obj, st) + like[e:]
    if json.loads(txt) != obj:                              # never trade correctness for a pretty diff
        txt = json.dumps(obj, ensure_ascii=False, indent=2) + ('\n' if like.endswith('\n') else '')
        log(f'   note: {os.path.basename(path)} re-serialized in full (format-preserving patch did not round-trip)')
    assert json.loads(txt) == obj
    return txt, '\r\n' if crlf else '\n'


def dump(obj, path, like, log=print):
    txt, nl = render(obj, path, like, log)
    with open(path, 'w', encoding='utf-8', newline=nl) as f:
        f.write(txt)


def write_all(outs):
    """[(path, text, newline)] -- every file or none: temp files first, then replace in order (master last),
    and a failed replace puts back what was already replaced. A half-applied house re-runs as APPLIED with
    its skipped pages one line off (review 2026-09-29)."""
    tmps, done = [], []
    try:
        for p, txt, nl in outs:
            with open(p + '.gridfix.tmp', 'w', encoding='utf-8', newline=nl) as f:
                f.write(txt)
            tmps.append(p + '.gridfix.tmp')
        for p, _, _ in outs:
            orig = open(p, 'rb').read()
            os.replace(p + '.gridfix.tmp', p)
            done.append((p, orig))
    except OSError as e:
        for p, orig in done:
            with open(p, 'wb') as f:
                f.write(orig)
        raise SystemExit(f'write failed ({e}) -- rolled back, the house is unchanged; rerun once the file is writable')
    finally:
        for t in tmps:
            if os.path.exists(t):
                os.remove(t)


def run(stg_path, apply=False, accept_mismatch=False, log=print):
    stg = json.load(open(stg_path, encoding='utf-8'))
    hdir, mname = stg['house_dir'], stg['master']
    house = mname.split('_หน้า00')[0]

    def img(p):
        return p if not isinstance(p, str) or p.startswith('image/') else f'image/{house}/{os.path.basename(p)}'
    def mm(v):   # 2.8 + 0.15 = 2.9499999999999997 -> 2.95: staging numbers are millimetres, like placeholders
        return round(v, 3) if isinstance(v, float) else v
    for arr in ('dimension_chains', 'unassigned_dimensions', 'z_levels_add', 'chain_fixes'):
        for e in stg.get(arr) or []:
            if 'source_image' in e:
                e['source_image'] = img(e['source_image'])
            for k in ('value_m', 'level_m'):
                if k in e:
                    e[k] = mm(e[k])
            for s in e.get('segments') or []:
                if 'value_m' in s:
                    s['value_m'] = mm(s['value_m'])
    stg['pages_swept'] = [img(p) for p in stg.get('pages_swept') or []]
    mpath = os.path.join(hdir, mname)
    mtext = open(mpath, encoding='utf-8').read()
    old = json.loads(mtext)
    doc = copy.deepcopy(old)
    grid = doc['grid']
    chains = copy.deepcopy(grid.get('dimension_chains') or [])
    touched = set()
    for fx in stg.get('chain_fixes') or []:
        chains[fx['index']]['segments'] = fx['segments']
        touched.add(fx['index'])
    first_new = len(chains)
    chains += copy.deepcopy(stg.get('dimension_chains') or [])
    touched |= set(range(first_new, len(chains)))

    # 1. placeholders -> lines
    want = {'x': set(), 'y': set()}
    for c in chains:
        if c.get('axis') in want:
            for s in c['segments']:
                for k in ('from', 'to'):
                    if isinstance(s.get(k), str) and s[k].startswith('@'):
                        want[c['axis']].add(round(float(s[k][1:]), 3))
    src = {}
    for c in chains:
        for s in c['segments'] if c.get('axis') in want else []:
            for k in ('from', 'to'):
                if isinstance(s.get(k), str) and s[k].startswith('@'):
                    src.setdefault((c['axis'], round(float(s[k][1:]), 3)), c.get('source_image'))
    # add_lines: a line no chain prints, e.g. a beam centreline derived from a printed face (house 04 B2)
    extra = {}
    for a in stg.get('add_lines') or []:
        p = round(float(a['pos_m']), 3)
        want[a['axis']].add(p)
        extra[(a['axis'], p)] = {k: v for k, v in a.items() if k not in ('axis', 'pos_m')}
    got, rename, warns = {}, {}, []
    for ax in 'xy':
        merges = [m for m in stg.get('merge_lines') or [] if m.get('axis') == ax]
        g, r, w = plan_axis(grid.setdefault(f'{ax}_lines', []), want[ax], ax, merges)
        got[ax], warns = g, warns + w
        for l in grid[f'{ax}_lines']:
            if l.pop('_new', False):
                l['note'] = 'dimension tick, section 4 rule 4 (added by op_fix 2026-09-29)'
                if src.get((ax, l['pos_m'])):
                    l['source_image'] = src[(ax, l['pos_m'])]
                l.update(extra.get((ax, l['pos_m']), {}))
        for o, n in r.items():
            if o in rename:
                raise SystemExit(f'ambiguous rename: {o} exists on both axes')
            rename[o] = n
    for c in chains:
        ax = c.get('axis')
        for s in c['segments']:
            for k in ('from', 'to'):
                e = s.get(k)
                if not isinstance(e, str):
                    continue
                if e.startswith('@') and ax in got:
                    s[k] = got[ax][round(float(e[1:]), 3)]
                elif ax in got and norm(e) in rename:
                    s[k] = rename[norm(e)]

    # 2. z
    # never create an absent array: absent = "not swept yet", empty = "swept, found nothing" (section 4)
    zl = grid.setdefault('z_levels', []) if 'z_levels' in grid or stg.get('z_levels_add') else []
    for z in stg.get('z_levels_add') or []:
        if not any(e.get('id') == z.get('id') and e.get('level_m') == z.get('level_m') for e in zl):
            zl.append(z)
    zids = {e.get('id') for e in zl}
    errors = []
    # a z label can name several levels on purpose (two ridges both printed ระดับหลังอกไก่) -- see step 3
    for ax in 'xy':
        ids = [norm(l['id']) for l in grid[f'{ax}_lines'] if 'id' in l]
        errors += [f'{ax}_lines id {i!r} used twice' for i in sorted({i for i in ids if ids.count(i) > 1})]
    # a staging applied twice duplicates its chains -- refuse when ALL of it is already there. One identical
    # chain is fine: a plan often prints the same row above and below (house 01 หน้า19 "1-3 7.00" twice)
    def leftover(new, old):
        pool, rest = list(old), []
        for e in new:
            (pool.remove if e in pool else rest.append)(e)
        return rest
    new_un = stg.get('unassigned_dimensions') or []
    if (chains[first_new:] or new_un) and not leftover(chains[first_new:], chains[:first_new]) \
            and not leftover(new_un, grid.get('unassigned_dimensions') or []):
        errors.append('every chain and unassigned entry of this staging is already in the master -- it looks applied already')
    for i, c in enumerate(chains):
        if c.get('axis') == 'z':
            for s in c['segments']:
                for k in ('from', 'to'):
                    if s.get(k) not in zids and s.get(k) != 'edge':
                        errors.append(f'chain {i} (z, {c.get("source_image")}): {k}={s.get(k)!r} is not a z_levels id')
        elif c.get('axis') not in ('x', 'y'):
            errors.append(f'chain {i}: axis {c.get("axis")!r}')

    # 3. every segment closes against the line positions
    pos = {ax: {} for ax in 'xyz'}             # id -> every position it names (z labels can repeat)
    for ax in 'xy':
        for l in grid[f'{ax}_lines']:
            if isinstance(l.get('pos_m'), (int, float)):
                pos[ax].setdefault(norm(l['id']), []).append(l['pos_m'])
    for e in zl:
        if isinstance(e.get('level_m'), (int, float)):
            pos['z'].setdefault(e.get('id'), []).append(e['level_m'])
    bad_new, bad_old = [], []
    for i, c in enumerate(chains):
        P = pos.get(c.get('axis'), {})
        key = (lambda e: e) if c.get('axis') == 'z' else norm
        for s in c['segments']:
            A, B, v = P.get(key(s.get('from'))), P.get(key(s.get('to'))), s.get('value_m')
            if not A or not B or not isinstance(v, (int, float)):
                continue
            if not any(abs(abs(b - a) - v) <= SEG_TOL for a in A for b in B):
                a, b = A[0], B[0]
                (bad_new if i in touched else bad_old).append(
                    f"chain {i} {c['axis']} {os.path.basename(c.get('source_image') or '')}: "
                    f"{s['from']}({'/'.join(f'{x:g}' for x in A)})->{s['to']}({'/'.join(f'{x:g}' for x in B)}) "
                    f"printed {v:g}, lines say {abs(b - a):.3f}")

    # 4. renames reach every file of the house, and every ref keeps its position
    others = [p for p in glob.glob(os.path.join(hdir, '*หน้า00*gridline*.json')) if os.path.abspath(p) != os.path.abspath(mpath)]
    if rename and others:
        errors.append(f'renames needed but the house has a second master {others} -- resolve by hand')
    old_pos = {norm(l['id']): (ax, l['pos_m']) for ax in 'xy' for l in old['grid'].get(f'{ax}_lines', []) if isinstance(l.get('pos_m'), (int, float))}
    new_pos = {norm(l['id']): (ax, l['pos_m']) for ax in 'xy' for l in grid[f'{ax}_lines'] if isinstance(l.get('pos_m'), (int, float))}
    moved_ok = {norm(m['id']): (m['axis'], float(m['into_pos'])) for m in stg.get('merge_lines') or []}
    names = set(rename) | {norm(v) for ax in 'xy' for v in got[ax].values()} - set(old_pos)   # renamed or new
    changed_files, exact_hits, eyeball = {}, [], []
    # every run, not only when something is renamed: a new line can bind a ref that pointed at no line
    for p in sorted(glob.glob(os.path.join(hdir, '*.json'))):
        t = open(p, encoding='utf-8').read()
        d = doc if os.path.abspath(p) == os.path.abspath(mpath) else json.loads(t)
        d2 = walk_refs(d, lambda s: rename_str(s, rename)) if rename else d
        before, after = [], []
        walk_refs(d, lambda s: before.append(s) or s)
        walk_refs(d2, lambda s: after.append(s) or s)
        for sb, sa in zip(before, after):
            tb, ta = ref_tokens(sb), ref_tokens(sa)
            if len(tb) != len(ta):
                errors.append(f'{os.path.basename(p)}: token count changed in {sb!r} -> {sa!r}')
            for x, y in zip(tb, ta):
                np_ = new_pos.get(y)
                if x in moved_ok and np_ and np_[0] == moved_ok[x][0] and abs(np_[1] - moved_ok[x][1]) <= TOL:
                    continue                          # a merged line: its refs move on purpose
                if x in old_pos and old_pos[x] != np_:
                    errors.append(f'{os.path.basename(p)}: ref {sb!r} -> {sa!r} moved {x}{old_pos[x]} -> {y}{np_}')
                elif x not in old_pos and np_:        # house 11 bathroom "1-1'": 1' did not exist
                    errors.append(f'{os.path.basename(p)}: ref {sb!r} names {y}, a line the master did not have -- '
                                  f'this run would bind it to {np_}. Fix the ref by hand first (see op_fix SKILL.md)')
            u = unsure(sb, names) if names else []
            if u and sb not in (stg.get('eyeball_ok') or []):     # eyeball_ok: exact strings checked as prose
                eyeball.append(f'{os.path.basename(p)}: {sb!r} ({", ".join(u)})')
        if rename:
            skip = REF_KEYS + (('x_lines', 'y_lines', 'dimension_chains') if d is doc else ())
            exact_hits += [f'{os.path.basename(p)}: {s!r}' for s in all_strings(d, skip) if norm(s) in rename]
        if d is doc:
            doc = d2
            grid = doc['grid']
        elif d2 != d:
            changed_files[p] = (d2, t)

    if chains or 'dimension_chains' in grid:
        grid['dimension_chains'] = chains
    swept = stg.get('pages_swept') or []
    if swept:
        grid['unassigned_dimensions'] = (grid.get('unassigned_dimensions') or []) + (stg.get('unassigned_dimensions') or [])
        sp = doc.setdefault('source_pages', [])
        sp += [p for p in swept if p not in sp]
    elif stg.get('unassigned_dimensions'):
        grid.setdefault('unassigned_dimensions', []).extend(stg['unassigned_dimensions'])
    notes = list(stg.get('warnings') or []) + [f'op_fix/gridfix: {w}' for w in warns]
    if rename:
        notes.append('op_fix/gridfix 2026-09-29: dummy primes re-sequenced into reading order (spec section 4 Dummy grid) -- '
                     + ', '.join(f'{o} -> {n}' for o, n in rename.items())
                     + '; grid refs in every file of the house follow; prose in older warnings still uses the old names')
    if bad_new and accept_mismatch:
        notes += [f'op_fix: printed chain does not close against the lines (kept as printed): {b}' for b in bad_new]
    doc.setdefault('warnings', []).extend(notes)

    log(f'== {mname}')
    log(f'   chains: {len(chains)} ({len(stg.get("dimension_chains") or [])} new, {len(stg.get("chain_fixes") or [])} fixed)'
        f' · unassigned +{len(stg.get("unassigned_dimensions") or [])} · z_levels +{len(stg.get("z_levels_add") or [])}')
    for ax in 'xy':
        if want[ax]:
            log(f'   {ax}: {len(want[ax])} placeholder point(s) -> ' + ', '.join(f'{place(p)}={got[ax][p]}' for p in sorted(want[ax])))
    for o, n in rename.items():
        log(f'   rename {o} -> {n}')
    for w in warns:
        log(f'   warn: {w}')
    for b in bad_new:
        log(f'   MISMATCH (new/fixed chain): {b}')
    for b in bad_old:
        log(f'   pre-existing mismatch (untouched chain): {b}')
    for h in exact_hits:
        log(f'   CHECK BY HAND -- a non-ref field equals a renamed id: {h}')
    for h in eyeball:
        log(f'   EYEBALL -- read as prose/quote/glued, so neither renamed nor position-checked: {h}')
    for p in changed_files:
        log(f'   refs renamed in {os.path.basename(p)}')
    for e in errors:
        log(f'   ERROR: {e}')
    if errors or (bad_new and not accept_mismatch):
        log('   -> not applied' if apply else '   -> would NOT apply')
        return False
    if exact_hits and apply:
        log('   -> not applied: resolve the CHECK BY HAND lines first')
        return False
    if eyeball and apply:
        log('   -> not applied: fix each EYEBALL ref by hand, or list its exact string under eyeball_ok if it is prose')
        return False
    if not apply:
        log('   -> dry-run ok')
        return True
    write_all([(p, *render(d2, p, t, log)) for p, (d2, t) in changed_files.items()]
              + [(mpath, *render(doc, mpath, mtext, log))])
    log(f'   -> APPLIED ({1 + len(changed_files)} file(s) written)')
    return True


def selftest():
    import tempfile
    d = tempfile.mkdtemp()
    h = os.path.join(d, '01บ้าน')
    os.makedirs(h)
    master = {'pattern': 'grid_master', 'warnings': [], 'grid': {
        'x_lines': [{'id': '1', 'pos_m': 0.0, 'type': 'named'}, {'id': "1'", 'pos_m': 1.2, 'type': 'dummy'},
                    {'id': '2', 'pos_m': 2.4, 'type': 'named'}, {'id': '3', 'pos_m': 6.0, 'type': 'named'}],
        'y_lines': [{'id': 'A', 'pos_m': 0.0, 'type': 'named'}, {'id': 'B', 'pos_m': 2.4, 'type': 'named'},
                    {'id': "A'", 'pos_m': 1.0, 'type': 'dummy', 'confidence_score': 1},   # Makham's label
                    {'id': "C'", 'pos_m': 2.0, 'type': 'dummy'}],   # C' sits above C -> messy base C
        'z_levels': [{'id': 'L0', 'level_m': 0.0, 'type': 'datum'}],
        'dimension_chains': [{'axis': 'x', 'source_image': 'p.png', 'segments': [
            {'from': 'edge', 'to': '1', 'value_m': 1.0}, {'from': '1', 'to': '2', 'value_m': 2.4}]}]}}
    page = {'elements': [{'grid_ref_start': "A1'", 'grid_ref_end': 'A2', 'grid_refs': ["B1'", "C''1'"],
                          'grid_ref': "A-B x 1-1'", 'note': "1'"},
                         {'grid_ref': "~1, detail-box labels '1'/'2' (bottom)"},
                         {'grid_ref': "B-A x 1-1' (approx), box '3 +0.50 1', see view1's note"}]}
    json.dump(master, open(os.path.join(h, 'h_หน้า00_gridline.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(page, open(os.path.join(h, 'h_หน้า19.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    stg = {'house_dir': h, 'master': 'h_หน้า00_gridline.json', 'pages_swept': ['p.png'],
           'chain_fixes': [{'index': 0, 'segments': [{'from': '@-1.0', 'to': '1', 'value_m': 1.0},
                                                     {'from': '1', 'to': '2', 'value_m': 2.4},
                                                     {'from': '@1.2', 'to': '2', 'value_m': 1.2}]}],
           'dimension_chains': [{'axis': 'x', 'source_image': 'q.png', 'segments': [
               {'from': '3', 'to': '@7.0', 'value_m': 1.0}, {'from': '@7.0', 'to': '@8.2', 'value_m': 1.2}]},
               {'axis': 'y', 'source_image': 'q.png', 'segments': [{'from': 'B', 'to': '@2.5', 'value_m': 0.1},
                                                                   {'from': 'A', 'to': '@0.5', 'value_m': 0.5}]}],
           'unassigned_dimensions': [], 'warnings': [],
           'eyeball_ok': [page['elements'][1]['grid_ref'], page['elements'][2]['grid_ref']]}   # quoted/possessive
    sp = os.path.join(d, 's.json')
    json.dump(stg, open(sp, 'w', encoding='utf-8'), ensure_ascii=False)
    out = []
    assert not run(sp, apply=True, log=out.append), 'must refuse: note field equals a renamed id'
    assert any('CHECK BY HAND' in o for o in out)
    page['elements'][0]['note'] = 'moved'
    json.dump(page, open(os.path.join(h, 'h_หน้า19.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    out = []
    assert run(sp, apply=True, log=out.append), out
    m = json.load(open(os.path.join(h, 'h_หน้า00_gridline.json'), encoding='utf-8'))
    x = {l['id']: l['pos_m'] for l in m['grid']['x_lines']}
    assert x == {"1'": -1.0, '1': 0.0, "1''": 1.2, '2': 2.4, '3': 6.0, "3'": 7.0, "3''": 8.2}, x
    seg = m['grid']['dimension_chains'][0]['segments']
    assert seg[0]['from'] == "1'" and seg[2]['from'] == "1''", seg   # @1.2 = old 1', renamed in the same run
    y = {l['id']: l['pos_m'] for l in m['grid']['y_lines']}
    assert y["B'"] == 2.5, y
    # base A: new 0.5, Makham's A' (1.0) and the misfiled C' (2.0, above B) all re-sequenced in reading order
    assert (y["A'"], y["A''"], y["A'''"]) == (0.5, 1.0, 2.0) and "C'" not in y, y
    e = json.load(open(os.path.join(h, 'h_หน้า19.json'), encoding='utf-8'))['elements'][0]
    assert (e['grid_ref_start'], e['grid_refs'], e['grid_ref']) == ("A1''", ["B1''", "C''1''"], "A-B x 1-1''"), e
    q = json.load(open(os.path.join(h, 'h_หน้า19.json'), encoding='utf-8'))['elements'][1]['grid_ref']
    assert q == "~1, detail-box labels '1'/'2' (bottom)", q   # quoted label untouched
    q = json.load(open(os.path.join(h, 'h_หน้า19.json'), encoding='utf-8'))['elements'][2]['grid_ref']
    assert q == "B-A x 1-1'' (approx), box '3 +0.50 1', see view1's note", q   # ref renames; box + possessive don't
    # a chain that doesn't close is refused
    stg2 = dict(stg, chain_fixes=[], dimension_chains=[{'axis': 'x', 'source_image': 'r.png', 'segments': [
        {'from': '1', 'to': '2', 'value_m': 2.5}]}])
    json.dump(stg2, open(sp, 'w', encoding='utf-8'), ensure_ascii=False)
    out = []
    assert not run(sp, apply=False, log=out.append) and any('MISMATCH' in o for o in out), out
    # merge: a wrong line removed, its refs moved to the line at into_pos (house 03's 2', 2026-09-29)
    json.dump({'house_dir': h, 'master': 'h_หน้า00_gridline.json',
               'merge_lines': [{'axis': 'x', 'id': "1''", 'into_pos': 2.4}]}, open(sp, 'w', encoding='utf-8'))
    out = []
    assert run(sp, apply=True, log=out.append), out
    x = {l['id']: l['pos_m'] for l in json.load(open(os.path.join(h, 'h_หน้า00_gridline.json'), encoding='utf-8'))['grid']['x_lines']}
    assert "1''" not in x and x["1'"] == -1.0, x
    e = json.load(open(os.path.join(h, 'h_หน้า19.json'), encoding='utf-8'))['elements'][0]
    assert e['grid_ref_start'] == 'A2', e
    # an unswept master stays unswept: a rename-only run must not invent empty arrays
    h2 = os.path.join(d, '02บ้าน')
    os.makedirs(h2)
    json.dump({'pattern': 'grid_master', 'warnings': [], 'grid': {
        'x_lines': [{'id': '1', 'pos_m': 0.0, 'type': 'named'}, {'id': "2'", 'pos_m': 1.0, 'type': 'dummy'},
                    {'id': '2', 'pos_m': 2.0, 'type': 'named'}], 'y_lines': [{'id': 'A', 'pos_m': 0.0, 'type': 'named'}]}},
              open(os.path.join(h2, 'h_หน้า00_gridline.json'), 'w', encoding='utf-8'))
    json.dump({'house_dir': h2, 'master': 'h_หน้า00_gridline.json'}, open(sp, 'w', encoding='utf-8'))
    assert run(sp, apply=True, log=lambda *_: None)
    g2 = json.load(open(os.path.join(h2, 'h_หน้า00_gridline.json'), encoding='utf-8'))['grid']
    assert [l['id'] for l in g2['x_lines']] == ['1', "1'", '2'] and 'dimension_chains' not in g2 and 'z_levels' not in g2, g2
    selftest_review(d)
    print('selftest ok')


def selftest_review(d):
    """The adversarial review of 2026-09-29: each case once."""
    import stat
    n = [0]

    def house(x, y, pages):
        n[0] += 1
        h = os.path.join(d, f'r{n[0]}')
        os.makedirs(h)
        json.dump({'pattern': 'grid_master', 'warnings': [], 'grid': {'x_lines': x, 'y_lines': y}},
                  open(os.path.join(h, 'h_หน้า00_gridline.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        for i, refs in enumerate(pages):
            json.dump({'elements': [{'grid_ref': r} for r in refs]},
                      open(os.path.join(h, f'h_หน้า{10 + i}.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        return h

    def go(h, apply=True, **stg):
        sp = os.path.join(d, 'r.json')
        json.dump(dict(stg, house_dir=h, master='h_หน้า00_gridline.json'), open(sp, 'w', encoding='utf-8'), ensure_ascii=False)
        out = []
        try:
            return run(sp, apply=apply, log=out.append), out
        except SystemExit as e:
            return 'EXIT', [str(e)]

    def ids(h, ax):
        return [l['id'] for l in json.load(open(os.path.join(h, 'h_หน้า00_gridline.json'), encoding='utf-8'))['grid'][f'{ax}_lines']]

    def tick(ax, a, b, v):
        return [{'axis': ax, 'source_image': 't.png', 'segments': [{'from': a, 'to': b, 'value_m': v}]}]
    N = lambda i, p: {'id': i, 'pos_m': p, 'type': 'named'}
    D = lambda i, p: {'id': i, 'pos_m': p, 'type': 'dummy'}
    X, Y = [N('1', 0.0), N('2', 4.0)], [N('A', 0.0), N('B', 3.0)]
    # a ref naming a line the master lacks must not be bound by a new line (house 11 bathroom "1-1'")
    h = house(X, Y, [["A-B x 1-1' (bathroom)"]])
    ok, out = go(h, dimension_chains=tick('x', '@-0.6', '1', 0.6))
    assert ok is False and any('did not have' in o for o in out), out
    # merge_lines never takes a printed line ("2nd floor" -> "3nd floor")
    h = house([N('1', 0.0), N('2', 3.0), N('3', 3.0)], Y, [['1-2, 2nd floor, 2.70m']])
    ok, out = go(h, merge_lines=[{'axis': 'x', 'id': '2', 'into_pos': 3.0}])
    assert ok == 'EXIT' and 'dummies only' in out[0], out
    # a new tick whose rule name is a printed id gets a real name, never "@pos" (house 12 ง')
    h = house(X, [N("ง'", -2.8), N('ง', 0.0), N('ค', 4.0)], [])
    ok, out = go(h, pages_swept=['t.png'], dimension_chains=tick('y', 'ง', '@0.5', 0.5))
    assert ok is True and ids(h, 'y') == ["ง'", 'ง', "ง''", 'ค'], (out, ids(h, 'y'))
    # an id already twice in the master stops the run
    h = house([N('1', 0.0), D("1'", 1.0), D("1'", 2.0), N('2', 3.0)], Y, [["A1'"]])
    assert go(h)[0] == 'EXIT'
    # applying a staging twice is refused (one entry per printed row per sheet)
    h = house(X, Y, [])
    assert go(h, dimension_chains=tick('x', '1', '@1.5', 1.5))[0] is True
    ok, out = go(h, dimension_chains=tick('x', '1', '@1.5', 1.5))
    assert ok is False and any('looks applied' in o for o in out), out
    # a write that fails half-way is rolled back: every file of the house as it was
    h = house([N('1', 0.0), D("1'", 1.8), N('2', 3.0)], Y, [["A1'"], ["A1'"]])
    snap = {f: open(os.path.join(h, f), 'rb').read() for f in os.listdir(h)}
    lock = os.path.join(h, 'h_หน้า11.json')
    os.chmod(lock, stat.S_IREAD)
    try:
        ok, out = go(h, dimension_chains=tick('x', '1', '@0.9', 0.9))
    finally:
        os.chmod(lock, stat.S_IWRITE | stat.S_IREAD)
    assert ok == 'EXIT' and 'rolled back' in out[0], out
    assert {f: open(os.path.join(h, f), 'rb').read() for f in os.listdir(h)} == snap
    # "D-C'x1-2" is a ref (x separator, not a possessive); Thai glued to prose blocks until eyeballed
    h = house([N('1', 0.0), D("1'", 1.2), N('2', 2.4)], [N('ก', 0.0), N('ข', 3.0), D("ข'", 4.0), N('ค', 6.0)],
              [["ก-ข x 1'x2"], ["แนวข'-ค x 1-2"]])
    stg = dict(dimension_chains=tick('x', '@-1.0', '1', 1.0) + tick('y', 'ข', '@3.5', 0.5))
    ok, out = go(h, **stg)
    assert ok is False and any('EYEBALL' in o and 'นวข' in o for o in out), out
    assert go(h, eyeball_ok=["แนวข'-ค x 1-2"], **stg)[0] is True
    assert json.load(open(os.path.join(h, 'h_หน้า10.json'), encoding='utf-8'))['elements'][0]['grid_ref'] == "ก-ข x 1''x2"
    # an axis the staging doesn't touch keeps its order, pos-less dummies included
    y = [N('ก', 0.0), {'id': "ข'", 'pos_m': None, 'type': 'dummy'}, N('ข', 4.5), N('ค', 9.0)]
    h = house(X, y, [["ข'1"]])
    assert go(h, dimension_chains=tick('x', '1', '2', 4.0))[0] is True and ids(h, 'y') == ['ก', "ข'", 'ข', 'ค']
    # ...and when its tick is finally printed, one run creates the point and merges the pos-less dummy into it
    ok, out = go(h, dimension_chains=tick('y', 'ก', '@2.25', 2.25), merge_lines=[{'axis': 'y', 'id': "ข'", 'into_pos': 2.25}])
    assert ok is True and ids(h, 'y') == ['ก', "ก'", 'ข', 'ค'], (out, ids(h, 'y'))
    assert json.load(open(os.path.join(h, 'h_หน้า10.json'), encoding='utf-8'))['elements'][0]['grid_ref'] == "ก'1"
    # staging arithmetic noise is rounded to the millimetre (2.8 + 0.15 = 2.9499999999999997)
    h = house(X, Y, [])
    assert go(h, pages_swept=['t.png'], z_levels_add=[{'id': 'top', 'level_m': 2.8 + 0.15, 'type': 'dummy'}])[0] is True
    zl = json.load(open(os.path.join(h, 'h_หน้า00_gridline.json'), encoding='utf-8'))['grid']['z_levels']
    assert zl[-1]['level_m'] == 2.95 and _num(2.8 + 0.15, True) == repr(2.8 + 0.15), zl


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        print(__doc__)
    elif a[0] == '--selftest':
        selftest()
    else:
        ok = run(a[0], apply='--apply' in a, accept_mismatch='--accept-mismatch' in a)
        sys.exit(0 if ok else 1)
