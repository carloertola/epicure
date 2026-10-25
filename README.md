# Gursha

**Get more from your food.** A simple meal planner using the Ethiopian Food Composition Table 2025, published food-group serving references, and an optional encrypted nutrition journal.

## Experience

- Landing page with the supplied Gursha logo, ingredient search, the requested description and **Plan a Meal**.
- Three steps: diners (age, kid/adult and female/male nutrition reference), ingredients with pairing/spice suggestions, then available equipment and preparation methods.
- Preparation sequence, household quantities, separate diner portions, calories, macronutrients and micronutrients with explicit data coverage.
- Saved meal recipes and individual intake entries. Daily, Monday–Sunday weekly, calendar-month, yearly and custom-range totals, filtered by profile.
- Private storage, locking, encrypted backup export/import, recipe removal and intake correction. No account or meal-data upload.
- Compact branded footer following the shared structure of Bete Zelan and Voxedu: social links, creator credit, and a legal/accessibility/sources disclosure.

## Run and verify

Buildless JavaScript, Node.js 20 or newer, no dependencies:

```sh
node scripts/serve.mjs
node --check public/app.js
node --check public/engine.js
node --check public/guidance.js
node --check public/portions.js
node --check public/planner.js
node --check public/vault.js
node --check public/sw.js
node --test tests/*.test.mjs
```

Local address: `http://127.0.0.1:4173`. Serve only `public/`. Web Crypto and the optional offline cache need HTTPS or localhost.

## Portion model

The Australian Government **Eat for Health** daily standard serves are transcribed by age band and sex, for ages 2+. For each represented food group:

`diner daily serves × chosen meal fraction ÷ foods in that group × standard serve grams`

The meal fraction defaults to one third. This allocation is Gursha’s planning convention, not a published personalized meal prescription. The app discloses its references, assumptions, age boundaries and applicability. A standard serve is distinct from a person’s appetite or calorie requirement.

- Vegetables: 75 g; fresh fruit: 150 g; cooked pulses counted once as protein foods: 150 g; nuts/seeds: 30 g as an occasional protein-food equivalent.
- Appropriate cooked meat, fish, eggs, tofu, yoghurt and cheese use the published food-specific amounts.
- Cooked grains use a 100 g planning value within the published 75–120 g range. Bread/flatbread uses 40 g, explicitly a proxy when applied to injera.
- Oil uses the midpoint of the age/sex allowance range. Spices and avocado use disclosed culinary starting amounts.
- A food/state without a defensible gram reference requires user-entered edible grams. Milk volume is not silently equated to gram weight.
- Missing food groups are never compensated for by increasing another group. The meal is not promised to meet every nutritional requirement.

References:

