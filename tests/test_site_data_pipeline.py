import importlib.util
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "site_data_pipeline.py"
SPEC = importlib.util.spec_from_file_location("site_data_pipeline", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        self.ids.extend(value for name, value in attrs if name == "id")


class SiteDataPipelineTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "about": {
                "paragraphs_html": ["About {{umich_blue}}"],
                "research_interests_html": [
                    "<span class=\"mark mark-gold\">Human behavior modeling</span>",
                    "Quantitative models",
                ],
                "education_html": "Graduate education",
            },
            "appointment": {
                "title": "Researcher",
                "organization_html": "{{ihub_purple}}",
                "advisor_html": "Advisor",
            },
            "latest_updates": [{"datetime": "2025", "label": "2025", "text": "Curated update"}],
            "experience": [{"period": "2026-Present", "title": "Role", "description_html": "Work"}],
            "teaching_experience": [
                {
                    "period": "Winter 2026",
                    "institution": "University of Michigan",
                    "location": "Ann Arbor, MI",
                    "role": "[GSI] Graduate Student Instructor",
                    "course": "IOE - 333 Human Factors Ergo",
                    "lecturer": "Manhua Wang, Ph.D.",
                }
            ],
            "presentations": [
                {
                    "type": "Lecture",
                    "period": "2024-Present",
                    "items": [
                        {
                            "authors": "A. Author (presenter)",
                            "year": "2025",
                            "title": "Presentation Title",
                            "venue": "Conference Name",
                            "doi": "https://doi.org/presentation",
                        }
                    ],
                }
            ],
            "education": [
                {"period": "2026", "degree": "Degree", "details_html": "School", "note_html": "Note"}
            ],
            "awards": [{"year": "2026", "title": "Award", "description_html": "Description"}],
            "footer": {"cv_updated_label": "August 2026"},
        }
        self.publications = {
            "generated_at_label": "Aug. 27, 2026",
            "source": {
                "label": "Google Scholar indexed works",
                "url": "https://scholar.example/profile",
                "publications": 2,
                "citations": 55,
                "metrics": {
                    "since_label": "Since 2021",
                    "citations": {"all": 55, "since": 55},
                    "h_index": {"all": 5, "since": 5},
                    "i10_index": {"all": 1, "since": 1},
                    "citations_per_year": [
                        {"year": 2023, "citations": 0},
                        {"year": 2024, "citations": 2},
                        {"year": 2025, "citations": 26},
                        {"year": 2026, "citations": 27},
                    ],
                },
                "last_successful_sync_label": "Aug. 27, 2026",
                "last_successful_sync_mode": "scholar-sync",
            },
            "counts": {"all": 3, "journal": 3},
            "category_order": ["journal"],
            "category_labels": {"all": "All", "journal": "Journal"},
            "featured_slug": "older-paper",
            "featured_slugs": ["older-paper", "new-paper", "third-paper"],
            "publications": [
                {
                    "slug": "older-paper",
                    "title": "Older Paper",
                    "authors": "WH Lo, A. Author",
                    "venue": "Journal A",
                    "year": 2025,
                    "category": "journal",
                    "summary_html": "Expandable summary",
                    "links": [
                        {"label": "DOI", "href": "https://doi.org/older"},
                        {"label": "CV", "href": "Wei-Hsiang-Lo-CV.pdf"},
                    ],
                    "tags": [],
                },
                {
                    "slug": "new-paper",
                    "title": "New Paper",
                    "authors": "A. Author",
                    "venue": "Journal B",
                    "year": 2026,
                    "category": "journal",
                    "links": [{"label": "Scholar", "href": "https://scholar.example/new"}],
                    "tags": [],
                },
                {
                    "slug": "third-paper",
                    "title": "Third Paper",
                    "authors": "B. Author",
                    "venue": "Journal C",
                    "year": 2024,
                    "category": "journal",
                    "scholar_url": "https://scholar.example/third",
                    "links": [{"label": "DOI", "href": "https://doi.org/third"}],
                    "tags": [],
                },
            ],
        }

    def template(self):
        return "\n".join(
            f"  <!-- site-data:{name}:start -->\n  stale\n  <!-- site-data:{name}:end -->"
            for name in MODULE.BLOCK_NAMES
        ) + "\n"

    def test_render_links_profile_and_publication_data(self):
        rendered = MODULE.render_document(self.template(), self.profile, self.publications)

        self.assertIn('class="scholar-card"', rendered)
        self.assertIn('<p class="research-interests-label">Research interests</p>', rendered)
        self.assertIn('<div class="prose about-card has-research-interests">', rendered)
        self.assertIn('<div class="about-summary">', rendered)
        self.assertIn('<div class="about-research">', rendered)
        self.assertIn('<ul class="research-interests">', rendered)
        self.assertEqual(rendered.count("<li>"), 2)
        self.assertIn('<p class="about-education">Graduate education</p>', rendered)
        self.assertLess(
            rendered.index('<p class="about-education">Graduate education</p>'),
            rendered.index('<p class="research-interests-label">Research interests</p>'),
        )
        self.assertIn('id="scholar-citations-all">55</td>', rendered)
        self.assertIn('id="scholar-h-index-all">5</td>', rendered)
        self.assertIn('data-year="2026" data-citations="27"', rendered)
        self.assertIn('data-year="2023" data-citations="0" tabindex="0"', rendered)
        self.assertIn('style="--bar-height: 0%"', rendered)
        self.assertIn('id="scholar-source-link" href="https://scholar.example/profile">Google Scholar</a>', rendered)
        self.assertIn('id="scholar-updated-label">Aug. 27, 2026</time>', rendered)
        self.assertNotIn("Publication Catalog", rendered)
        self.assertNotIn("Current Appointment", rendered)
        self.assertEqual(rendered.count('class="dashboard-card featured-card record-card"'), 3)
        self.assertIn('class="featured-papers-section"', rendered)
        self.assertIn('id="featured-papers-grid" role="list"', rendered)
        featured_section = rendered.split('class="featured-papers-section"', 1)[1].split("</section>", 1)[0]
        self.assertEqual(featured_section.count('role="listitem"'), 3)
        self.assertEqual(featured_section.count('class="featured-meta-row"'), 3)
        self.assertNotIn("View Scholar", featured_section)
        self.assertEqual(featured_section.count(">View Publications</a>"), 1)
        self.assertEqual(
            re.findall(r'<span class="publication-label">(\[[A-Z]\d+\])</span>', featured_section),
            ["[J1]", "[J2]", "[J3]"],
        )
        self.assertIn('<p class="featured-authors"><strong>WH Lo</strong>, A. Author</p>', featured_section)
        self.assertEqual(rendered.count('class="featured-section-title"'), 1)
        self.assertEqual(rendered.count(">Featured Paper</h3>"), 1)
        self.assertIn("Older Paper", rendered)
        self.assertIn("New Paper", rendered)
        self.assertIn("Third Paper", rendered)
        self.assertNotIn("Latest Updates", rendered)
        self.assertNotIn("Curated update", rendered)
        self.assertIn("Teaching Experience", rendered)
        self.assertIn('<div class="presentation-group-heading"><h3>Research Experience</h3></div>', rendered)
        self.assertIn('<div class="presentation-group-heading"><h3>Teaching Experience</h3></div>', rendered)
        self.assertNotIn("subsection-title", rendered)
        self.assertIn("IOE - 333 Human Factors Ergo", rendered)
        self.assertIn('class="presentation-card record-card"', rendered)
        self.assertIn('class="award-tile record-card"', rendered)
        self.assertIn('class="paper-card record-card', rendered)
        self.assertIn("Presentation Title", rendered)
        self.assertIn('<span class="publication-label">[J1]</span>', rendered)
        self.assertIn('<strong class="publication-venue">Journal A</strong>', rendered)
        older_card = rendered[rendered.index('data-publication-label="[J1]"') :]
        self.assertNotIn('class="tag', rendered)
        self.assertLess(older_card.index('class="publication-venue"'), older_card.index('class="paper-actions"'))
        self.assertLess(older_card.index('class="paper-actions"'), older_card.index('class="paper-details"'))
        self.assertIn('href="https://doi.org/older">DOI</a>', older_card)
        self.assertNotIn('href="Wei-Hsiang-Lo-CV.pdf">CV</a>', older_card)
        self.assertIn('<div class="paper-details"><p>Expandable summary</p></div>', older_card)
        new_card = rendered[
            rendered.index('data-publication-label="[J2]"') : rendered.index('data-publication-label="[J3]"')
        ]
        self.assertNotIn('class="paper-actions"', new_card)
        self.assertIn("CV updated August 2026 · Site data checked Aug. 27, 2026", rendered)

    def test_render_is_idempotent(self):
        once = MODULE.render_document(self.template(), self.profile, self.publications)
        twice = MODULE.render_document(once, self.profile, self.publications)

        self.assertEqual(once, twice)

    def test_about_card_without_research_interests_stays_single_column(self):
        rendered = MODULE.render_about({"about": {"paragraphs_html": ["About"]}})

        self.assertIn('<div class="prose about-card">', rendered)
        self.assertIn('<div class="about-summary">', rendered)
        self.assertNotIn("has-research-interests", rendered)
        self.assertNotIn('<div class="about-research">', rendered)

    def test_about_card_renders_semantic_inline_icons(self):
        rendered = MODULE.render_about(
            {
                "about": {
                    "paragraphs_html": ["About"],
                    "education_html": "From {{sjsu_plain}} and {{batlab_blue}}.",
                    "research_interests_html": ["Behavior", "Perception", "Models"],
                }
            }
        )

        self.assertIn("brand-icon-sjsu", rendered)
        self.assertIn("sjsu-spirit-mark-32.png", rendered)
        self.assertIn('<span class="mark mark-blue">San José State University</span>', rendered)
        self.assertIn("batlab-mention", rendered)
        self.assertIn("brand-icon-car", rendered)
        self.assertEqual(rendered.count('class="brand-icon interest-icon"'), 3)
        self.assertEqual(rendered.count('class="interest-copy"'), 3)

    def test_missing_marker_fails_without_partial_output(self):
        broken = self.template().replace("<!-- site-data:awards:end -->", "")

        with self.assertRaisesRegex(ValueError, "awards"):
            MODULE.render_document(broken, self.profile, self.publications)

    def test_production_index_is_current_and_has_unique_ids(self):
        root = Path(__file__).resolve().parents[1]
        document = (root / "index.html").read_text(encoding="utf-8")
        profile = json.loads((root / "data" / "site-profile.json").read_text(encoding="utf-8"))
        publications = json.loads((root / "data" / "publications.json").read_text(encoding="utf-8"))
        collector = IdCollector()
        collector.feed(document)
        client_script = (root / "script.js").read_text(encoding="utf-8")
        style_sheet = (root / "styles.css").read_text(encoding="utf-8")

        self.assertEqual(document, MODULE.render_document(document, profile, publications))
        self.assertEqual(len(collector.ids), len(set(collector.ids)))
        self.assertNotIn('dashboard-label">Featured Paper', client_script)
        self.assertNotIn("renderTags", client_script)
        self.assertNotIn("View Scholar", client_script)
        self.assertNotIn("Read DOI", client_script)
        self.assertNotIn("Read DOI", document)
        self.assertIn('role="listitem"', client_script)
        self.assertIn('paper-card record-card', client_script)
        self.assertIn("publicationLabel(publication.category", client_script)
        self.assertEqual(document.count("data-theme-toggle"), 2)
        self.assertIn('aria-label="Turn on lights"', document)
        self.assertIn('<html lang="en" data-theme="light">', document)
        self.assertIn('localStorage.getItem("site-theme") === "dark"', document)
        self.assertIn('<link rel="stylesheet" href="styles.css?v=20260908-doi-hover">', document)
        self.assertIn('<script src="script.js?v=20260908-about-card"></script>', document)
        self.assertIn("<dt>Role</dt>", document)
        self.assertIn("<dd>Ph.D. student</dd>", document)
        self.assertNotIn("<dt>Base</dt>", document)
        self.assertRegex(style_sheet, r"\.contact-list dd a\s*\{[^}]*text-decoration:\s*underline;[^}]*text-underline-offset:\s*3px;")
        self.assertIn('href="https://ioe.engin.umich.edu/people/manhua-wang/">Dr. Manhua Wang</a>', document)
        self.assertIn('href="https://www.sjsu.edu/people/gaojian.huang/">Dr. Gaojian Huang</a>', document)
        self.assertIn('html[data-theme="light"]', style_sheet)
        self.assertIn("--type-page-title: 32px;", style_sheet)
        self.assertIn("--type-section-title: 20px;", style_sheet)
        self.assertIn("--type-record-title: 18px;", style_sheet)
        self.assertIn("--type-intro: 17px;", style_sheet)
        self.assertIn("--type-body: 15px;", style_sheet)
        self.assertIn("--type-meta: 13px;", style_sheet)
        self.assertIn("--type-label: 12px;", style_sheet)
        self.assertRegex(style_sheet, r"\.record-card\s*\{[^}]*border:\s*0;[^}]*border-bottom:\s*1px solid var\(--border\);")
        self.assertRegex(style_sheet, r"\.section-head h2\s*\{[^}]*font-family:\s*var\(--font\);[^}]*font-size:\s*var\(--type-page-title\);[^}]*font-weight:\s*700;")
        self.assertRegex(style_sheet, r"\.timeline time\s*\{[^}]*font-size:\s*var\(--type-label\);")
        self.assertRegex(style_sheet, r"\.group-title,\s*\.presentation-group-heading h3\s*\{[^}]*font-family:\s*var\(--font\);[^}]*font-size:\s*14px;[^}]*font-weight:\s*800;[^}]*text-transform:\s*uppercase;")
        self.assertNotIn(".group-title::before", style_sheet)
        self.assertRegex(style_sheet, r"\.timeline h3,[^}]*\.featured-card h3\s*\{[^}]*font-size:\s*var\(--type-record-title\);[^}]*font-weight:\s*700;")
        self.assertIn("#about .prose a.mark", style_sheet)
        self.assertRegex(style_sheet, r"#about \.prose a\.mark\s*\{[^}]*text-decoration:\s*underline;[^}]*text-underline-offset:\s*3px;")
        self.assertIn("#about .research-interests", style_sheet)
        self.assertRegex(style_sheet, r"#about \.research-interests-label\s*\{[^}]*font-size:\s*14px;[^}]*text-transform:\s*uppercase;")
        self.assertRegex(style_sheet, r"#about \.research-interests\s*\{[^}]*font-size:\s*var\(--type-intro\);")
        self.assertIn(".about-card", style_sheet)
        self.assertRegex(style_sheet, r"\.about-card\s*\{[^}]*box-shadow:\s*none;")
        self.assertRegex(style_sheet, r"\.about-card\.has-research-interests\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\);")
        self.assertRegex(style_sheet, r"\.about-research\s*\{[^}]*background:\s*var\(--panel-soft\);[^}]*border-top:\s*1px solid var\(--border\);")
        self.assertRegex(style_sheet, r"#about \.research-interests\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\);")
        self.assertRegex(style_sheet, r"#about \.research-interests li\s*\{[^}]*max-width:\s*78ch;")
        self.assertRegex(style_sheet, r"\.about-card \.about-education\s*\{[^}]*font-size:\s*var\(--type-intro\);")
        self.assertRegex(style_sheet, r"\.about-summary p\s*\{[^}]*text-align:\s*left;[^}]*text-wrap:\s*pretty;")
        self.assertRegex(style_sheet, r"#about \.research-interests li\s*\{[^}]*text-align:\s*left;[^}]*text-wrap:\s*pretty;")
        self.assertNotIn("text-justify: inter-character", style_sheet)
        self.assertRegex(style_sheet, r"\.catalog-index\s*\{[^}]*border-bottom:\s*1px solid var\(--border\);")
        self.assertRegex(style_sheet, r"\.catalog-tab\s*\{[^}]*border:\s*0;[^}]*border-radius:\s*0;[^}]*background:\s*transparent;")
        self.assertRegex(style_sheet, r"\.catalog-tab\.is-active::after\s*\{[^}]*background:\s*var\(--umich-maize\);")
        self.assertRegex(style_sheet, r"\.featured-links a:focus-visible\s*\{[^}]*color:\s*var\(--panel\);[^}]*background:\s*var\(--accent-strong\);")
        self.assertNotIn(".subsection-title", style_sheet)
        self.assertNotIn(".theme-chip", style_sheet)
        self.assertNotIn(".theme-chip", client_script)
        self.assertIn('content: attr(data-citations) " citations";', style_sheet)
        self.assertIn(".scholar-year:hover::after", style_sheet)
        self.assertIn('tabindex="0" aria-label="', client_script)
        self.assertNotIn("--umich-maize: #765700;", style_sheet)
        self.assertIn("renderFeaturedAuthors(publication)", client_script)
        self.assertIn("openLinksInNewTabs();", client_script)
        self.assertIn('a[href]:not([href^="#"]):not([href^="mailto:"])', client_script)
        self.assertIn('link.setAttribute("target", "_blank")', client_script)
        self.assertIn('link.setAttribute("rel", "noopener noreferrer")', client_script)
        self.assertIn("bindThemeToggles();", client_script)
        self.assertIn("<h1><strong>Wei-Hsiang Lo</strong></h1>", document)
        self.assertIn('<p class="mobile-name"><strong>Wei-Hsiang Lo</strong></p>', document)
        self.assertIn('href="https://batlab.info/">Behavior, Accessibility, and Technology Lab (BAT Lab)</a>', document)

    def test_production_navigation_uses_requested_order(self):
        root = Path(__file__).resolve().parents[1]
        document = (root / "index.html").read_text(encoding="utf-8")
        desktop_nav = document.split('<nav class="tabs" aria-label="Primary">', 1)[1].split("</nav>", 1)[0]
        mobile_nav = document.split('<nav class="mobile-tabs tabs"', 1)[1].split("</nav>", 1)[0]
        expected = ["about", "research", "presentation", "notes", "experience"]

        self.assertEqual(re.findall(r'data-tab="([^"]+)"', desktop_nav), expected)
        self.assertEqual(re.findall(r'data-tab="([^"]+)"', mobile_nav), expected)
        self.assertNotIn('id="education"', document)
        self.assertEqual(document.count('class="presentation-card record-card"'), 7)
        self.assertEqual(document.count('class="award-tile record-card"'), 4)
        award_section = document.split('id="notes"', 1)[1].split("</section>", 1)[0]
        self.assertIn("<time>2025–2027</time>", award_section)
        self.assertIn("<h3>Rackham Conference Travel Grant — University of Michigan</h3>", award_section)
        self.assertIn(
            "<h3>Donald Beall Student Award for Engineering Accomplishment — San Jose State University</h3>",
            award_section,
        )
        self.assertIn("Teaching Experience", document)
        self.assertIn("IOE - 333 Human Factors Ergo", document)
        self.assertIn("THEA - 1118 Visual Identity Design", document)
        home_section = document.split('id="about"', 1)[1].split('id="experience"', 1)[0]
        self.assertNotIn("Research Themes", home_section)
        expected_labels = [
            *[f"[J{index}]" for index in range(1, 4)],
            *[f"[C{index}]" for index in range(1, 10)],
            *[f"[P{index}]" for index in range(1, 3)],
            *[f"[T{index}]" for index in range(1, 4)],
        ]
        self.assertEqual(re.findall(r'data-publication-label="([^"]+)"', document), expected_labels)
        featured_section = document.split('class="featured-papers-section"', 1)[1].split("</section>", 1)[0]
        self.assertEqual(featured_section.count('class="featured-meta-row"'), 3)
        self.assertEqual(
            re.findall(r'<span class="publication-label">(\[[A-Z]\d+\])</span>', featured_section),
            ["[J1]", "[C3]", "[J3]"],
        )
        self.assertEqual(featured_section.count("<strong>WH Lo</strong>"), 3)
        self.assertNotIn("View Scholar", featured_section)
        journal_section = document.split('id="pub-panel-journal"', 1)[1].split('id="pub-panel-conference"', 1)[0]
        self.assertEqual(journal_section.count('class="paper-actions"'), 3)
        self.assertNotIn('>CV</a>', journal_section)

    def test_cv_social_links_use_text_label(self):
        root = Path(__file__).resolve().parents[1]
        document = (root / "index.html").read_text(encoding="utf-8")

        self.assertEqual(document.count('data-tooltip="CV">CV</a>'), 2)


if __name__ == "__main__":
    unittest.main()
