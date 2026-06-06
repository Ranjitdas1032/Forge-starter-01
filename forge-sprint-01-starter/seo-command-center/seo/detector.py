"""
detector.py — deterministic SEO issue detection from a Screaming Frog internal_all.csv.

STARTER IMPLEMENTATION. It already detects several issues so the pipeline runs end to
end. Your job in the Sprint is to COMPLETE the rulebook (see rulebook.md): add the
missing detectors, handle edge cases, and improve accuracy against the hidden export.

Standard library only (csv). Detection is plain Python on purpose — the model is for
judgment (rewriting titles, choosing redirect targets), not for counting rows.
"""

from __future__ import annotations
import csv
import os
from collections import defaultdict


def load_rows(export_dir: str) -> list[dict]:
    path = os.path.join(export_dir, "internal_all.csv")
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        if not rows:
            raise ValueError("CSV is empty")
        required = {"Address", "Status Code", "Content Type"}
        missing = required - set(rows[0].keys() or {})
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        return rows


def _int(v, default=0):
    try:
        s = str(v).strip().lower()
        if s in ("nan", "none", "", "n/a"):
            return default
        return int(float(s))
    except (ValueError, TypeError):
        return default


def _float(v, default=0.0):
    try:
        s = str(v).strip().lower()
        if s in ("nan", "none", "", "n/a"):
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


def is_html(r):  return "text/html" in ((r.get("Content Type") or "") or "").lower()
def is_200(r):   return _int(r.get("Status Code", 0)) == 200
def indexable(r): return ((r.get("Indexability") or "") or "").strip().lower() == "indexable"


