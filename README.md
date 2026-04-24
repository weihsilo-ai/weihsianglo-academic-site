# Wei-Hsiang Lo Academic Site

Static academic portfolio for Wei-Hsiang Lo.

## Local structure

- `index.html` - main portfolio site
- `styles.css` - styling
- `script.js` - tab and dashboard behavior
- `data/publications.json` - synced publication data consumed by the site
- `data/publication-overrides.json` - curated summaries, tags, visuals, and category overrides
- `scripts/publications_pipeline.py` - Google Scholar sync and manual BibTeX import workflow
- `cv.html` - embedded CV viewer
- `assets/` - profile photo and project visuals

## Publication sync

This site now uses a compromise workflow:

- `GitHub Actions` runs a daily Google Scholar sync and updates `data/publications.json`
- the front-end reads `data/publications.json` and refreshes publication tabs, counts, and the featured paper
- if Scholar blocks or changes, you can fall back to a manual export

### Automatic sync

GitHub Actions workflow:

- `.github/workflows/scholar-sync.yml`

It runs `python scripts/publications_pipeline.py sync-scholar` and commits the regenerated data file when changes are found.

### Manual fallback

If Google Scholar sync stops working, export your selected publications from Google Scholar as BibTeX and run:

```bash
python3 scripts/publications_pipeline.py import-bibtex ~/Downloads/google-scholar-export.bib
```

That rebuilds `data/publications.json` while preserving the local summaries, tags, visuals, and category choices from `data/publication-overrides.json`.

## Deploy on Vercel

1. Import this repository into Vercel.
2. Keep the project root at `/`.
3. No build command is required for this static site.
4. After the first production deploy, confirm the assigned production domain.
5. If you later attach a custom domain, update:
   - `index.html`
   - `cv.html`
   - `robots.txt`
   - `sitemap.xml`

## SEO note

This repo currently points to the default Vercel production URL:

`https://weihsianglo-academic-site.vercel.app/`

If Vercel assigns a different production URL, update the canonical, Open Graph, and sitemap links to match.
