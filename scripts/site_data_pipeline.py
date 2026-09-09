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
    "presentations",
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
SJSU_ICON = '<img class="brand-icon brand-icon-sjsu" src="assets/sjsu-spirit-mark-32.png" alt="" aria-hidden="true">'
CAR_ICON = (
    '<svg class="brand-icon brand-icon-car" viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M4 16v-4l2-1 2-4h8l3 4h1v5H4Z"/><circle cx="7" cy="16" r="2"/><circle cx="17" cy="16" r="2"/>'
    "</svg>"
)
RESEARCH_INTEREST_ICONS = (
    '<svg class="brand-icon interest-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="7" r="3"/><path d="M5.5 20c.5-4 2.7-6 6.5-6s6 2 6.5 6"/></svg>',
    '<svg class="brand-icon interest-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.5"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3"/></svg>',
    '<svg class="brand-icon interest-icon" viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="12" cy="5.5" rx="7" ry="3"/><path d="M5 5.5v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6M5 11.5v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/></svg>',
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
    "{{sjsu_plain}}": (
        '<span class="brand-mention academic-mention">'
        + SJSU_ICON
        + '<span class="mark mark-blue">San José State University</span></span>'
    ),
    "{{batlab_blue}}": (
        '<span class="brand-mention lab-mention batlab-mention">'
        + CAR_ICON
        + '<a class="mark mark-blue" href="https://batlab.info/">Behavior, Accessibility, and Technology Lab (BAT Lab)</a></span>'
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def date_sort_key(value: Any) -> tuple[int, int]:
    text = str(value or "")
    years = [int(match) for match in re.findall(r"\d{2,4}", text)]
    if len(years) > 1 and years[1] < 100:
        years[1] = (years[0] // 100) * 100 + years[1]
    start_year = years[0] if years else 0
    end_year = 9999 if "present" in text.lower() else (years[-1] if years else 0)
    return end_year, start_year


def newest_first(items: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: tuple(-part for part in date_sort_key(item.get(field))))


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
    required = (
        "about",
        "appointment",
        "latest_updates",
        "experience",
        "teaching_experience",
        "presentations",
        "education",
        "awards",
        "footer",
    )
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
    about = profile["about"]
    paragraphs = about.get("paragraphs_html", [])
    if not paragraphs:
        raise ValueError("Profile about section must contain at least one paragraph")
    research_interests = about.get("research_interests_html", [])
    card_class = "prose about-card has-research-interests" if research_interests else "prose about-card"
    lines = ['  <div class="about-summary">']
    lines.extend(f"    <p>{expand_rich_html(paragraph)}</p>" for paragraph in paragraphs)
    education = about.get("education_html")
    if education:
        lines.append(f'    <p class="about-education">{expand_rich_html(education)}</p>')
    lines.append("  </div>")
    if research_interests:
        lines.append('  <div class="about-research">')
        lines.append('    <p class="research-interests-label">Research interests</p>')
        lines.append('    <ul class="research-interests">')
        for index, item in enumerate(research_interests):
            icon = RESEARCH_INTEREST_ICONS[index % len(RESEARCH_INTEREST_ICONS)]
            lines.append(f'      <li>{icon}<span class="interest-copy">{expand_rich_html(item)}</span></li>')
        lines.append("    </ul>")
        lines.append("  </div>")
    return f'<div class="{card_class}">\n' + "\n".join(lines) + "\n</div>"


def render_publication_stats(publications: dict[str, Any]) -> str:
    source = publications.get("source") or {}
    metrics = source.get("metrics") or {}
    citations = metrics.get("citations") or {}
    h_index = metrics.get("h_index") or {}
    i10_index = metrics.get("i10_index") or {}
    yearly = metrics.get("citations_per_year") or []
    updated_label = source.get("last_successful_sync_label") or publications.get("generated_at_label", "Unknown")
    yearly_max = max((int(item.get("citations", 0) or 0) for item in yearly), default=0)
    axis_max = max(5, ((yearly_max + 4) // 5) * 5)
    bars = []
    for item in yearly:
        year = int(item.get("year", 0) or 0)
        count = int(item.get("citations", 0) or 0)
        height = round((count / axis_max) * 100, 2) if axis_max else 0
        height_label = f"{height:g}"
        bars.append(
            '<div class="scholar-year" role="listitem" '
            f'data-year="{year}" data-citations="{count}" tabindex="0" '
            f'aria-label="{year}: {count} citations" style="--bar-height: {height_label}%">'
            '<span class="scholar-bar" aria-hidden="true"></span>'
            f'<span class="scholar-year-label">{year}</span></div>'
        )
    return "\n".join(
        (
            '<section class="scholar-card" aria-labelledby="scholar-card-title">',
            '  <h2 id="scholar-card-title"><a id="scholar-profile-link" href="'
            + escape(source.get("url"))
            + '">Cited by</a></h2>',
            '  <table class="scholar-metrics">',
            "    <thead><tr><th></th><th>All</th><th id=\"scholar-since-label\">"
            + escape(metrics.get("since_label", "Since recent"))
            + "</th></tr></thead>",
            "    <tbody>",
            "      <tr><th>Citations</th>"
            f'<td id="scholar-citations-all">{int(citations.get("all", source.get("citations", 0)) or 0)}</td>'
            f'<td id="scholar-citations-since">{int(citations.get("since", source.get("citations", 0)) or 0)}</td></tr>',
            "      <tr><th>h-index</th>"
            f'<td id="scholar-h-index-all">{int(h_index.get("all", 0) or 0)}</td>'
            f'<td id="scholar-h-index-since">{int(h_index.get("since", 0) or 0)}</td></tr>',
            "      <tr><th>i10-index</th>"
            f'<td id="scholar-i10-index-all">{int(i10_index.get("all", 0) or 0)}</td>'
            f'<td id="scholar-i10-index-since">{int(i10_index.get("since", 0) or 0)}</td></tr>',
            "    </tbody>",
            "  </table>",
            f'  <div class="scholar-chart" style="--axis-max: {axis_max}" aria-label="Citations per year">',
            '    <div class="scholar-axis" aria-hidden="true">'
            f'<span>{axis_max}</span><span>{axis_max // 2}</span><span>0</span></div>',
            '    <div class="scholar-bars" id="scholar-year-bars" role="list">' + "".join(bars) + "</div>",
            "  </div>",
            '  <p class="scholar-source-line">Source: <a id="scholar-source-link" href="'
            + escape(source.get("url"))
            + '">Google Scholar</a> · Updated <time id="scholar-updated-label">'
            + escape(updated_label)
            + "</time></p>",
            "</section>",
        )
    )


def render_appointment(profile: dict[str, Any]) -> str:
    return ""


def featured_publications(publications: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    items = publications.get("publications") or []
    requested_slugs = publications.get("featured_slugs") or [publications.get("featured_slug")]
    items_by_slug = {item.get("slug"): item for item in items}
    featured: list[dict[str, Any]] = []
    for slug in requested_slugs:
        item = items_by_slug.get(slug)
        if item and item not in featured:
            featured.append(item)
    for item in items:
        if len(featured) >= limit:
            break
        if item not in featured:
            featured.append(item)
    if not featured:
        raise ValueError("At least one publication is required to render the featured paper")
    return newest_first(featured[:limit], "year")


def render_featured_links(publication: dict[str, Any]) -> str:
    links = publication.get("links", [])
    doi_link = next(
        (link for link in links if str(link.get("label", "")).lower() == "doi" and link.get("href")),
        None,
    )
    rendered: list[str] = []
    if doi_link:
        rendered.append(f'<a href="{escape(doi_link["href"])}">DOI</a>')
    if not rendered:
        rendered.append('<a href="#research">View Publications</a>')
    return '<div class="featured-links">' + "".join(rendered) + "</div>"


def render_featured_authors(publication: dict[str, Any]) -> str:
    return escape(publication.get("authors")).replace("WH Lo", "<strong>WH Lo</strong>")


def render_featured_paper(publications: dict[str, Any]) -> str:
    cards: list[str] = []
    for publication in featured_publications(publications):
        category = publication.get("category")
        category_publications = newest_first(
            [item for item in publications.get("publications", []) if item.get("category") == category],
            "year",
        )
        category_prefixes = {"journal": "J", "conference": "C", "preprint": "P", "report": "T"}
        label = f"[{category_prefixes.get(category, str(category)[:1].upper())}{category_publications.index(publication) + 1}]"
        meta = publication.get("venue_line") or " · ".join(
            str(value) for value in (publication.get("venue"), publication.get("year")) if value
        )
        scholar_url = publication.get("scholar_url") or "#research"
        authors = render_featured_authors(publication)
        cards.append(
            "\n".join(
                (
                    f'<article class="dashboard-card featured-card record-card" role="listitem" data-featured-slug="{escape(publication.get("slug"))}">',
                    f'  <h3><span class="publication-label">{escape(label)}</span><a class="featured-title-link" href="{escape(scholar_url)}">{escape(publication.get("title"))}</a></h3>',
                    f'  <p class="featured-authors">{authors}</p>',
                    '  <div class="featured-meta-row">',
                    f'    <p class="paper-compact-meta">{escape(meta)}</p>',
                    "    " + render_featured_links(publication),
                    "  </div>",
                    "</article>",
                )
            )
        )
    return "\n".join(
        (
            '<section class="featured-papers-section" aria-labelledby="featured-papers-heading">',
            '  <h3 class="featured-section-title" id="featured-papers-heading">Featured Paper</h3>',
            '  <div class="featured-papers-grid" id="featured-papers-grid" role="list">',
            "\n".join(cards),
            "  </div>",
            "</section>",
        )
    )


def render_latest_updates(profile: dict[str, Any], publications: dict[str, Any]) -> str:
    return ""


def render_experience(profile: dict[str, Any]) -> str:
    research_articles = []
    for item in newest_first(profile.get("experience", []), "period"):
        research_articles.append(
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
    teaching_articles = []
    for item in newest_first(profile.get("teaching_experience", []), "period"):
        institution = ", ".join(
            value for value in (item.get("institution"), item.get("location")) if value
        )
        teaching_articles.append(
            "\n".join(
                (
                    "  <article>",
                    f"    <time>{escape(item.get('period'))}</time>",
                    "    <div>",
                    f"      <h3>{escape(item.get('role'))} · {escape(item.get('course'))}</h3>",
                    f"      <p><strong>{escape(institution)}</strong> · Lecturer: {escape(item.get('lecturer'))}</p>",
                    "    </div>",
                    "  </article>",
                )
            )
        )
    service_articles = []
    for item in newest_first(profile.get("service", []), "period"):
        service_articles.append(
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
    return "\n".join(
        (
            '<div class="experience-sections">',
            '  <section class="experience-group">',
            '    <div class="presentation-group-heading"><h3>Research Experience</h3></div>',
            '    <div class="timeline">',
            textwrap.indent("\n".join(research_articles), "    "),
            "    </div>",
            "  </section>",
            '  <section class="experience-group">',
            '    <div class="presentation-group-heading"><h3>Teaching Experience</h3></div>',
            '    <div class="timeline">',
            textwrap.indent("\n".join(teaching_articles), "    "),
            "    </div>",
            "  </section>",
            '  <section class="experience-group">',
            '    <div class="presentation-group-heading"><h3>Service</h3></div>',
            '    <div class="timeline">',
            textwrap.indent("\n".join(service_articles), "    "),
            "    </div>",
            "  </section>",
            "</div>",
        )
    )


def render_presentations(profile: dict[str, Any]) -> str:
    groups = []
    for group in profile.get("presentations", []):
        cards = []
        for item in newest_first(group.get("items", []), "year"):
            item_link = item.get("link") or item.get("doi")
            item_link_label = item.get("link_label") or ("DOI" if item.get("doi") else "Link")
            note = item.get("note")
            cards.append(
                "\n".join(
                    part
                    for part in (
                        '<article class="presentation-card record-card">',
                        f'  <div class="presentation-year">{escape(item.get("year"))}</div>',
                        '  <div class="presentation-copy">',
                        f'    <p class="presentation-authors">{expand_rich_html(item.get("authors_html"))}</p>',
                        f'    <h3>{escape(item.get("title"))}</h3>',
                        '    <div class="presentation-meta-row">',
                        f'      <p class="presentation-venue">{escape(item.get("venue"))}</p>',
                        f'      <a class="presentation-doi" href="{escape(item_link)}">{escape(item_link_label)}</a>' if item_link else "",
                        "    </div>",
                        f'    <span class="presentation-note">{escape(note)}</span>' if note else "",
                        "  </div>",
                        "</article>",
                    )
                    if part
                )
            )
        groups.append(
            "\n".join(
                (
                    '<section class="presentation-group">',
                    f'  <div class="presentation-group-heading"><h3>{escape(group.get("type"))}</h3><span>{escape(group.get("period"))}</span></div>',
                    '  <div class="presentation-list">',
                    textwrap.indent("\n".join(cards), "    "),
                    "  </div>",
                    "</section>",
                )
            )
        )
    return '<div class="presentation-groups">\n' + "\n".join(groups) + "\n</div>"


def render_links(links: list[dict[str, Any]] | None) -> str:
    return "".join(
        f'<a href="{escape(link.get("href"))}">{escape(link.get("label"))}</a>'
        for link in links or []
        if link.get("label") and link.get("href")
    )


def render_paper_card(publication: dict[str, Any], publication_label: str) -> str:
    has_visual = bool(publication.get("visual"))
    authors = publication.get("authors_html") or escape(publication.get("authors"))
    details = ""
    if publication.get("summary_html"):
        details += f"<p>{publication['summary_html']}</p>"
    visible_links = [
        link
        for link in publication.get("links", [])
        if str(link.get("label", "")).lower() != "cv"
        and (
            publication.get("category") != "journal"
            or str(link.get("label", "")).lower() == "doi"
        )
    ]
    actions = render_links(visible_links)
    meta = ""
    if publication.get("year"):
        meta += f"<span>{escape(publication['year'])}</span>"
    if publication.get("venue"):
        meta += f'<strong class="publication-venue">{escape(publication["venue"])}</strong>'
    if publication.get("citation_details"):
        meta += f'<span class="publication-detail">{escape(publication["citation_details"])}</span>'
    if actions:
        meta += f'<div class="paper-actions">{actions}</div>'
    visual = ""
    if has_visual:
        visual = (
            f'<img src="{escape(publication.get("visual"))}" '
            f'alt="{escape(publication.get("visual_alt") or publication.get("title"))}">'
        )
    return "\n".join(
        part
        for part in (
            f'<article class="paper-card record-card {"with-visual" if has_visual else "text-only"}" tabindex="0" aria-expanded="false" data-publication-label="{escape(publication_label)}">',
            '  <div class="paper-copy">',
            f'    <h3><span class="publication-label">{escape(publication_label)}</span><span>{escape(publication.get("title"))}</span></h3>',
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
    category_prefixes = {"journal": "J", "conference": "C", "preprint": "P", "report": "T"}
    for category in publications.get("category_order") or []:
        group_title = labels.get(category, category)
        if category == "journal":
            group_title = "Journal Articles"
        elif category == "conference":
            group_title = "Conference Proceedings"
        category_publications = [
            item for item in publications.get("publications", []) if item.get("category") == category
        ]
        prefix = category_prefixes.get(category, category[:1].upper())
        cards = [
            render_paper_card(item, f"[{prefix}{index}]")
            for index, item in enumerate(newest_first(category_publications, "year"), start=1)
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


def render_awards(profile: dict[str, Any]) -> str:
    cards = []
    for item in newest_first(profile.get("awards", []), "year"):
        description = item.get("description_html")
        cards.append(
            "\n".join(
                part
                for part in (
                    '  <article class="award-tile record-card">',
                    f"    <time>{escape(item.get('year'))}</time>",
                    f"    <h3>{escape(item.get('title'))}</h3>",
                    f"    <p>{expand_rich_html(description)}</p>" if description else "",
                    "  </article>",
                )
                if part
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
        "presentations": render_presentations(profile),
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