- [Adult daily serves](https://www.eatforhealth.gov.au/food-essentials/how-much-do-we-need-each-day/recommended-number-serves-adults)
- [Children’s daily serves](https://www.eatforhealth.gov.au/food-essentials/how-much-do-we-need-each-day/recommended-number-serves-children-adolescents-and-toddlers)
- [Standard serve sizes](https://www.eatforhealth.gov.au/food-essentials/how-much-do-we-need-each-day/serve-sizes)

## Food data and processing

Ethiopian Public Health Institute (EPHI) and FAO. 2025. *The Ethiopian Food Composition Table 2025.* Addis Ababa. © EPHI 2025. Reused with acknowledgement. No endorsement is implied.

The 722 imported food codes remain unchanged, with their original printed values and source pages. Trace, missing and lower-quality markers remain inspectable. Apparent source anomalies are excluded from calculations. `public/data/source-table.pdf`, `foods.json` and the audits retain provenance. All 722 food entries have local image references with credits/licenses in `images.json`. These include source photographs, explicitly labeled recipe/ingredient-family references, and four AI-generated veal/organ illustrations documented in `image-illustrations.html`. Thumbnail silhouettes remain visible in rounded square frames at 38–44 px. The Gursha brand image was supplied by the project owner and is used without raster edits.

The processing engine checks selected equipment, rejects unsupported combinations, and preserves food subtype when matching a cooked profile. A raw lean-meat entry cannot silently become a cooked organ-meat entry. Cooked targets must be weighed after preparation; no cooking yield is guessed. If a preparation has no matching nutrient profile, its values are unknown rather than zero. Blending/grinding uses ingredient weight before water and assumes solids are retained. No absorption or retention multiplier is invented.

Where a numeric kJ value is recorded but kcal is absent, `planner.js` converts using 4.184 kJ per kcal, flags the result as derived, and preserves the original data. Individual readings expose both the calculated estimate and original source values.

Pairing rules cover plant iron/vitamin C and carotenoids/dietary fat using disclosed practical thresholds. Sources distinguish food-level human studies, preparation guidance, culinary flavor suggestions and supplement evidence. No universal nutritional score or disease claim is made.

## Private journal

Planning drafts stay in page memory. Opt-in recipes and intake entries are serialized into a single authenticated **AES-256-GCM** ciphertext in browser local storage (`gursha-private-v1`). The key is derived using **PBKDF2-SHA256, 310,000 iterations**, a random 16-byte salt and a new random 12-byte nonce on every save. Keys are non-extractable and kept in memory; passphrases are never stored or uploaded.

The journal locks manually, after ten minutes of inactivity, on another tab’s change, and when leaving/reloading the page. Locking discards decrypted records and planning memory. Writes compare the prior encrypted envelope and use browser Web Locks when available to avoid silently overwriting a newer journal. Storage or quota failures are reported without claiming success.

Encrypted JSON backups can be exported and restored using their original passphrase. Import verifies the encryption envelope and record structure before replacing storage. There is no password reset or server recovery copy. Browser-data clearing, changing origins, or losing the device can remove access. A compromised device or an unlocked screen remains outside the protection of at-rest encryption.

Each logged intake is for a selected diner’s actual portion fraction, not the entire household batch. Nutrient snapshots and their missing/flagged coverage are retained with each entry. All-profile totals are explicitly labeled as combined. The offline cache contains only public app/data/image files, never decrypted meal data.

## Hosting

Public address: **https://gursha.carloertola.com**. The existing GitHub repository remains `carloertola/epicure` so the established cPanel polling deployment continues to work. Repository naming is infrastructure, independent of the Gursha product name.

The previous homepage redirects to Gursha. An explicit old-origin journal route, `https://epicure.carloertola.com/?legacy=1#journal`, remains available for unlocking and exporting encrypted backups before restoring them on Gursha. Browser storage cannot move across origins automatically. The meal book links this migration route. Static assets remain available on the old origin so the export page continues to work.

The cPanel account fetches public GitHub `main` every minute and atomically switches the public release symlink. Only `public/` is exported:

- Checkout: `/home/carloertolanet/repositories/epicure`
- Deployment state: `/home/carloertolanet/.deployments/epicure`
- Releases: `/home/carloertolanet/epicure-public/releases`
- Document root: `/home/carloertolanet/epicure-public/current`

These existing remote paths are retained to preserve the installed cron job. `deployment/poll-and-deploy.sh` documents the deployed script. Previous releases are retained for rollback. GitHub Actions and local tests must pass before pushing because the hosting poll does not wait for CI.

The provider’s authoritative Cloudflare DNS requires synchronization through **Yegara HOST → Package Details → Cloudflare → Sync Zone Editor** after cPanel DNS changes. A cPanel domain entry alone does not verify public DNS or TLS. The legacy subdomain should redirect only once Gursha’s DNS, certificate and content are confirmed working.

## Main modules

- `app.js`: landing page, wizard, reference readings, preparation result and journal UI.
- `portions.js`: published serving references and transparent household allocation.
- `planner.js`: equipment constraints, exact-state matching, preparation sequence, nutrition estimates and calendar aggregation.
- `vault.js`: encrypted device storage, backup validation and concurrent-write protection.
- `guidance.js`: evidence-linked pairings, processing tips and culinary spice suggestions.
- `engine.js`: food groups, validated portions and source-aware arithmetic.
- `sw.js`: optional public-file offline cache.

Tests cover source provenance, calculations, serving boundaries, group allocation, equipment constraints, food subtype matching, missing processed data, energy-unit conversion, journal periods, encryption/tamper rejection, backups and concurrent writes.
