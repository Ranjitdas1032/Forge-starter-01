# DECISIONS.md — decision & learnings log

A short running note of the real choices you made: what you tried, what failed and why, what
you changed. This is your engineering judgement on the record — it is what separates a builder
from a button-presser, and it is graded (challenge brief section 08).

Append a 1–2 line entry whenever you make a real decision or hit/fix a wall. Add a timestamp.

Format:
`[HH:MM] <decision or problem> → <what you did and why>`

---

## Project Context

**Project Goal:**
Build a Claude Code plugin that audits SEO exports (Screaming Frog CSV format) against deterministic rules, detects issues, prioritizes them, generates fixes, and renders a live dashboard + exportable HTML/JSON reports.

**Architecture Summary:**
- `skills/seo-audit/SKILL.md` — main orchestrator
- `agents/` — sub-agents: ingest, auditor, fixer, reporter (each handles one phase)
- `seo/detector.py` — deterministic rule-based issue detection (CSV/pandas)
- `mcp/server.py` — MCP tool registry + live dashboard (localhost:7700)
- `dashboard/` — HTML/JS cockpit for real-time issue viewing
- `outputs/` — generated `report.json` (must match `report.schema.json`) + `report.html`

**Rulebook Summary (from rulebook.md):**
- Pre-filter: only `text/html` content; duplicates only on Indexable 200 pages
- 17 issue types across: titles, meta descriptions, H1s, links (broken/redirect/chains), content (thin/orphan), security, indexability
- Severity: High / Medium / Low
- Redirect chains: build {Address → Redirect URL} map; chain = redirect target that is itself a key in that map
- Count = affected URLs; no hard-coded URLs

**Build Plan:**
1. Complete `seo/detector.py` for full rulebook coverage (17 issue types)
2. Implement fixer agent (title/meta rewrites within limits, redirect mapping)
3. Improve dashboard & report formatting for client readiness
4. Commit incrementally (≥10 commits); maintain audit trail

---

## My log
- `[15:56]` **CSV schema validation on load** → Added required column checks (Address, Status Code, Content Type) in `load_rows()` to fail fast if export is malformed; prevents cascading KeyErrors downstream.
- `[15:56]` **KeyError crash risk on missing columns** → Replaced all direct dict access `r["Address"]` with `r.get("Address", "")` throughout detector.py; the hidden test export may have different or missing columns.
- `[15:57]` **NaN string handling** → Updated `_int()` and `_float()` to explicitly handle "nan", "NaN", "None", "n/a" strings (case-insensitive) before numeric conversion; SF exports sometimes contain these.
- `[15:57]` **File handle leaks in reporting** → Changed `open(path).read()` and `open(path).write()` to `with open(path) as f:` context managers in `seo_report()`, `seo_export()`, and dashboard GET handlers.
- `[15:57]` **Hardcoded company branding** → Removed "NMG Technologies" hardcodes from `generate_title()` and `generate_meta()`; now accepts `company` parameter (default "Your Company") for configurability.
- `[15:57]` **Hidden export robustness** → All changes assume CSV columns may differ, be empty, or contain unexpected values; code now degrades gracefully instead of crashing.
