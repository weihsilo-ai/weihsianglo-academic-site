---
date: 2026-08-27
topic: site-wide-data-linkage
---

# Site-wide data linkage

## What We're Building

The production homepage will use two explicit sources of truth: Google Scholar data for publications and metrics, and one curated profile JSON file for biography content. A successful refresh will regenerate the HTML fallback so JavaScript users, no-JavaScript visitors, and search crawlers all receive matching values.

## Why This Approach

The existing browser hydration is useful but leaves stale values in the deployed HTML. Generating the fallback from the same source removes that split while keeping the site static, inexpensive, and compatible with Vercel. Curated career information should not be inferred from LinkedIn or repeatedly parsed from a PDF.

## Key Decisions

- `data/publications.json` remains authoritative for counts, sync date, featured paper, catalog, and the newest-publication update.
- `data/site-profile.json` becomes authoritative for About, Current Appointment, curated updates, Experience, Education, Awards, and the CV revision label.
- `index.html` keeps readable fallback HTML inside named generated blocks; the existing client-side publication hydration remains as a fresh-data safeguard.
- The daily LaunchAgent runs the existing pipeline, stages all generated linked files, pushes only when data changes, and exits. It does not become a resident watcher.
- Rendering fails closed when a generated marker or required profile field is missing, preventing partial page rewrites.

## Not Doing

- No LinkedIn scraping or external account access.
- No automatic CV PDF parsing or generation.
- No changes to demo pages, research tools, unrelated app files, or `InkspaceVault/`.
- No external-link crawler running in the background.

## Open Questions

None. The user approved the single-profile-source and non-resident daily sync direction.

## Next Steps

Implement the renderer, cover idempotency and failure behavior, connect it to both local and manual-cloud sync paths, deploy, and verify the production source plus LaunchAgent process state.

<details>
<summary>Decision history</summary>

- The production Scholar JSON was current, while the static homepage fallback and footer were stale.
- A single curated profile file was recommended instead of scraping personal information.
- The user approved this direction on Aug. 27, 2026.

</details>
