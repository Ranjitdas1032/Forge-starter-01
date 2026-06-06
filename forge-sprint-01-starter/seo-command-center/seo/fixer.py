"""
fixer.py — fix generation for SEO issues (titles, metas, redirects).

Generates ready-to-use fixes with deterministic templates (no model required).
Outputs: titles_metas.csv (url, old_title, new_title, old_meta, new_meta)
         redirect_map.csv (from, to, reason)
"""

from __future__ import annotations
import csv
import os
from collections import defaultdict
from urllib.parse import urlparse


def _extract_domain_title(url: str) -> str:
    """Extract meaningful title from URL path."""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/").split("/")[-1]
        if not path or path.endswith(".html"):
            path = path.replace(".html", "")
        if path:
            return " ".join(w.capitalize() for w in path.replace("-", " ").split())
    except Exception:
        pass
    return "Page"


def _truncate_title(text: str, max_chars: int = 60) -> str:
    """Truncate title to max chars, breaking on word boundaries."""
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    # Truncate and remove trailing incomplete word
    text = text[:max_chars]
    last_space = text.rfind(" ")
    if last_space > max_chars * 0.6:  # Only break if we can keep at least 60% of limit
        text = text[:last_space]
    return text.strip()


def _truncate_meta(text: str, max_chars: int = 155) -> str:
    """Truncate meta description to max chars, breaking on word boundaries."""
    text = (text or "").strip()[:max_chars]
    if len((text or "").strip()) > max_chars:
        text = text.rsplit(" ", 1)[0] + "..."
    return text.strip()


def _ensure_length(text: str, min_chars: int, max_chars: int) -> str:
    """Ensure text is between min and max chars, padding if needed."""
    text = (text or "").strip()
    if len(text) >= min_chars:
        return _truncate_title(text, max_chars)
    # Pad with generic text to meet minimum
    padding = " | NMG Technologies" if len(text) + 18 <= max_chars else ""
    return _truncate_title(text + padding, max_chars) if padding else text


def generate_title(row: dict) -> str:
    """Generate a fixed title (30-60 chars) from row data."""
    existing = (row.get("Title 1") or "").strip()
    h1 = (row.get("H1-1") or "").strip()
    h2 = (row.get("H2-1") or "").strip()
    url = row.get("Address", "")

    # Try combinations to find a good title
    candidates = []

    # 1. Use existing if good length
    if existing and 30 <= len(existing) <= 60:
        candidates.append(existing)

    # 2. H1 combined with H2
    if h1 and h2:
        candidates.append(f"{h1} - {h2}")

    # 3. H1 with domain
    if h1:
        candidates.append(f"{h1} | NMG Technologies")

    # 4. H1 alone (if reasonable)
    if h1 and 15 <= len(h1) <= 65:
        candidates.append(h1)

    # 5. Existing title (truncated)
    if existing:
        candidates.append(existing)

    # 6. From URL
    candidates.append(_extract_domain_title(url))

    # Find best candidate within range
    for cand in candidates:
        cand = _truncate_title(cand, 60)
        if 30 <= len(cand) <= 60:
            return cand

    # Fallback: pad to minimum length
    best = _truncate_title(candidates[0] if candidates else "Page", 60)
    if len(best) < 30:
        best = best + " | NMG" if len(best) + 6 <= 60 else best

    return _truncate_title(best, 60)


def generate_meta(row: dict) -> str:
    """Generate a fixed meta description (50-155 chars) from row data."""
    existing = (row.get("Meta Description 1") or "").strip()
    h1 = (row.get("H1-1") or "").strip()
    h2 = (row.get("H2-1") or "").strip()
    title = (row.get("Title 1") or "").strip()
    url = row.get("Address", "")

    # Try to build from available text
    if existing and 50 <= len(existing) <= 155:
        candidate = existing
    elif h1 and h2:
        candidate = _truncate_meta(f"{h1}. {h2}", 155)
    elif h1:
        candidate = _truncate_meta(f"{h1}. Learn more about this topic.", 155)
    elif title and len(title) >= 20:
        candidate = _truncate_meta(f"{title} - Visit us for more information.", 155)
    else:
        # Fallback: generic from domain
        domain = urlparse(url).netloc or "our site"
        candidate = _truncate_meta(f"Discover more content on {domain}.", 155)

    # Ensure at least 50 chars
    if len(candidate) < 50:
        candidate = candidate + " " * (50 - len(candidate))

    return _truncate_meta(candidate, 155)


