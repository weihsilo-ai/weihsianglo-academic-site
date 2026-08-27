#!/usr/bin/env python3
"""Render all linked homepage data into the static HTML fallback."""

from __future__ import annotations

import argparse
import html
import json
import re
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "index.html"
PROFILE_PATH = ROOT / "data" / "site-profile.json"
PUBLICATIONS_PATH = ROOT / "data" / "publications.json"

BLOCK_NAMES = (
    "about",
    "publication-stats",
    "appointment",
    "featured-paper",
    "latest-updates",
    "experience",
    "publication-tabs",
    "publication-board",
    "education",
    "awards",
    "footer",
)

LAB_ICON = (
    '<svg class="brand-icon brand-icon-lab" viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M7 6.5a2.5 2.5 0 1 1 1.2 2.1l2.4 2.2a3 3 0 0 1 2.8-.2l2.1-3.1a2.4 2.4 0 1 1 1.2.8'
    'l-2.1 3.1a3 3 0 0 1 .6 3.2l2.7 2.1a2.5 2.5 0 1 1-.9 1.1l-2.7-2.1a3 3 0 0 1-4.4-3.8L7.4 9.7'
    'A2.5 2.5 0 0 1 7 6.5Zm0 1.3a1.2 1.2 0 1 0 0-2.4 1.2 1.2 0 0 0 0 2.4Zm6 6.7a1.6 1.6 0 1 0 0-3.2'
    ' 1.6 1.6 0 0 0 0 3.2Zm4.5-7.4a1.1 1.1 0 1 0 0-2.2 1.1 1.1 0 0 0 0 2.2Zm2.3 12.6a1.2 1.2 0 1 0 0-2.4'
    ' 1.2 1.2 0 0 0 0 2.4Z"/>'
    "</svg>"
)
RICH_TOKENS = {
    "{{umich_blue}}": (
        '<span class="brand-mention umich-mention"><span class="brand-icon brand-icon-umich" aria-hidden="true">M</span>'
        '<span class="mark mark-blue">University of Michigan</span></span>'
    ),
    "{{umich_orange}}": (
        '<span class="brand-mention umich-mention"><span class="brand-icon brand-icon-umich" aria-hidden="true">M</span>'
        '<span class="mark mark-orange">University of Michigan</span></span>'
    ),
    "{{ihub_blue}}": (
        '<span class="brand-mention lab-mention">'
        + LAB_ICON
        + '<a class="mark mark-blue" href="https://ihub.engin.umich.edu/">Intelligence &amp; Human Augmentation Lab (iHub)</a></span>'
    ),
    "{{ihub_purple}}": (
        '<span class="brand-mention lab-mention">'
        + LAB_ICON
        + '<a class="mark mark-purple" href="https://ihub.engin.umich.edu/">Intelligence &amp; Human Augmentation Lab</a></span>'
    ),
    "{{ihub_plain}}": (
        '<span class="brand-mention lab-mention">'
        + LAB_ICON
        + "Intelligence &amp; Human Augmentation Lab</span>"
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def expand_rich_html(value: Any) -> str:
    rendered = str(value or "")
    for token, markup in RICH_TOKENS.items():
        rendered = rendered.replace(token, markup)
    unresolved = re.search(r"\{\{[^{}]+\}\}", rendered)
    if unresolved:
        raise ValueError(f"Unknown rich-text token: {unresolved.group(0)}")
    return rendered


def require_profile_sections(profile: dict[str, Any]) -> None:
    required = ("about", "appointment", "latest_updates", "experience", "education", "awards", "footer")
    missing = [name for name in required if name not in profile]
    if missing:
        raise ValueError("Missing profile sections: " + ", ".join(missing))


def validate_markers(document: str) -> None:
    for name in BLOCK_NAMES:
        start = f"<!-- site-data:{name}:start -->"
        end = f"<!-- site-data:{name}:end -->"
        if document.count(start) != 1 or document.count(end) != 1:
            raise ValueError(f"Expected exactly one complete generated block for {name}")
        if document.index(start) > document.index(end):
            raise ValueError(f"Generated block markers are reversed for {name}")


def replace_generated_block(document: str, name: str, body: str) -> str:
    start = f"<!-- site-data:{name}:start -->"
    end = f"<!-- site-data:{name}:end -->"
    pattern = re.compile(
        rf"^(?P<indent>[ \t]*){re.escape(start)}.*?^[ \t]*{re.escape(end)}",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(document)
    if not match:
        raise ValueError(f"Unable to replace generated block {name}")
    indent = match.group("indent")
    replacement = "\n".join(
        (
            indent + start,
            textwrap.indent(body.strip(), indent),
            indent + end,
        )
    )
    return document[: match.start()] + replacement + document[match.end() :]


def render_about(profile: dict[str, Any]) -> str:
    paragraphs = profile["about"].get("paragraphs_html", [])
    if not paragraphs:
        raise ValueError("Profile about section must contain at least one paragraph")
    inner = "\n".join(f"  <p>{expand_rich_html(paragraph)}</p>" for paragraph in paragraphs)
    return f'<div class="prose">\n{inner}\n</div>'


def render_publication_stats(publications: dict[str, Any]) -> str:
    source = publications.get("source") or {}
    publication_count = int(source.get("publications", 0) or 0)
    citation_count = int(source.get("citations", 0) or 0)
    sync_label = source.get("last_successful_sync_label") or publications.get("generated_at_label", "Unknown")
    sync_prefix = "last manual refresh " if source.get("last_successful_sync_mode") == "manual-bibtex-import" else "last successful sync "
    return "\n".join(
        (
            '<article class="dashboard-card stat-card">',
            '  <span class="dashboard-label">Publication Catalog</span>',
            '  <div class="stat-metrics">',
            '    <div class="stat-metric">',
            f'      <strong id="publication-count" data-target="{publication_count}">{publication_count}</strong>',
            "      <span>Publications</span>",
            "    </div>",
            '    <div class="stat-metric">',
            f'      <strong id="citation-count" data-target="{citation_count}">{citation_count}</strong>',
            "      <span>Citations</span>",
            "    </div>",
            "  </div>",
            '  <p class="stat-source" id="scholar-source-line"><a href="'
            + escape(source.get("url"))
            + '">'
            + escape(source.get("label"))
            + "</a> · "
            + escape(sync_prefix + str(sync_label))
            + ".</p>",
            "</article>",
        )
    )


def render_appointment(profile: dict[str, Any]) -> str:
    appointment = profile["appointment"]
    return "\n".join(
        (
            '<article class="dashboard-card appointment-card">',
            '  <span class="dashboard-label">Current Appointment</span>',
            f"  <h3>{escape(appointment.get('title'))}</h3>",
            f"  <p>{expand_rich_html(appointment.get('organization_html'))}</p>",
            f'  <p class="advisor-line">{expand_rich_html(appointment.get("advisor_html"))}</p>',
            "</article>",
        )
    )


def featured_publication(publications: dict[str, Any]) -> dict[str, Any]:
    items = publications.get("publications") or []
    featured_slug = publications.get("featured_slug")
    featured = next((item for item in items if item.get("slug") == featured_slug), None)
    if featured is None and items:
        featured = items[0]
    if featured is None:
        raise ValueError("At least one publication is required to render the featured paper")
    return featured


def render_featured_paper(publications: dict[str, Any]) -> str:
    featured = featured_publication(publications)
    primary_link = next((link for link in featured.get("links", []) if link.get("label") and link.get("href")), None)
    if primary_link:
        link_label = "View Scholar Entry" if primary_link["label"] == "Scholar" else f"Read {primary_link['label']}"
        link_markup = f'<a id="featured-paper-link" href="{escape(primary_link["href"])}">{escape(link_label)}</a>'
    else:
        link_markup = '<a id="featured-paper-link" href="#research">View Publications</a>'
    meta = " · ".join(str(value) for value in (featured.get("venue"), featured.get("year")) if value)
    return "\n".join(
        (
            '<article class="dashboard-card featured-card">',
            '  <span class="dashboard-label">Featured Paper</span>',
            f'  <h3 id="featured-paper-title">{escape(featured.get("title"))}</h3>',
            f'  <p class="paper-compact-meta" id="featured-paper-meta">{escape(meta)}</p>',
            "  " + link_markup,
            "</article>",
        )
    )


def newest_publication(publications: dict[str, Any]) -> dict[str, Any] | None:
    dated = [item for item in publications.get("publications", []) if int(item.get("year", 0) or 0) > 0]
    return max(dated, key=lambda item: int(item.get("year", 0) or 0), default=None)


def render_latest_updates(profile: dict[str, Any], publications: dict[str, Any]) -> str:
    updates: list[dict[str, Any]] = []
    newest = newest_publication(publications)
    if newest:
        venue_suffix = f" published in {newest['venue']}." if newest.get("venue") else " added to Google Scholar."
        updates.append(
            {
                "datetime": str(newest["year"]),
                "label": str(newest["year"]),
                "text": f"“{newest['title']}”{venue_suffix}",
            }
        )
    updates.extend(profile.get("latest_updates", []))
    items = "\n".join(
        f'    <li><time datetime="{escape(item.get("datetime"))}">{escape(item.get("label"))}</time>'
        f'<span>{escape(item.get("text"))}</span></li>'
        for item in updates
    )
    return "\n".join(
        (
            '<article class="dashboard-card news-card">',
            '  <span class="dashboard-label">Latest Updates</span>',
            '  <ul class="mini-news">',
            items,
            "  </ul>",
            "</article>",
        )
    )


def render_experience(profile: dict[str, Any]) -> str:
    articles = []
    for item in profile.get("experience", []):
        articles.append(
            "\n".join(
                (
                    "  <article>",
                    f"    <time>{escape(item.get('period'))}</time>",
                    "    <div>",
                    f"      <h3>{escape(item.get('title'))}</h3>",
                    f"      <p>{expand_rich_html(item.get('description_html'))}</p>",
                    "    </div>",
                    "  </article>",
                )
            )
        )
    return '<div class="timeline">\n' + "\n".join(articles) + "\n</div>"


def render_tags(tags: list[dict[str, Any]] | list[str] | None) -> str:
    rendered = []
    for tag in tags or []:
        if isinstance(tag, str):
            label, tone = tag, ""
        else:
            label, tone = tag.get("label", ""), tag.get("tone", "")
        if label:
            tone_class = f" tag-{escape(tone)}" if tone else ""
            rendered.append(f'<span class="tag{tone_class}">{escape(label)}</span>')
    return "".join(rendered)


def render_links(links: list[dict[str, Any]] | None) -> str:
    return "".join(
        f'<a href="{escape(link.get("href"))}">{escape(link.get("label"))}</a>'
        for link in links or []
        if link.get("label") and link.get("href")
    )


def render_paper_card(publication: dict[str, Any]) -> str:
    has_visual = bool(publication.get("visual"))
    authors = publication.get("authors_html") or escape(publication.get("authors"))
    details = ""
    if publication.get("summary_html"):
        details += f"<p>{publication['summary_html']}</p>"
    links = render_links(publication.get("links"))
    if links:
        details += f'<div class="link-row">{links}</div>'
    meta = ""
    if publication.get("year"):
        meta += f"<span>{escape(publication['year'])}</span>"
    if publication.get("venue"):
        meta += f"<span>{escape(publication['venue'])}</span>"
    meta += render_tags(publication.get("tags"))
    visual = ""
    if has_visual:
        visual = (
            f'<img src="{escape(publication.get("visual"))}" '
            f'alt="{escape(publication.get("visual_alt") or publication.get("title"))}">'
        )
    return "\n".join(
        part
        for part in (
            f'<article class="paper-card {"with-visual" if has_visual else "text-only"}" tabindex="0" aria-expanded="false">',
            '  <div class="paper-copy">',
            f"    <h3>{escape(publication.get('title'))}</h3>",
            f'    <p class="authors">{authors}</p>',
            f'    <div class="meta-line">{meta}</div>',
            f'    <div class="paper-details">{details}</div>',
            "  </div>",
            "  " + visual if visual else "",
            '  <button class="paper-toggle" type="button" aria-label="Expand paper">',
            '    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 9 5 5 5-5H7Z"/></svg>',
            "  </button>",
            "</article>",
        )
        if part
    )


def render_publication_tabs(publications: dict[str, Any]) -> str:
    category_order = ["all", *(publications.get("category_order") or [])]
    labels = publications.get("category_labels") or {}
    counts = publications.get("counts") or {}
    buttons = []
    for index, category in enumerate(category_order):
        active = index == 0
        panel_id = "publication-board" if category == "all" else f"pub-panel-{category}"
        buttons.append(
            f'<button class="catalog-tab{" is-active" if active else ""}" id="pub-tab-{escape(category)}" '
            f'type="button" role="tab" data-pub-tab="{escape(category)}" aria-selected="{str(active).lower()}" '
            f'aria-controls="{escape(panel_id)}"{"" if active else " tabindex=\"-1\""}>'
            f'{escape(labels.get(category, category))} <span class="catalog-count">{escape(counts.get(category, 0))}</span></button>'
        )
    return (
        '<div class="catalog-index" id="publication-catalog-tabs" role="tablist" aria-label="Publication categories">\n  '
        + "\n  ".join(buttons)
        + "\n</div>"
    )


def render_publication_board(publications: dict[str, Any]) -> str:
    sections = []
    labels = publications.get("category_labels") or {}
    for category in publications.get("category_order") or []:
        group_title = labels.get(category, category)
        if category == "journal":
            group_title = "Journal Articles"
        elif category == "conference":
            group_title = "Conference Proceedings"
        cards = [
            render_paper_card(item)
            for item in publications.get("publications", [])
            if item.get("category") == category
        ]
        list_class = "paper-list" if category == "journal" else "paper-list compact"
        card_markup = textwrap.indent("\n".join(cards), "      ")
        sections.append(
            "\n".join(
                (
                    f'  <section class="publication-group" id="pub-panel-{escape(category)}" role="tabpanel" '
                    f'data-pub-panel="{escape(category)}" aria-labelledby="pub-tab-{escape(category)}">',
                    f'    <h3 class="group-title">{escape(group_title)}</h3>',
                    f'    <div class="{list_class}">',
                    card_markup,
                    "    </div>",
                    "  </section>",
                )
            )
        )
    return '<div class="publication-board" id="publication-board">\n' + "\n".join(sections) + "\n</div>"


def render_education(profile: dict[str, Any]) -> str:
    cards = []
    for item in profile.get("education", []):
        cards.append(
            "\n".join(
                (
                    '  <article class="education-card">',
                    f"    <time>{escape(item.get('period'))}</time>",
                    f"    <h3>{escape(item.get('degree'))}</h3>",
                    f"    <p>{expand_rich_html(item.get('details_html'))}</p>",
                    f"    <p>{expand_rich_html(item.get('note_html'))}</p>",
                    "  </article>",
                )
            )
        )
    return '<div class="education-grid">\n' + "\n".join(cards) + "\n</div>"


def render_awards(profile: dict[str, Any]) -> str:
    cards = []
    for item in profile.get("awards", []):
        cards.append(
            "\n".join(
                (
                    '  <article class="award-tile">',
                    f"    <time>{escape(item.get('year'))}</time>",
                    f"    <h3>{escape(item.get('title'))}</h3>",
                    f"    <p>{expand_rich_html(item.get('description_html'))}</p>",
                    "  </article>",
                )
            )
        )
    return '<div class="award-strip">\n' + "\n".join(cards) + "\n</div>"


def render_footer(profile: dict[str, Any], publications: dict[str, Any]) -> str:
    source = publications.get("source") or {}
    checked = source.get("last_successful_sync_label") or publications.get("generated_at_label", "Unknown")
    cv_updated = profile["footer"].get("cv_updated_label", "Unknown")
    return f'<footer class="site-footer">CV updated {escape(cv_updated)} · Site data checked {escape(checked)}</footer>'


def render_document(document: str, profile: dict[str, Any], publications: dict[str, Any]) -> str:
    require_profile_sections(profile)
    validate_markers(document)
    rendered_blocks = {
        "about": render_about(profile),
        "publication-stats": render_publication_stats(publications),
        "appointment": render_appointment(profile),
        "featured-paper": render_featured_paper(publications),
        "latest-updates": render_latest_updates(profile, publications),
        "experience": render_experience(profile),
        "publication-tabs": render_publication_tabs(publications),
        "publication-board": render_publication_board(publications),
        "education": render_education(profile),
        "awards": render_awards(profile),
        "footer": render_footer(profile, publications),
    }
    rendered = document
    for name in BLOCK_NAMES:
        rendered = replace_generated_block(rendered, name, rendered_blocks[name])
    return rendered


def render_site_file(
    *,
    index_path: Path = INDEX_PATH,
    profile_path: Path = PROFILE_PATH,
    publications_path: Path = PUBLICATIONS_PATH,
    check: bool = False,
) -> bool:
    current = index_path.read_text(encoding="utf-8")
    rendered = render_document(current, load_json(profile_path), load_json(publications_path))
    changed = current != rendered
    if check:
        if changed:
            raise RuntimeError(f"{index_path} is out of date; run scripts/site_data_pipeline.py")
        return False
    if changed:
        index_path.write_text(rendered, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if index.html is not synchronized with its data files.")
    args = parser.parse_args()
    try:
        changed = render_site_file(check=args.check)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Site data render failed: {error}")
        return 1
    if args.check:
        print("index.html is synchronized with the site data files.")
    elif changed:
        print(f"Rendered linked site data into {INDEX_PATH}")
    else:
        print("index.html already matches the site data files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
