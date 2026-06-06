# AUDIT.md — code inspection & findings

Comprehensive audit of detector.py, run.py, and mcp/server.py against rulebook.md and report.schema.json.
Date: 2026-06-06 | Do not edit files; findings only.

---

## Missing Detectors (from rulebook.md)

**Currently implemented (7/17):**
- missing_title ✓
- duplicate_title ✓
- title_too_long ✓
- broken_link ✓
- server_error ✓
- redirect ✓
- orphan_page ✓

**NOT implemented (10/17):**
- `title_too_short` — `Title 1 Length < 30 (and not empty)` on indexable pages
- `missing_meta_description` — `Meta Description 1` empty, indexable 200 page
- `duplicate_meta_description` — same `Meta Description 1` on 2+ indexable URLs
- `meta_description_too_long` — `Meta Description 1 Length > 155`
- `missing_h1` — `H1-1` empty on a 200 page
- `duplicate_h1` — same `H1-1` on 2+ indexable URLs
- `redirect_chain` — build {Address → Redirect URL} map; chain = target is itself a key
- `thin_content` — `Word Count < 200` on indexable page
- `non_indexable_but_linked` — `Indexability = Non-Indexable AND Inlinks > 0`
- `slow_page` — `Response Time > 1.0`

See detector.py:94–97 TODOs.

---

## CRITICAL Issues

### 1. Status code detectors ignore content-type filter
**Location:** detector.py:77–85 (`broken_link`, `server_error`, `redirect`)

**Problem:** Rules state "only consider rows where Content Type contains text/html", but these
detectors iterate over `rows` (all rows) instead of `html` (filtered).
- `broken_link`: uses `rows` instead of `html`
- `server_error`: uses `rows` instead of `html`
- `redirect`: uses `rows` instead of `html`

**Impact:** Will report non-HTML resources (JS, images, APIs) as broken links. On hidden export with
different crawl scope, accuracy will drop significantly.

**Fix:** Change all three to filter through `html` list, apply same pattern as `orphan_page` (idx200).

---

### 2. No schema validation before writing report.json
**Location:** server.py:96 & run.py:49

**Problem:** CLAUDE.md (line 18) states: "`outputs/report.json` MUST match `report.schema.json`.
Validate before declaring done." However, `seo_report()` writes JSON without validation.

**Impact:** If detector bugs or incomplete fixes create invalid JSON (wrong severity enum, missing
required fields), grader will fail silently or with a cryptic message.

**Risk:** On hidden export, unvalidated output could crash the grader's test harness.

---

### 3. Environment variable name mismatch
**Location:** server.py:22

**Problem:** `MODEL = os.environ.get("RADAR_MODEL", "qwen3.5:9b")`

The variable is named `RADAR_MODEL` (appears to be copy-paste from a different project) but the
README and code context suggest SEO-specific naming.

**Impact:** Environment variable documentation will be confusing; CI/CD scripts may set wrong var name.

---

## HIGH Severity Issues

### 1. Incomplete duplicate detection for meta description & H1
**Location:** detector.py:62–69 (title duplicates only)

**Problem:** Duplicate detection for title works correctly, filtering to `idx200` (indexable + 200),
but the rule applies the same filter to meta descriptions and H1s. These detectors don't exist yet,
so when implemented, must use same filter.

**Impact:** If future implementer adds meta/H1 duplicate detection without filtering to indexable
pages, will over-count issues.

---

### 2. Hard-coded column names with no fallback
**Location:** detector.py:38–40, throughout

**Problem:** Code accesses columns like `"Title 1"`, `"Status Code"`, `"Indexability"` directly.
If Screaming Frog changes export format or columns are missing, `.get()` returns None and parsing fails.

**Risk:** Hidden export may use different column names (e.g., "Page Title" vs "Title 1"). Code will
silently skip those rows or produce wrong counts.

**Example:** Line 55: `idx200 = [r for r in html if is_200(r) and indexable(r)]` — if Status Code
or Indexability columns are missing/renamed, idx200 becomes empty.

---

### 3. Float comparison without epsilon tolerance
**Location:** detector.py:31–35 (not yet critical, but slow_page detector will use this)

**Problem:** `_float()` conversion for Response Time values could be unstable with floating-point
rounding. Slow_page rule: `Response Time > 1.0`. If export has `1.0000001` due to precision, direct
comparison may fail.

**Impact:** Edge-case pages just over the threshold may be missed.

---

### 4. Missing redirect_chain implementation
**Location:** detector.py:95 (TODO)

**Problem:** Redirect chain detection requires building a map and checking for cycles. Not started.
Rule is complex: "a redirect whose Redirect URL is itself a redirecting URL" + handling loops.

**Risk:** Redirect chains often indicate configuration errors. Scoring heavily on hidden export
requires correct implementation. No cycle detection = infinite loops in fix recommendations.

---

## MEDIUM Severity Issues

### 1. Empty/None handling for Redirect URL field
**Location:** Not yet implemented (redirect_chain detector)

**Problem:** When building redirect map, must handle rows where Redirect URL is empty. If redirect
chain detector doesn't check for None/"", it could crash or create incomplete map.

**Risk:** Site with some 3xx responses but missing Redirect URL values will cause KeyError or
logic error.

---

