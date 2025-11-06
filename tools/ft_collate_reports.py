#!/usr/bin/env python3
import json
import statistics
import sys
from pathlib import Path

SRC = Path(".firsttry/reports")
OUT_JSON = Path(".firsttry/tier_summary.json")
OUT_MD   = Path(".firsttry/tier_summary.md")

def load_reports():
    items = []
    for p in sorted(SRC.glob("*.json")):
        name = p.stem  # 20251106T123456Z_tier_phase
        try:
            _, tier, phase = name.split("_")[-3:]
        except ValueError:
            # fallback: detect phase keywords
            s = name.lower()
            phase = "warm" if "warm" in s else "cold"
            parts = s.split("_")
            tier = next((x for x in parts if x not in ("cold","warm")), "unknown")
        data = json.loads(p.read_text())
        items.append({"path": str(p), "tier": tier, "phase": phase, "data": data})
    return items

def summarize(items):
    tiers = {}
    for it in items:
        tier = it["tier"]; phase = it["phase"]; checks = it["data"].get("checks", {})
        rec = tiers.setdefault(tier, {"cold": {}, "warm": {}})
        stats = {"count": 0, "ok":0, "fail":0, "skip":0, "error":0,
                 "durations_ms": [], "checks": {}}
        for k,v in checks.items():
            st = v.get("status","")
            cs = v.get("cache_status")
            d  = (v.get("duration_ms") or 0)
            stats["count"] += 1
            stats[st] = stats.get(st,0) + 1
            stats["durations_ms"].append(d)
            stats["checks"][k] = {"status": st, "cache_status": cs, "duration_ms": d}
        rec[phase] = stats
    # compute warm hit rate & medians
    for tier, phases in tiers.items():
        warm = phases.get("warm", {})
        cold = phases.get("cold", {})
        wh = 0; wt = 0
        for k,v in warm.get("checks", {}).items():
            wt += 1
            if v.get("cache_status") in ("hit-local","hit-remote"):
                wh += 1
        warm["cache_hit_rate"] = (wh / wt) if wt else None
        for ph in ("cold","warm"):
            ds = phases.get(ph,{}).get("durations_ms", [])
            if ds:
                phases[ph]["p50_ms"] = int(statistics.median(ds))
                phases[ph]["p95_ms"] = int(statistics.quantiles(ds, n=20)[18]) if len(ds) > 5 else max(ds)
            else:
                phases[ph]["p50_ms"] = phases[ph]["p95_ms"] = None
        # detect regressions: warm slower than cold by >25%
        wc = phases.get("warm",{}).get("p50_ms"); cc = phases.get("cold",{}).get("p50_ms")
        phases["regression_flag"] = bool(wc and cc and wc > 1.25*cc)
    return tiers

def write_outputs(tiers):
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"tiers": tiers}, indent=2))
    # Markdown
    lines = ["# FirstTry Tier Summary\n"]
    for tier, ph in sorted(tiers.items()):
        lines.append(f"## {tier}\n")
        c = ph.get("cold",{}); w = ph.get("warm",{})
        lines.append(f"- Cold: p50={c.get('p50_ms')}ms, p95={c.get('p95_ms')}ms, ok={c.get('ok',0)}/{c.get('count',0)}")
        lines.append(f"- Warm: p50={w.get('p50_ms')}ms, p95={w.get('p95_ms')}ms, ok={w.get('ok',0)}/{w.get('count',0)}, cache_hit_rate={w.get('cache_hit_rate')}")
        if ph.get("regression_flag"):
            lines.append("- ⚠️ Warm slower than cold (>25%)")
        # slowest 3 warm checks
        checks = w.get("checks",{})
        slow = sorted(checks.items(), key=lambda kv: kv[1].get("duration_ms") or 0, reverse=True)[:3]
        if slow:
            lines.append("- Slowest warm checks:")
            for k,v in slow:
                lines.append(f"  - {k}: {v.get('duration_ms')}ms ({v.get('cache_status')})")
        lines.append("")
    OUT_MD.write_text("\n".join(lines))

def main():
    items = load_reports()
    if not items:
        print(f"No reports in {SRC} — run scripts/ft_tier_sweep.sh first."); sys.exit(1)
    tiers = summarize(items)
    write_outputs(tiers)
    print(f"Wrote {OUT_JSON} and {OUT_MD}")

if __name__ == "__main__":
    main()
