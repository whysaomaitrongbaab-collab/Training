"""สรุปผลทั้งหลังตาม temperature — 83b8e52c เทียบเฉลย + บ้านเน็ต (ชนเพดาน / gridline / จีน / ชื่อบ้านเทรน)"""
import json, re, sys, os
sys.path.insert(0, 'bench'); import score_house as S
HOUSE = re.compile(r"บ้าน_(?:เล็ก|ใหญ่)_[12]ชั้น_\d+")
P = r"d:/00mk/steel project/training/Training/tune_ai/t05_Destrier/proof/04_vllm_sglang_บนการ์ด/out"
def runs(name):  # (T, path)
    r = [('0.7 เช้า', f'{P}/vllm_{"house" if name=="house" else name}')]
    for T in ('0.4', '0.2', '0.0'):
        r.append((T, f'resultsT/out/{name}_T{T}'))
    return [(t, p) for t, p in r if os.path.exists(f'{p}/summary.json')]
def stats(p):
    s = json.load(open(f'{p}/summary.json', encoding='utf-8'))
    calls = [json.loads(l) for l in open(f'{p}/calls.jsonl', encoding='utf-8')]
    raw = open(f'{p}/result.json', encoding='utf-8').read()
    cap = [c['kind'] for c in calls if (c.get('completion_tokens') or 0) >= 9000]
    g = [c for c in calls if c['kind'] == 'gridline']
    gl = 'วน' if g and (g[0].get('completion_tokens') or 0) >= 9000 else ('ผ่าน' if g and g[0]['json_ok'] else 'ไม่มี/พัง')
    return s['wall_s'], s['all']['json_ok'], s['all']['n'], cap, gl, sum(c.get('cjk', 0) for c in calls), len(HOUSE.findall(raw))
tm, tc = S.truth()
print('== 83b8e52c (มีเฉลย)')
for t, p in runs('house'):
    mm, mc, ok, total = S.model(f'{p}/result.json')
    hit = sum(len(tm[x] & mm[x]) for x in S.PAGES); want = sum(len(tm[x]) for x in S.PAGES); got = sum(len(mm[x]) for x in S.PAGES)
    w, jo, n, cap, gl, cjk, hn = stats(p)
    print(f'T={t:<7} {w:6.0f}s JSON {jo}/{n} มาร์ค {hit}/{want} recall {hit/want:.2f} precision {hit/got if got else 0:.2f} ชนเพดาน {len(cap)} gridline {gl} จีน {cjk} ชื่อบ้านเทรน {hn}')
for h in ('dpt13226_1fl', 'dpt13244_1fl', 'dpt13250_2fl'):
    print(f'== {h}')
    for t, p in runs(h):
        w, jo, n, cap, gl, cjk, hn = stats(p)
        print(f'T={t:<7} {w:6.0f}s JSON {jo}/{n} ชนเพดาน {len(cap)} {cap} gridline {gl} จีน {cjk} ชื่อบ้านเทรน {hn}')
