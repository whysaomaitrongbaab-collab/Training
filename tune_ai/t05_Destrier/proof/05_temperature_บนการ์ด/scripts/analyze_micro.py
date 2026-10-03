"""micro ต่อ temperature: หน้าเดียวยิงซ้ำ 4 รอบ เทียบเฉลย 83b8e52c"""
import json, sys, statistics as stt
sys.path.insert(0, 'bench'); import score_house as S
tm, tc = S.truth()
print(f"{'T':>4} {'งาน':<13} {'ชิ้นต่อรอบ (เฉลย)':<26} {'มาร์คตรงต่อรอบ':<22} {'วิ/คำขอ':>8} {'จีน':>4} {'ชนเพดาน':>7} {'JSON':>5}")
for T in ['0.7', '0.4', '0.2', '0.0']:
    d = f'resultsT/out/micro_T{T}'
    outs = json.load(open(f'{d}/outputs.json', encoding='utf-8'))
    calls = [json.loads(l) for l in open(f'{d}/calls.jsonl', encoding='utf-8')]
    for kind, pg in [('section', 22), ('plan_beam', 20), ('plan_footing', 19)]:
        rs = [o for o in outs if o['kind'] == kind and o['page'] == pg]
        cs = [c for c in calls if c['kind'] == kind]
        cnt, hit = [], []
        for o in rs:
            els = [e for e in ((o['json'] or {}).get('elements') or []) if isinstance(e, dict)]
            ms = {S.norm(S.mark_of(e)) for e in els if S.mark_of(e)}
            cnt.append(len(els)); hit.append(len(tm[pg] & ms))
        print(f"{T:>4} {kind:<13} {str(cnt)+' ('+str(tc[pg])+')':<26} {str(hit)+'/'+str(len(tm[pg])):<22} "
              f"{stt.mean(c['seconds'] for c in cs):8.1f} {sum(c.get('cjk', 0) for c in cs):4d} "
              f"{sum((c.get('completion_tokens') or 0) >= 9000 for c in cs):7d} {sum(c['json_ok'] for c in cs):>2}/{len(cs)}")
