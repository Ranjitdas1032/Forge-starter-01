# CLAUDE.md — project memory for the SEO Command Center build

This file is your **context / memory for the AI**. Claude Code loads it automatically every
session. Strong builders engineer this file instead of re-explaining everything in chat — it
is one of the clearest signals of good practice, and it is graded (see the challenge brief
section 08). Keep it short, specific, and update it as you learn.

Replace the prompts below with your own. This is YOUR file.

## What we are building
A Claude Code plugin that ingests a Screaming Frog SEO export (`internal_all.csv` + issue
CSVs), audits it against the rulebook, prioritizes issues, writes fixes, serves a live
dashboard at localhost:7700, and outputs `outputs/report.json` + `outputs/report.html`.

## Hard rules (the agent must follow these)
- Detect issues in **plain Python** (csv/pandas). Use the model only for judgment
  (rewriting titles/metas, choosing redirect targets). Never feed raw crawl rows to the model.
- `outputs/report.json` MUST match `report.schema.json`. Validate before declaring done.
- Filter to `text/html` + indexable pages before title/meta checks (see `rulebook.md`).
- Do not hard-code anything to the sample export — it must work on an unseen export.
- Keep model calls small and few (free-tier quota). One page per fix call.
- **Robustness**: Never assume column existence; validate CSV schema on load.
- **Robustness**: Use `.get()` for dict access, never direct keys (prevents KeyError on missing columns).
- **Robustness**: Handle NaN, "nan", None, and empty strings in numeric conversions.
- **Robustness**: File handles must use `with` statements; never call `open().read()` or `open().write()`.
- **Robustness**: Make company name / branding configurable, never hardcode "NMG Technologies".

## Architecture (keep it real)
- `skills/seo-audit/SKILL.md` orchestrates. Sub-agents: ingest, auditor, fixer, reporter.
- `seo/detector.py` = deterministic detectors (extend to the full rulebook — biggest score).
- `mcp/server.py` = MCP tools + the live dashboard.

## Conventions
- Commit after each working step with a real message.
- Run `python run.py sample-export/` to test end to end.

## Things I have learned during the build (update this as you go)
- **Crash risk**: Direct dict access `r["Address"]` crashes if column missing; all dict access must use `.get()` with safe defaults.
- **NaN handling**: Screaming Frog exports may contain "nan", "NaN", "None" strings in numeric columns; `_int()` and `_float()` converters must handle these explicitly.
- **CSV schema validation**: Must validate required columns exist in the first row of internal_all.csv (Address, Status Code, Content Type minimum).
- **File handle leaks**: Never use `open(path).read()` or `open(path).write()` — always use `with` context managers.
- **Hardcoded branding**: Do not hardcode company names like "NMG Technologies" in generated titles/metas; make configurable via function parameters.
- **Hidden export differs**: The grader's hidden test export likely has different column names, ordering, or missing optional columns; code must be defensive.