def find_nearest_target(broken_url: str, valid_urls: list[str]) -> str | None:
    """Find the closest valid URL by path similarity."""
    if not valid_urls:
        return None

    try:
        broken_path = urlparse(broken_url).path.lower()
        broken_parts = broken_path.strip("/").split("/")

        best_score = -1
        best_url = valid_urls[0]

        for valid_url in valid_urls:
            valid_path = urlparse(valid_url).path.lower()
            valid_parts = valid_path.strip("/").split("/")

            # Count matching path segments
            matches = sum(1 for b, v in zip(broken_parts, valid_parts) if b == v)
            score = matches

            if score > best_score:
                best_score = score
                best_url = valid_url

        return best_url if best_score > 0 else valid_urls[0]
    except Exception:
        return valid_urls[0] if valid_urls else None


def generate_fixes(rows: list[dict], issues: list[dict], detector=None) -> tuple[list[dict], list[dict]]:
    """Generate title/meta and redirect fixes from detected issues."""
    titles_metas_fixes = []
    redirect_fixes = []

    # Build set of valid (200, indexable, HTML) URLs for redirect targeting
    if detector is None:
        from . import detector
    html = [r for r in rows if detector.is_html(r)]
    valid_urls = [r["Address"] for r in html if detector.is_200(r) and detector.indexable(r)]

    # Index rows by URL for quick lookup
    rows_by_url = {r.get("Address"): r for r in rows}

    # Collect all URLs that need fixes (title or meta issues)
    urls_to_fix = set()
    title_issues = {
        "missing_title", "title_too_long", "title_too_short", "duplicate_title"
    }
    meta_issues = {
        "missing_meta_description", "meta_description_too_long", "duplicate_meta_description"
    }

    for issue in issues:
        if issue["type"] in title_issues or issue["type"] in meta_issues:
            urls_to_fix.update(issue.get("affected_urls", []))

    # Generate fixes for each affected URL (both title and meta in one record)
    for url in sorted(urls_to_fix):
        if url in rows_by_url:
            row = rows_by_url[url]
            old_title = (row.get("Title 1") or "").strip()
            old_meta = (row.get("Meta Description 1") or "").strip()
            new_title = generate_title(row)
            new_meta = generate_meta(row)

            # Add fix if either title or meta changed
            if new_title != old_title or new_meta != old_meta:
                titles_metas_fixes.append({
                    "url": url,
                    "old_title": old_title,
                    "new_title": new_title,
                    "old_meta": old_meta,
                    "new_meta": new_meta
                })

    # Process redirect issues
    redirect_issues = {"broken_link", "server_error"}
    for issue in issues:
        if issue["type"] in redirect_issues:
            for url in issue.get("affected_urls", []):
                target = find_nearest_target(url, valid_urls)
                if target and target != url:
                    redirect_fixes.append({
                        "from": url,
                        "to": target,
                        "reason": f"Broken link ({issue['type']}) → nearest valid page"
                    })

    return titles_metas_fixes, redirect_fixes



def write_csv(filepath: str, data: list[dict], fieldnames: list[str]) -> int:
    """Write list of dicts to CSV file."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    return len(data)


if __name__ == "__main__":
    import sys
    import json
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from seo import detector

    d = sys.argv[1] if len(sys.argv) > 1 else "sample-export"
    rows = detector.load_rows(d)
    issues = detector.detect(rows)

    titles, redirects = generate_fixes(rows, issues, detector)

    out_dir = os.path.join(d, "..", "outputs")
    t_count = write_csv(
        os.path.join(out_dir, "titles_metas.csv"),
        titles,
        ["url", "old_title", "new_title", "old_meta", "new_meta"]
    )
    r_count = write_csv(
        os.path.join(out_dir, "redirect_map.csv"),
        redirects,
        ["from", "to", "reason"]
    )

    print(f"Generated {t_count} title/meta fixes")
    print(f"Generated {r_count} redirect fixes")
