#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OVERRIDES_PATH = DATA_DIR / "publication-overrides.json"
OUTPUT_PATH = DATA_DIR / "publications.json"

CATEGORY_ORDER = ("journal", "conference", "preprint", "report")
CATEGORY_LABELS = {
    "all": "All",
    "journal": "Journal",
    "conference": "Conference",
    "preprint": "Preprints",
    "report": "Technical Reports",
}
MONTH_LABELS = [
    "Jan.",
    "Feb.",
    "Mar.",
    "Apr.",
    "May",
    "Jun.",
    "Jul.",
    "Aug.",
    "Sep.",
    "Oct.",
    "Nov.",
    "Dec.",
]
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def format_pretty_date(date_value: dt.date) -> str:
    return f"{MONTH_LABELS[date_value.month - 1]} {date_value.day}, {date_value.year}"


def slugify(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("–", "-").replace("—", "-").replace("’", "'").replace("“", '"').replace("”", '"')
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def strip_tags(raw_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip(" ,")
    if any(marker in text for marker in ("â", "Â", "Ã")):
      try:
        text = text.encode("latin-1").decode("utf-8")
      except UnicodeError:
        pass
    return text


def derive_venue(venue_line: str) -> str:
    if not venue_line:
        return ""
    if "·" in venue_line:
        venue_line = venue_line.split("·", 1)[0].strip()
    parts = [part.strip() for part in venue_line.split(",") if part.strip()]
    return parts[0] if parts else venue_line.strip()


def infer_category(title: str, venue_line: str) -> str:
    combined = f"{title} {venue_line}".lower()
    if "arxiv" in combined or "preprint" in combined:
        return "preprint"
    if any(
        marker in combined
        for marker in (
            "proceedings",
            "conference",
            "annual meeting",
            "automotiveui",
            "adjunct",
            "ieee cai",
        )
    ):
        return "conference"
    if any(marker in combined for marker in ("transportation institute", "rosa", "national transportation library", "brief")):
        return "report"
    return "journal"


def normalize_links(raw_links: list[dict[str, Any]] | None, scholar_url: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for link in raw_links or []:
        label = str(link.get("label", "")).strip()
        href = str(link.get("href", "")).strip()
        if label and href:
            links.append({"label": label, "href": href})
    if not links and scholar_url:
        links.append({"label": "Scholar", "href": scholar_url})
    return links


def current_publications_by_slug() -> dict[str, dict[str, Any]]:
    current_payload = load_json(OUTPUT_PATH)
    publications = current_payload.get("publications", [])
    return {str(item.get("slug")): item for item in publications if item.get("slug")}


def fetch_url(url: str) -> str:
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    contexts: list[ssl.SSLContext] = [ssl.create_default_context()]

    try:
        import certifi  # type: ignore
    except ImportError:
        certifi = None

    if certifi is not None:
        contexts.append(ssl.create_default_context(cafile=certifi.where()))

    contexts.append(ssl._create_unverified_context())

    last_error: Exception | None = None
    for context in contexts:
        try:
            with urllib.request.urlopen(request, timeout=30, context=context) as response:
                payload = response.read()
                for encoding in ("utf-8", "latin-1"):
                    try:
                        return payload.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                return payload.decode("utf-8", errors="replace")
        except urllib.error.URLError as error:
            last_error = error

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Unable to fetch {url}")


def fetch_google_scholar_html(user_id: str) -> tuple[str, str]:
    url = f"https://scholar.google.com/citations?user={user_id}&hl=en&view_op=list_works&pagesize=100&sortby=pubdate"
    return fetch_url(url), url


def parse_google_scholar_html(html_text: str) -> tuple[list[dict[str, Any]], int | None]:
    publications: list[dict[str, Any]] = []
    rows = re.findall(r'<tr class="gsc_a_tr">(.*?)</tr>', html_text, re.S)
    for row_html in rows:
        title_match = re.search(r'<a href="([^"]*citation_for_view=[^"]+)" class="gsc_a_at">(.*?)</a>', row_html, re.S)
        if not title_match:
            continue

        entry_href = html.unescape(title_match.group(1))
        title = strip_tags(title_match.group(2))
        gray_lines = re.findall(r'<div class="gs_gray">(.*?)</div>', row_html, re.S)
        authors = strip_tags(gray_lines[0]) if gray_lines else ""
        venue_line = strip_tags(gray_lines[1]) if len(gray_lines) > 1 else ""
        citation_count_match = re.search(r'class="gsc_a_ac[^"]*">(.*?)</a>', row_html, re.S)
        year_match = re.search(r'<span class="gsc_a_h gsc_a_hc gs_ibl">(\d{4})</span>', row_html)
        citation_id_match = re.search(r'citation_for_view=[^:]+:([^"&]+)', entry_href)
        citations_text = strip_tags(citation_count_match.group(1)) if citation_count_match else ""

        publications.append(
            {
                "slug": slugify(title),
                "scholar_id": citation_id_match.group(1) if citation_id_match else slugify(title),
                "title": title,
                "authors": authors,
                "venue_line": venue_line,
                "year": int(year_match.group(1)) if year_match else 0,
                "citations": int(citations_text) if citations_text.isdigit() else 0,
                "scholar_url": f"https://scholar.google.com{entry_href}" if entry_href.startswith("/") else entry_href,
            }
        )

    description_match = re.search(r'<meta name="description" content="([^"]+)"', html_text)
    total_citations = None
    if description_match:
        description = html.unescape(description_match.group(1))
        citations_match = re.search(r"Cited by (\d+)", description)
        if citations_match:
            total_citations = int(citations_match.group(1))

    return publications, total_citations


def parse_bibtex_entries(raw_text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    index = 0
    while True:
        start = raw_text.find("@", index)
        if start < 0:
            break
        brace_start = raw_text.find("{", start)
        if brace_start < 0:
            break

        depth = 0
        end = brace_start
        while end < len(raw_text):
            char = raw_text[end]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    break
            end += 1
        block = raw_text[start : end + 1]
        entries.append(parse_single_bibtex_block(block))
        index = end + 1
    return [entry for entry in entries if entry]


def parse_single_bibtex_block(block: str) -> dict[str, str]:
    header_match = re.match(r"@(\w+)\s*\{\s*([^,]+)\s*,", block, re.S)
    if not header_match:
        return {}
    body = block[header_match.end() :].rstrip("}").strip()
    parsed: dict[str, str] = {"entry_type": header_match.group(1), "entry_key": header_match.group(2)}
    position = 0
    while position < len(body):
        field_match = re.match(r"\s*([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body[position:])
        if not field_match:
            break
        field_name = field_match.group(1).lower()
        position += field_match.end()
        if position >= len(body):
            break

        opener = body[position]
        if opener == "{":
            depth = 0
            start = position + 1
            cursor = position
            while cursor < len(body):
                char = body[cursor]
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        break
                cursor += 1
            value = body[start:cursor]
            position = cursor + 1
        elif opener == '"':
            cursor = position + 1
            escaped = False
            while cursor < len(body):
                char = body[cursor]
                if char == '"' and not escaped:
                    break
                escaped = char == "\\" and not escaped
                cursor += 1
            value = body[position + 1 : cursor]
            position = cursor + 1
        else:
            cursor = position
            while cursor < len(body) and body[cursor] not in ",\n":
                cursor += 1
            value = body[position:cursor]
            position = cursor

        parsed[field_name] = re.sub(r"\s+", " ", value).strip()
        while position < len(body) and body[position] in ", \n\r\t":
            position += 1
    return parsed


def bibtex_to_publications(bibtex_path: Path, scholar_profile_url: str) -> list[dict[str, Any]]:
    current_by_slug = current_publications_by_slug()
    entries = parse_bibtex_entries(bibtex_path.read_text(encoding="utf-8"))
    publications: list[dict[str, Any]] = []
    for entry in entries:
        title = strip_tags(entry.get("title", ""))
        if not title:
            continue
        slug = slugify(title)
        current = current_by_slug.get(slug, {})
        venue_line = (
            entry.get("journal")
            or entry.get("booktitle")
            or entry.get("publisher")
            or entry.get("howpublished")
            or current.get("venue_line", "")
        )
        authors = entry.get("author", "").replace(" and ", ", ")
        links: list[dict[str, str]] = []
        if entry.get("doi"):
            links.append({"label": "DOI", "href": f"https://doi.org/{entry['doi']}"})
        elif entry.get("url"):
            links.append({"label": "Link", "href": entry["url"]})

        publications.append(
            {
                "slug": slug,
                "scholar_id": current.get("scholar_id", slug),
                "title": title,
                "authors": authors,
                "venue_line": venue_line,
                "year": int(re.search(r"\d{4}", entry.get("year", "")).group(0)) if re.search(r"\d{4}", entry.get("year", "")) else int(current.get("year", 0) or 0),
                "citations": int(current.get("citations", 0) or 0),
                "scholar_url": current.get("scholar_url", scholar_profile_url),
                "fallback_links": links,
            }
        )
    return publications


def merge_publications(
    raw_publications: list[dict[str, Any]],
    overrides: dict[str, Any],
    mode: str,
    citations_total: int | None = None,
) -> dict[str, Any]:
    today = dt.datetime.now(dt.timezone.utc)
    current_by_slug = current_publications_by_slug()
    override_items = overrides.get("items", {})
    merged_publications: list[dict[str, Any]] = []

    for publication in raw_publications:
        slug = publication["slug"]
        override = override_items.get(slug, {})
        current = current_by_slug.get(slug, {})
        venue_line = override.get("venue_line") or publication.get("venue_line") or current.get("venue_line", "")
        merged = {
            "slug": slug,
            "scholar_id": publication.get("scholar_id") or current.get("scholar_id") or slug,
            "title": override.get("title") or publication["title"],
            "authors": override.get("authors") or current.get("authors") or publication.get("authors", ""),
            "authors_html": override.get("authors_html") or current.get("authors_html", ""),
            "venue": override.get("venue") or current.get("venue") or derive_venue(venue_line),
            "venue_line": venue_line,
            "year": int(override.get("year") or publication.get("year") or current.get("year") or 0),
            "citations": int(publication.get("citations", current.get("citations", 0)) or 0),
            "category": override.get("category") or current.get("category") or infer_category(publication["title"], venue_line),
            "summary_html": override.get("summary_html") or current.get("summary_html", ""),
            "tags": override.get("tags") or current.get("tags", []),
            "links": normalize_links(
                override.get("links") or publication.get("fallback_links") or current.get("links", []),
                publication.get("scholar_url", current.get("scholar_url", "")),
            ),
            "visual": override.get("visual") or current.get("visual"),
            "visual_alt": override.get("visual_alt") or current.get("visual_alt") or f"Visual preview for {publication['title'].lower()}",
            "featured": bool(override.get("featured") or current.get("featured")),
            "sort_priority": int(override.get("sort_priority", current.get("sort_priority", 999))),
            "scholar_url": publication.get("scholar_url", current.get("scholar_url", "")),
            "source_title": publication["title"],
            "source_authors": publication.get("authors", ""),
            "source_venue_line": publication.get("venue_line", ""),
        }
        merged_publications.append(merged)

    merged_publications.sort(
        key=lambda item: (
            CATEGORY_ORDER.index(item["category"]) if item["category"] in CATEGORY_ORDER else len(CATEGORY_ORDER),
            item["sort_priority"],
            -int(item.get("year", 0) or 0),
            -int(item.get("citations", 0) or 0),
            item["title"].lower(),
        )
    )

    counts = {"all": len(merged_publications)}
    for category in CATEGORY_ORDER:
        counts[category] = sum(1 for item in merged_publications if item["category"] == category)

    featured_slug = overrides.get("featured_slug") or next(
        (item["slug"] for item in merged_publications if item.get("featured")),
        merged_publications[0]["slug"] if merged_publications else "",
    )

    preserved_citations_total = citations_total
    if preserved_citations_total is None:
        preserved_citations_total = load_json(OUTPUT_PATH).get("source", {}).get("citations", 0)

    return {
        "generated_at": today.isoformat(),
        "generated_at_label": format_pretty_date(today.date()),
        "source": {
            "mode": mode,
            "label": "Google Scholar indexed works",
            "url": overrides.get("scholar_profile_url", ""),
            "citations": int(preserved_citations_total or 0),
            "publications": len(merged_publications),
        },
        "counts": counts,
        "category_order": list(CATEGORY_ORDER),
        "category_labels": CATEGORY_LABELS,
        "featured_slug": featured_slug,
        "publications": merged_publications,
    }


def run_sync_scholar() -> None:
    overrides = load_json(OVERRIDES_PATH)
    user_id = overrides.get("scholar_user_id")
    if not user_id:
        raise SystemExit(f"Missing scholar_user_id in {OVERRIDES_PATH}")

    try:
        html_text, _ = fetch_google_scholar_html(user_id)
    except urllib.error.URLError as error:
        raise SystemExit(f"Unable to fetch Google Scholar profile: {error}") from error

    publications, citations_total = parse_google_scholar_html(html_text)
    if len(publications) < 5:
        raise SystemExit(f"Scholar sync returned only {len(publications)} publications; aborting to avoid wiping current data.")

    payload = merge_publications(publications, overrides, mode="scholar-sync", citations_total=citations_total)
    save_json(OUTPUT_PATH, payload)
    print(f"Wrote {len(payload['publications'])} publications to {OUTPUT_PATH}")


def run_import_bibtex(path_arg: str) -> None:
    overrides = load_json(OVERRIDES_PATH)
    bibtex_path = Path(path_arg).expanduser().resolve()
    if not bibtex_path.exists():
        raise SystemExit(f"BibTeX file not found: {bibtex_path}")

    publications = bibtex_to_publications(bibtex_path, overrides.get("scholar_profile_url", ""))
    if not publications:
        raise SystemExit(f"No BibTeX entries were imported from {bibtex_path}")

    payload = merge_publications(publications, overrides, mode="manual-bibtex-import")
    save_json(OUTPUT_PATH, payload)
    print(f"Imported {len(payload['publications'])} publications from {bibtex_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build publications.json from Google Scholar or a manual BibTeX export.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("sync-scholar", help="Fetch the public Google Scholar profile and rebuild data/publications.json.")

    import_bibtex = subparsers.add_parser(
        "import-bibtex",
        help="Use a manual Google Scholar BibTeX export as a fallback source and rebuild data/publications.json.",
    )
    import_bibtex.add_argument("path", help="Path to the exported .bib file.")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "sync-scholar":
        run_sync_scholar()
    elif args.command == "import-bibtex":
        run_import_bibtex(args.path)
    else:
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
