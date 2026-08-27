import importlib.util
import json
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
            "about": {"paragraphs_html": ["About {{umich_blue}}"]},
            "appointment": {
                "title": "Researcher",
                "organization_html": "{{ihub_purple}}",
                "advisor_html": "Advisor",
            },
            "latest_updates": [{"datetime": "2025", "label": "2025", "text": "Curated update"}],
            "experience": [{"period": "2026-Present", "title": "Role", "description_html": "Work"}],
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
                "last_successful_sync_label": "Aug. 27, 2026",
                "last_successful_sync_mode": "scholar-sync",
            },
            "counts": {"all": 2, "journal": 2},
            "category_order": ["journal"],
            "category_labels": {"all": "All", "journal": "Journal"},
            "featured_slug": "older-paper",
            "publications": [
                {
                    "slug": "older-paper",
                    "title": "Older Paper",
                    "authors": "A. Author",
                    "venue": "Journal A",
                    "year": 2025,
                    "category": "journal",
                    "links": [{"label": "DOI", "href": "https://doi.org/older"}],
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
            ],
        }

    def template(self):
        return "\n".join(
            f"  <!-- site-data:{name}:start -->\n  stale\n  <!-- site-data:{name}:end -->"
            for name in MODULE.BLOCK_NAMES
        ) + "\n"

    def test_render_links_profile_and_publication_data(self):
        rendered = MODULE.render_document(self.template(), self.profile, self.publications)

        self.assertIn('data-target="2">2</strong>', rendered)
        self.assertIn('data-target="55">55</strong>', rendered)
        self.assertIn("last successful sync Aug. 27, 2026", rendered)
        self.assertIn("New Paper", rendered)
        self.assertIn("Researcher", rendered)
        self.assertIn("Curated update", rendered)
        self.assertIn("CV updated August 2026 · Site data checked Aug. 27, 2026", rendered)

    def test_render_is_idempotent(self):
        once = MODULE.render_document(self.template(), self.profile, self.publications)
        twice = MODULE.render_document(once, self.profile, self.publications)

        self.assertEqual(once, twice)

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

        self.assertEqual(document, MODULE.render_document(document, profile, publications))
        self.assertEqual(len(collector.ids), len(set(collector.ids)))


if __name__ == "__main__":
    unittest.main()
