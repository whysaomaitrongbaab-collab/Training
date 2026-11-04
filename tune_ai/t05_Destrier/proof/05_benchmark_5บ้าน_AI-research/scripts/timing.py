import json, os
B = os.path.dirname(os.path.abspath(__file__))
print(f"{'บ้าน':<8}{'หน้า':>5}{'รวม(นาที)':>10}{'วิ/หน้า':>8}{'pass0(วิ)':>10}{'pass2(วิ)':>10}{'คำขอ':>6}{'JSONผ่าน':>9}{'token ออก':>10}{'tok/s':>7}{'ชนเพดาน':>8}")
tot = [0, 0, 0]
for t in ("TEST-01", "TEST-02", "TEST-03", "TEST-04", "TEST-05"):
    sp = os.path.join(B, "out", t, "vllm", "summary.json")
    if not os.path.exists(sp): print(t, "— ยังไม่มีผล"); continue
    s = json.load(open(sp, encoding="utf-8")); n = len(json.load(open(os.path.join(B, t, "job.json")))["payload"]["pages"])
    calls = [json.loads(l) for l in open(os.path.join(B, "out", t, "vllm", "calls.jsonl"), encoding="utf-8")]
    cap = sum(1 for c in calls if c.get("finish") == "length")
    tm = s.get("timings") or {}; a = s["all"]
    tot[0] += n; tot[1] += s["wall_s"]; tot[2] += 1
    print(f"{t:<8}{n:>5}{s['wall_s']/60:>10.1f}{s['wall_s']/n:>8.1f}{tm.get('pass0_s',0):>10.0f}{tm.get('pass2_s',0):>10.0f}{a['n']:>6}{a['json_ok']:>9}{a['completion_tokens'] or 0:>10}{a['tok_per_s'] or 0:>7}{cap:>8}")
print(f"รวม {tot[2]} หลัง {tot[0]} หน้า {tot[1]/60:.1f} นาที · เฉลี่ย {tot[1]/tot[0]:.1f} วิ/หน้า")