### 2. Recommendations are hard-coded in run.py
**Location:** run.py:40–45

**Problem:** Starter builds recommendations from top-5 issues by picking first N issue types. This
is not model-driven; champion tier requires AI-generated recommendations.

**Current:** `"Fix the {i['count']} {i['severity']}-severity '{i['type']}' issue(s) first."`

**Impact:** Grader expects intelligent prioritization. Starter recommendations are purely generic.

---

### 3. No error handling for missing export directory
**Location:** detector.py:18–21, run.py:26–28

**Problem:** If `internal_all.csv` doesn't exist or export_dir is invalid, `load_rows()` raises
FileNotFoundError with no context.

**Impact:** Grader or user gets cryptic traceback instead of actionable error.

---

### 4. Incomplete fixes object in report
**Location:** server.py:76, run.py:47

**Problem:** `run.py` sets `RUN["model_calls"] = 0` and `RUN["fixes"]` is empty dict. Schema allows
`fixes` to be missing (not in required), but `run_meta.model_calls` IS required (schema line 70).

**Risk:** If fixes are never set, report will have empty or missing fix blocks, confusing clients.

---

## LOW Severity Issues

### 1. Orphan page detection excludes 3xx redirects unintentionally
**Location:** detector.py:88–90

**Problem:** Orphan detection uses `idx200` which filters to Status Code 200. A 3xx redirect with
no inlinks is technically orphaned but won't be caught. Per rulebook, rule applies to "indexable
200 pages", so this is **correct by design**, but note: redirects are never orphaned by definition.

---

### 2. No input validation for export directory format
**Location:** run.py:26, detector.py:18

**Problem:** Script assumes export_dir contains exactly `internal_all.csv`. No check for issue CSVs
in `issues_reports/` subfolder. If structure differs, silent failure.

**Impact:** Grader's export may use different structure. Code should validate at entry point.

---

### 3. HTML export has no accessibility features
**Location:** server.py:107–133

**Problem:** Rendered HTML uses inline styles, no semantic landmarks, no aria labels, no alt text
for color-coded severity badges.

**Impact:** Exported report.html fails accessibility audit. Non-issue for grading, but bad for
client deliverable.

---

### 4. No model_calls tracking in detector
**Location:** detector.py, run.py:47

**Problem:** Detector is 100% deterministic (no model calls), but champion tier's fixer will call
the model. No hook in detector to track calls; must be done in fixer agent.

**Current:** run.py hard-codes `model_calls = 0`.

---

## Rulebook Violations

| Rule | Current Code | Violation |
|------|--------------|-----------|
| "Filter to text/html before title checks" | broken_link/server_error/redirect use `rows`, not `html` | 🔴 HIGH |
| "Duplicates only on indexable 200 pages" | Implemented correctly for titles; meta/H1 TBD | ⚠️ MEDIUM (when added) |
| "Title too short: `< 30 AND not empty`" | Not implemented | 🔴 CRITICAL |
| "Meta description too long: `> 155`" | Not implemented | 🔴 CRITICAL |
| "Redirect chain = target is also a key" | Not implemented | 🔴 CRITICAL |
| "Thin content: `Word Count < 200` indexable" | Not implemented | 🔴 CRITICAL |
| "Non-indexable but linked" | Not implemented | 🔴 CRITICAL |
| "Slow page: `Response Time > 1.0`" | Not implemented | 🔴 CRITICAL |

---

## Hidden-Export Risks

1. **Column name assumptions:** Hard-coded names will break if export format changes. No schema
   validation at load time.
   
2. **CSV encoding:** Only tries `utf-8-sig`. If hidden export uses different encoding, silent fail.

3. **Empty/whitespace fields:** Code uses `.strip()` and `.get(..., "")` but doesn't validate
   expected columns exist before processing.

4. **Redirect map cycles:** Redirect chain detector (when implemented) must detect and handle
   cycles (A → B → C → A). Risk: infinite loops in recommendation or validation.

5. **Floating-point precision:** Response Time comparisons could fail due to rounding. Epsilon
   tolerance needed.

6. **Missing issue types:** With only 7/17 detectors, hidden export will score poorly on accuracy
   no matter the CSV content.

---

## Summary by Severity

| Level | Count | Items |
|-------|-------|-------|
| **CRITICAL** | 3 | Status code filter bug, schema validation missing, 10 missing detectors |
| **HIGH** | 4 | Duplicate detection pattern, hard-coded columns, float precision, redirect_chain complex |
| **MEDIUM** | 4 | Redirect URL handling, generic recommendations, missing error handling, incomplete fixes |
| **LOW** | 4 | Orphan by design, export structure assumption, accessibility, model_calls tracking |

---

## Recommendations (Priority Order)

1. **Fix critical filter bug** in broken_link, server_error, redirect detectors (use `html` list).
2. **Add schema validation** before `seo_report()` writes JSON. Use `jsonschema` library.
3. **Implement missing detectors** in order of frequency on sample export (check manually).
4. **Implement redirect_chain** with proper cycle detection and loop handling.
5. **Add error handling** for missing files, columns, and CSV parsing failures.
6. **Fix environment variable** naming (RADAR_MODEL → SEO_MODEL or similar).
7. **Validate column names** at load time; warn if expected columns are missing.

---

End of audit.
