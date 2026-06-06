# PROMPTS.md — key prompts log

Keep the handful of prompts that actually moved the build. Not every message — the ones that
mattered: the system/sub-agent prompts, the ones you iterated on, the "this finally worked"
moment. This shows how you direct an AI, which is graded (challenge brief section 08).

Format per entry:
- **Prompt** (paste it)
- **For:** what you were trying to do
- **Revised?** did you have to change it, and why

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

## My prompts

1. Read:
- CLAUDE.md
- README.md
- rulebook.md

Create or update:

- PROMPTS.md
- DECISIONS.md

Add:

1. Project goal
2. Architecture summary
3. Rulebook summary
4. Build plan

Do not modify code yet.

2. Read:

- CLAUDE.md
- README.md
- rulebook.md

Inspect:

- seo/detector.py
- run.py
- mcp/server.py

Create AUDIT.md.

List:

- Missing detectors
- Bugs
- Rulebook violations
- Hidden-export risks

Rank:

Critical
High
Medium
Low

Do not edit files.

3.Read AUDIT.md.

Implement every missing rulebook detector.

Required:

- missing title
- duplicate title
- title too long
- title too short
- missing meta
- duplicate meta
- meta too long
- missing h1
- duplicate h1
- 4xx
- 5xx
- redirects
- redirect chains
- redirect loops
- thin content
- orphan pages
- non-indexable linked pages
- slow pages

Use deterministic Python logic.

Do not use LLM calls.

After edits explain:

- files changed
- detectors added

4.Read rulebook.md.

Compare every detector against the rulebook.

Create:

RULEBOOK_CHECK.md

Table:

Rule
Implemented?
Location
Edge Cases

Report any mismatch.