def detect(rows: list[dict]) -> list[dict]:
    """Return a list of issue dicts: {type, severity, affected_urls, count, explanation}.
    Complete implementation of all 18 rulebook detectors."""
    issues = []

    def add(t, sev, urls, explanation):
        urls = sorted(set(urls))
        if urls:
            issues.append({"type": t, "severity": sev, "affected_urls": urls,
                           "count": len(urls), "explanation": explanation})

    html = [r for r in rows if is_html(r)]
    idx200 = [r for r in html if is_200(r) and indexable(r)]

    # --- Titles (indexable 200 pages only) ---
    add("missing_title", "High",
        [r.get("Address", "") for r in idx200 if not (r.get("Title 1", "") or "").strip() if r.get("Address")],
        "Indexable pages with no title tag.")

    by_title = defaultdict(list)
    for r in idx200:
        addr = r.get("Address", "")
        if addr:
            t = (r.get("Title 1", "") or "").strip()
            if t:
                by_title[t].append(addr)
    dup_t = [u for urls in by_title.values() if len(urls) > 1 for u in urls]
    add("duplicate_title", "High", dup_t, "Pages sharing an identical title.")

    add("title_too_long", "Medium",
        [r.get("Address", "") for r in idx200
         if (_int(r.get("Title 1 Pixel Width", 0)) > 561 or _int(r.get("Title 1 Length", 0)) > 60) and r.get("Address")],
        "Titles likely truncated in search results.")

    add("title_too_short", "Low",
        [r.get("Address", "") for r in idx200
         if (r.get("Title 1", "") or "").strip() and _int(r.get("Title 1 Length", 0)) < 30 and r.get("Address")],
        "Titles may not display full content in search results.")

    # --- Meta descriptions (indexable 200 pages only) ---
    add("missing_meta_description", "Medium",
        [r.get("Address", "") for r in idx200 if not (r.get("Meta Description 1", "") or "").strip() and r.get("Address")],
        "Indexable pages with no meta description.")

    by_meta = defaultdict(list)
    for r in idx200:
        addr = r.get("Address", "")
        if addr:
            m = (r.get("Meta Description 1", "") or "").strip()
            if m:
                by_meta[m].append(addr)
    dup_m = [u for urls in by_meta.values() if len(urls) > 1 for u in urls]
    add("duplicate_meta_description", "Medium", dup_m,
        "Pages sharing an identical meta description.")

    add("meta_description_too_long", "Low",
        [r.get("Address", "") for r in idx200 if _int(r.get("Meta Description 1 Length", 0)) > 155 and r.get("Address")],
        "Meta descriptions truncated in search results.")

    # --- H1 tags (status 200 pages, not just indexable) ---
    html200 = [r for r in html if is_200(r)]
    add("missing_h1", "Medium",
        [r.get("Address", "") for r in html200 if not (r.get("H1-1", "") or "").strip() and r.get("Address")],
        "Pages with no H1 tag.")

    by_h1 = defaultdict(list)
    for r in idx200:
        addr = r.get("Address", "")
        if addr:
            h = (r.get("H1-1", "") or "").strip()
            if h:
                by_h1[h].append(addr)
    dup_h1 = [u for urls in by_h1.values() if len(urls) > 1 for u in urls]
    add("duplicate_h1", "Low", dup_h1, "Pages sharing an identical H1 tag.")

    # --- Response codes (HTML only) ---
    add("broken_link", "High",
        [r.get("Address", "") for r in html if (400 <= _int(r.get("Status Code", 0)) <= 499) and r.get("Address")],
        "URLs returning a client error (4xx).")
    add("server_error", "High",
        [r.get("Address", "") for r in html if (500 <= _int(r.get("Status Code", 0)) <= 599) and r.get("Address")],
        "URLs returning a server error (5xx).")
    add("redirect", "Medium",
        [r.get("Address", "") for r in html if (300 <= _int(r.get("Status Code", 0)) <= 399) and r.get("Address")],
        "URLs that redirect (3xx).")

    # --- Redirect chains and loops ---
    # Build {Address -> Redirect URL} map for all 3xx rows
    redirect_map = {}
    three_xx = [r for r in html if 300 <= _int(r.get("Status Code")) <= 399]
    for r in three_xx:
        addr = r.get("Address", "").strip()
        target = (r.get("Redirect URL", "") or "").strip()
        if addr and target:
            redirect_map[addr] = target

    # Detect redirect chains: target is itself a key in the map
    chain_urls = [addr for addr, target in redirect_map.items() if target in redirect_map]
    add("redirect_chain", "High", chain_urls,
        "Redirect chains (3xx URL redirects to another 3xx URL).")

    # Detect redirect loops: chain that returns to an earlier URL
    loop_urls = set()
    for addr in chain_urls:
        visited = set()
        current = addr
        while current in redirect_map and current not in visited:
            visited.add(current)
            current = redirect_map[current]
        if current in visited:
            loop_urls.add(addr)
    add("redirect_loop", "High", list(loop_urls),
        "Redirect loops (circular redirect chain).")

    # --- Content quality ---
    add("thin_content", "Low",
        [r.get("Address", "") for r in idx200 if _int(r.get("Word Count", 0)) < 200 and r.get("Address")],
        "Pages with < 200 words (thin content).")

    # --- Page structure ---
    add("orphan_page", "Medium",
        [r.get("Address", "") for r in idx200 if _int(r.get("Inlinks", 0)) == 0 and r.get("Address")],
        "Indexable pages with zero internal links in.")

    add("non_indexable_but_linked", "Medium",
        [r.get("Address", "") for r in html
         if not indexable(r) and _int(r.get("Inlinks", 0)) > 0 and r.get("Address")],
        "Non-indexable pages that are internally linked.")

    # --- Performance ---
    add("slow_page", "Low",
        [r.get("Address", "") for r in rows if _float(r.get("Response Time", 0.0)) > 1.0 and r.get("Address")],
        "Pages with response time > 1.0 second.")

    return issues


def summarize(issues: list[dict]) -> dict:
    by_sev = defaultdict(int)
    for i in issues:
        by_sev[i["severity"]] += 1
    return {"total_issues": len(issues),
            "by_severity": {"High": by_sev["High"], "Medium": by_sev["Medium"], "Low": by_sev["Low"]}}


if __name__ == "__main__":
    import sys, json
    d = sys.argv[1] if len(sys.argv) > 1 else "../sample-export"
    rows = load_rows(d)
    iss = detect(rows)
    print(f"Loaded {len(rows)} rows, detected {len(iss)} issue types.")
    print(json.dumps(summarize(iss), indent=2))
    for i in iss:
        print(f"  [{i['severity']:<6}] {i['type']:<24} x{i['count']}")
