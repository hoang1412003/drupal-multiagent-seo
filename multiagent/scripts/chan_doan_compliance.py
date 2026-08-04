import os, sys, collections
sys.path.insert(0, "scripts"); sys.path.insert(0, "src")
from agents import compliance
from label_helper import parse_sample
GOLD = "../docs/goldset/raw"
dem = collections.Counter()
for sid in ["G-001","G-002","G-003","G-004","G-005","G-006","G-007","G-010"]:
    f = parse_sample(os.path.join(GOLD, f"{sid}.txt"))
    r = compliance.run({"title": f.get("title",""), "body": f.get("body",""),
                        "meta_description": f.get("meta_description","")})
    if r is None:
        print(f"{sid}: None"); continue
    muc = {c["id"]: c["level"] for c in r["criteria"]}
    ap = [k for k,v in muc.items() if v is not None]
    for k,v in muc.items(): dem[(k, v)] += 1
    print(f"{sid}: diem={r['score']:5.1f} ap_dung={len(ap)}/8  " +
          " ".join(f"{k}={'NA' if v is None else v}" for k,v in muc.items()))
print()
for ma in ["CP1","CP2","CP3","CP4","CP5","CP6","CP7","CP8"]:
    print(ma, {("NA" if l is None else l): dem[(ma,l)] for l in (0,1,2,None) if dem[(ma,l)]})
