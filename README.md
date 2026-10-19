# Epicure

**Good food. Better together.** A minimal food library and meal studio based on the Ethiopian Food Composition Table 2025.

“Let thy food be thy medicine, and thy medicine be thy food”

## Use it

- Site: https://epicure.carloertola.com
- Browse source food states, search English descriptions and Amharic transliterations, filter categories and preparation, and compare 100 g nutrient values.
- Select edible gram weights, inspect full meal totals and coverage, and explore transparent protein, fiber, iron and food-group-variety suggestions.
- Food pairing, cooking and beverage advice links to supporting NIH, FDA and primary research sources.
- Plates persist in browser local storage. Export JSON or copy a URL that encodes the plate. No account or backend meal collection.

## Run locally

No dependencies or build step. Node.js 20 or newer:

```sh
node scripts/serve.mjs
node --check public/app.js
node --test tests/*.test.mjs
```

Open http://127.0.0.1:4173. Serve `public/`, never the repository root.

## Data provenance

Ethiopian Public Health Institute (EPHI) and Food and Agriculture Organization of the United Nations (FAO). 2025. *The Ethiopian Food Composition Table 2025.* Addis Ababa, Ethiopia. © EPHI 2025. Reused with acknowledgement under the permission printed in the source PDF. No EPHI or FAO endorsement is implied.

Original PDF: `public/data/source-table.pdf`. Imported data and original value markers: `public/data/foods.json`. The import script and audit document column mapping, source discrepancies and uncertain entries. Bracketed lower-quality values, non-African provenance, missing values and trace markers remain inspectable. Harvest and cooking conditions are included only as described by the source. No invented harvest model, cooking yield or absorption multiplier.

Food photographs are ingredient-family references. They are not cultivar, recipe or species verification. Images, original links and individual licenses are in `public/data/images.json`, also displayed on the Sources page. Missing pictures are explicitly labeled. The app's sprout-and-bowl SVG logo is an original design.

## Automatic deployment

The cPanel account polls the public GitHub `main` branch every minute. No hosting password, API token, webhook secret or GitHub deploy key is required. A successful source push normally appears within about one minute, plus fetch time.

- Repository checkout: `/home/carloertolanet/repositories/epicure`
- Deployment state: `/home/carloertolanet/.deployments/epicure`
- Public releases: `/home/carloertolanet/epicure-public/releases`
- Domain document root: `/home/carloertolanet/epicure-public/current`
- Cron invokes the installed `poll-and-deploy.sh` under a nonblocking file lock.
- The script fetches `main`, exports only `public/` into a commit-specific release directory, verifies required files, and atomically switches the `current` symlink.
- Previous releases are preserved. Roll back by switching `current` to an earlier release and pausing the Epicure cron entry while investigating.
- Public responses use revalidation headers so a successful update is not hidden by stale browser or CDN assets.
- GitHub Actions checks JavaScript and the calculation/data tests. The hosting poll does not wait for Actions; run checks before pushing. Only trusted maintainers should have write access to `main`.

The installed deployment script is outside the served root. Changes to `deployment/poll-and-deploy.sh` require explicitly updating the installed copy. The script never overwrites other sites, existing cron entries, or user meal data.

The provider manages Cloudflare DNS through Yegara HOST → Package Details → Cloudflare → Sync Zone Editor. cPanel’s local DNS changes need that synchronization because the domain’s authoritative nameservers are Cloudflare’s.

The verified photo catalog covers 678 of the 722 entries, using ingredient-family references and explicit prepared-dish labels. The 44 gaps are listed in `public/data/image-audit.json` and appear as labeled placeholders.

## Nutrition approach

Values describe source foods per 100 g edible portion on a fresh-weight basis. Cooked foods and dry raw ingredients use their own profiles. Totals are sums of selected values scaled by actual weights; missing values remain unknown. Suggestions are a transparent heuristic, not an optimized clinical diet. No food is promised to prevent or treat disease.

## Project structure

`public/app.js` renders accessible responsive UI. `public/engine.js` handles calculation, validation and contextual advice. `tests/` verifies nontrivial calculation and safety rules. `scripts/` contains the local server and data/image tooling. `deployment/` contains the hosting script.
