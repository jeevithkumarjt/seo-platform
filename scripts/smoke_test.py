"""Full-stack smoke test. Stdlib only. Fails loudly on any contract violation.
Contract per result: key/label/category/status/severity/found/source/checked_at present;
how_to_fix REQUIRED when status in (warning, fail, unavailable); checked_at ISO-parseable;
status/severity/category from closed sets. No hallucination: unavailable rows must say why."""
import json, sys, urllib.request, urllib.parse
from datetime import datetime

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
FAILS: list[str] = []
PASSES = 0

STATUSES = {"pass", "warning", "fail", "unavailable", "info"}
SEVS = {"ok", "info", "warning", "critical", "unknown"}
CATS = {"A-onpage","B-technical","C-structured","D-performance","E-a11y","F-links","G-content",
        "H-xbrowser","I-jshealth","J-techstack","K-aeo","L-rank","M-gsc","N-architecture",
        "O-security","Q-pwa","R-intl","S-frontend","T-local"}

def req(method, path, body=None, timeout=180):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode())

def check(name, cond, detail=""):
    global PASSES
    if cond: PASSES += 1; print(f"  PASS {name}")
    else: FAILS.append(f"{name} :: {detail}"); print(f"  FAIL {name} :: {detail}")

def validate_audit(audit, ctx):
    global PASSES
    res = audit.get("results", [])
    check(f"{ctx}: results non-empty", len(res) > 20, f"got {len(res)}")
    s = audit.get("summary", {})
    check(f"{ctx}: summary adds up", s.get("total") == len(res), str(s))
    bad = 0
    for r in res:
        errs = []
        for k in ("key","label","category","status","severity","found","source","checked_at"):
            if not r.get(k): errs.append(f"empty {k}")
        if r.get("status") not in STATUSES: errs.append(f"bad status {r.get('status')}")
        if r.get("severity") not in SEVS: errs.append(f"bad severity {r.get('severity')}")
        if r.get("category") not in CATS: errs.append(f"bad category {r.get('category')}")
        if r.get("status") in ("warning","fail","unavailable") and not (r.get("how_to_fix") or "").strip():
            errs.append("missing how_to_fix")
        try: datetime.fromisoformat(r["checked_at"])
        except Exception: errs.append("bad checked_at")
        if errs: bad += 1; FAILS.append(f"{ctx}:{r.get('category')}/{r.get('key')} :: {'; '.join(errs)}")
    if bad == 0: PASSES += 1; print(f"  PASS {ctx}: all {len(res)} results valid (fix present on every warning/fail/unavailable)")
    else: print(f"  FAIL {ctx}: {bad} invalid results (see list)")
    cats_hit = {r["category"] for r in res}
    missing = {"A-onpage","B-technical","C-structured","D-performance","E-a11y","F-links","G-content",
               "J-techstack","K-aeo","L-rank","O-security","Q-pwa","R-intl","S-frontend"} - cats_hit
    check(f"{ctx}: core categories covered", not missing, f"missing {missing}")

print("== health ==")
st, h = req("GET", "/health", timeout=15); check("health ok", h.get("status") == "ok", str(h))

print("== sites ==")
st, s1 = req("POST", "/api/v1/sites", {"url": "https://example.com", "label": "Example"})
check("create site 1", isinstance(s1.get("id"), int), str(s1))
st, s2 = req("POST", "/api/v1/sites", {"url": "example.org", "label": "Org", "is_local_business": True})
check("create site 2 (local, no-scheme normalize)", s2.get("url") == "https://example.org", str(s2))
st, lst = req("GET", "/api/v1/sites", timeout=15); check("list sites", len(lst.get("sites", [])) >= 2, str(lst))

print("== audit 1 (keyword + local + no rendered) ==")
st, a1 = req("POST", "/api/v1/audit/run", {"url": "https://example.com", "keyword": "example", "is_local_business": True, "include_rendered": False})
validate_audit(a1, "audit1")
check("audit1: keyword rows present", any(r["key"].startswith("g-kw-") for r in a1["results"]))
check("audit1: local rows ran (not skipped)", any(r["key"] == "t-schema" for r in a1["results"]))
check("audit1: content stats present", all(any(r["key"] == k for r in a1["results"]) for k in ("g-readtime","g-sentences","g-paras")))

print("== audit 2 (bare url) ==")
st, a2 = req("POST", "/api/v1/audit/run", {"url": "example.org", "include_rendered": False})
validate_audit(a2, "audit2")

print("== audit 3 (bare url, rendered = browser engines) ==")
st, a3 = req("POST", "/api/v1/audit/run", {"url": "https://example.com", "include_rendered": True}, timeout=240)
validate_audit(a3, "audit3")
res3 = a3["results"]
check("audit3: H cross-browser ran (chromium)", any(r["key"].startswith("h-chromium") for r in res3), "no h-chromium")
check("audit3: I js/css health present", any(r["category"] == "I-jshealth" for r in res3), "no I-jshealth rows")
check("audit3: screenshot image evidence (when PSI key set)",
      any(isinstance(r.get("evidence"), dict) and r["evidence"].get("type") == "image" for r in res3 if r["source"].startswith("PageSpeed")),
      "no screenshot image evidence")

print("== history / alerts / techstack / compare ==")
st, hst = req("GET", f"/api/v1/audit/history?site_id={s1['id']}", timeout=15)
check("history trend has entries", len(hst.get("trend", [])) >= 1, str(hst)[:120])
st, al = req("GET", "/api/v1/alerts", timeout=15); check("alerts feed shape", "alerts" in al, str(al)[:120])
st, df = req("GET", f"/api/v1/techstack/diff?site_id={s1['id']}", timeout=15)
check("techstack diff shape", "snapshots" in df, str(df)[:120])
st, cp = req("GET", f"/api/v1/sites/compare?ids={s1['id']},{s2['id']}", timeout=15)
check("compare 2 sites", len(cp.get("compare", [])) == 2 and all(c["summary"] for c in cp["compare"]), str(cp)[:200])

print("== integrations ==")
st, ig = req("GET", "/api/v1/integrations", timeout=15)
check("3 integrations listed", set(ig.get("integrations", {})) == {"gsc","pagespeed","webhook"}, str(ig)[:150])
st, sy = req("POST", "/api/v1/integrations/sync?kind=webhook", {}, timeout=30)
check("webhook probe honest-fail (no creds)", sy.get("sync") == "failed" and "integration" in sy, str(sy)[:200])
check("webhook last_error recorded", bool(sy["integration"].get("last_error")), str(sy)[:200])
st, sy2 = req("POST", "/api/v1/integrations/sync?kind=bogus", {}, timeout=15)
check("unknown kind rejected", "error" in sy2, str(sy2)[:120])

print(f"\nRESULT: {PASSES} passed, {len(FAILS)} failed")
sys.exit(1 if FAILS else 0)
