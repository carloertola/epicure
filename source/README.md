# EFCT 2025 data import

Source: Ethiopian Public Health Institute (EPHI) and Food and Agriculture Organization of the United Nations (FAO). 2025. *The Ethiopian Food Composition Table 2025*. Addis Ababa, Ethiopia. Copyright EPHI 2025. The supplied PDF permits use in products with acknowledgement and without implying endorsement. A verbatim copy is served at `/data/source-table.pdf`.

`scripts/import_foods.py` imports PDF pages 45–344 (printed pages 33–332), using the actual PDF table cell rectangles. It reads each of the five nutrient sections and joins them by the printed six-digit food code. This matters because some source sections contain repeated rows and some table headers have different geometry or incorrect tag labels. It preserves the original nutrient text without imputing absent nutrient amounts.

Run with Python and `pdfplumber`:

```text
python scripts/import_foods.py path/to/Ethiopian-Food-Composition-Table-2025.pdf
python scripts/validate_data.py
```

The `--reuse-extraction` option rebuilds JSON from `source/extracted-rows.json` after a complete extraction. This option is for transformations and debugging, not for importing a changed PDF. The source SHA-256 is recorded in both the dataset and audit.

## Schema

`public/data/foods.json` is an object with `metadata`, `components`, `groups`, and `foods`.

- `metadata`: citation, copyright, source hash, measurement basis, source counts, limitations, PDF path and page numbering.
- `components`: ordered objects with `key`, `label`, `unit`, INFOODS `tag`, and `section`. The PDF declares 39 nutritional components. There are 40 printed columns when edible portion is included, and 41 numeric keys because the combined energy kJ(kcal) column is split into two source units.
- `groups`: the 17 original two-digit food groups, with `declaredCount` and `importedCount`.
- Each food: `id` and `code` preserve the printed code; `name` and `amharic` preserve English and Amharic transliteration descriptions; `groupId` is the first two code digits.
- `nutrients`: numeric amounts per 100 g edible portion on a fresh-weight basis. `edible` is a conversion coefficient, not grams of a nutrient. Values marked trace, below detection limit, or missing are `null`, never zero. Both `energy_kj` and `energy_kcal` are present; one may be null when the source omits that unit.
- `raw`: all 40 original printed cell expressions, including `[ ]`, `tr`, `<LOD` and empty strings. Combined energy is retained as `raw.energy`.
- `quality`: arrays of flags for affected numeric keys: `lower-quality`, `trace`, `below-detection-limit`, `missing`, and `source-anomaly`.
- `nonAfrican`: the source's per-component markers, usually `oa`. Their absence does not establish that a value was analyzed in Ethiopia.
- `statistics`: per-component `sdOrRange` and `sampleCount` strings when supplied in the condensed table. No distinction between SD and range is inferred beyond the printed text.
- `pages`: one-based PDF pages for `macros`, `minerals`, `vitaminsBC`, `vitaminsADE`, `fats`. Subtract 12 for printed page numbers.
- `baseName`, `state`, `stateBasis`, `methods`, `conditions`, and `timings`: description-derived search aids. They are not a publisher-supplied taxonomy. `state` is a conservative raw/cooked/recipe heuristic; the complete source description is authoritative. Unspecified preparation defaults to raw as instructed by the guide. Harvest, cultivation, storage and preparation conditions absent from the PDF are not invented.

## Source limitations found during import

The guide declares **727 foods**, but the condensed nutrient table contains **722 distinct printed food codes**. All group counts agree except roots/tubers (43 actual versus 44 declared) and condiments/spices (37 actual versus 41 declared). All 722 codes occur in all five nutrient sections. The missing five entries cannot be recovered from this PDF and have not been fabricated. The complete 69-component Excel datasheets and recipe book were not supplied.

The cereal retinol column contains an apparent sequential-number error in the PDF itself: for example, PDF page 48 lists ascending values 1–9 and PDF page 98 lists 109–121. The source image was rendered and visually checked. All 157 cereal entries carry `quality.retinol: ["source-anomaly"]` and an explanatory `sourceNotes` message. Printed values are preserved for audit, but must be excluded from nutritional recommendations pending verification by the publisher.

Some energy cells omit kcal entirely. Some omit a closing parenthesis; the two visible numbers can still be parsed. Two expressions have an ambiguous missing opening parenthesis and remain null in both numeric energy fields. No missing unit is derived or estimated in the source dataset.

`public/data/data-audit.json` and `source/data-audit.json` document each page, code, count discrepancy, header/cell irregularity, duplicate source occurrence, component coverage, quality flags, and import checks. `source/extracted-rows.json` retains all source row occurrences, including duplicates. Validation checks include visually inspected fruit, seed and milk cells plus cases involving wrapped descriptions and duplicate nutrient-section rows.
