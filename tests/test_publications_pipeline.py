import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "publications_pipeline.py"
SPEC = importlib.util.spec_from_file_location("publications_pipeline", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PublicationsPipelineTests(unittest.TestCase):
    def test_google_scholar_parser_collects_metrics_and_yearly_citations(self):
        document = """
        <meta name="description" content="Researcher - Cited by 60">
        <table id="gsc_rsb_st">
          <thead><tr><th></th><th>All</th><th>Since 2021</th></tr></thead>
          <tbody>
            <tr><td>Citations</td><td class="gsc_rsb_std">60</td><td class="gsc_rsb_std">60</td></tr>
            <tr><td>h-index</td><td class="gsc_rsb_std">5</td><td class="gsc_rsb_std">5</td></tr>
            <tr><td>i10-index</td><td class="gsc_rsb_std">1</td><td class="gsc_rsb_std">1</td></tr>
          </tbody>
        </table>
        <div class="gsc_md_hist_b">
          <span class="gsc_g_t">2024</span><span class="gsc_g_t">2025</span><span class="gsc_g_t">2026</span>
          <a class="gsc_g_a"><span class="gsc_g_al">2</span></a>
          <a class="gsc_g_a"><span class="gsc_g_al">29</span></a>
          <a class="gsc_g_a"><span class="gsc_g_al">29</span></a>
        </div>
        """

        publications, total, metrics = MODULE.parse_google_scholar_html(document)

        self.assertEqual(publications, [])
        self.assertEqual(total, 60)
        self.assertEqual(metrics["since_label"], "Since 2021")
        self.assertEqual(metrics["h_index"], {"all": 5, "since": 5})
        self.assertEqual(metrics["citations_per_year"][-1], {"year": 2026, "citations": 29})

    def test_serpapi_parser_collects_metrics_and_yearly_citations(self):
        payload = {
            "articles": [],
            "cited_by": {
                "table": [
                    {"citations": {"all": 60, "since_2021": 60}},
                    {"h_index": {"all": 5, "since_2021": 5}},
                    {"i10_index": {"all": 1, "since_2021": 1}},
                ],
                "graph": [
                    {"year": 2024, "citations": 2},
                    {"year": 2025, "citations": 29},
                    {"year": 2026, "citations": 29},
                ],
            },
        }

        publications, total, metrics = MODULE.parse_serpapi_scholar_author(payload, "author-id")

        self.assertEqual(publications, [])
        self.assertEqual(total, 60)
        self.assertEqual(metrics["since_label"], "Since 2021")
        self.assertEqual(metrics["i10_index"], {"all": 1, "since": 1})
        self.assertEqual(len(metrics["citations_per_year"]), 3)

    def test_merge_preserves_ordered_featured_slugs_for_future_syncs(self):
        slugs = ["paper-one", "paper-two", "paper-three"]
        raw_publications = [
            {
                "slug": slug,
                "title": slug.replace("-", " ").title(),
                "authors": "A. Author",
                "venue_line": "Journal · 2026",
                "year": 2026,
                "citations": 0,
                "scholar_url": f"https://scholar.example/{slug}",
            }
            for slug in slugs
        ]
        overrides = {
            "scholar_profile_url": "https://scholar.example/profile",
            "featured_slug": slugs[0],
            "featured_slugs": [slugs[2], slugs[0], slugs[1]],
            "items": {},
        }

        merged = MODULE.merge_publications(raw_publications, overrides, "test")

        self.assertEqual(merged["featured_slugs"], [slugs[2], slugs[0], slugs[1]])

    def test_merge_preserves_curated_citation_details_for_future_syncs(self):
        raw_publications = [
            {
                "slug": "paper-one",
                "title": "Paper One",
                "authors": "A. Author",
                "venue_line": "Journal · 2026",
                "year": 2026,
                "citations": 0,
                "scholar_url": "https://scholar.example/paper-one",
            }
        ]
        overrides = {
            "scholar_profile_url": "https://scholar.example/profile",
            "items": {"paper-one": {"citation_details": "Vol. 42(16) · pp. 13244–13271"}},
        }

        merged = MODULE.merge_publications(raw_publications, overrides, "test")

        self.assertEqual(
            merged["publications"][0]["citation_details"],
            "Vol. 42(16) · pp. 13244–13271",
        )


if __name__ == "__main__":
    unittest.main()
