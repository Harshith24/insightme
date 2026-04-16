# Area Code Mapping

> How we map phone numbers to geographic regions for the map view.

## Approach
We bundle a static dictionary mapping ~300 US area codes to approximate (latitude, longitude, region_name) tuples. No external API calls.

### Why Static?
- **Privacy** — no network calls, no sending phone data anywhere
- **Reliability** — no API rate limits or downtime
- **Speed** — instant lookup

### Data Source
Based on NANPA (North American Numbering Plan Administration) public data. Each area code maps to the approximate center of its geographic region.

## How It Works
1. Take a normalized 10-digit phone number
2. `extract_area_code()` returns the first 3 digits
3. `get_area_code_location()` looks up lat/lng/name from the static dict
4. UI plots these on an interactive map

## Limitations
- **Overlay area codes** — Some cities have multiple area codes covering the same area. We map each to a representative center point.
- **Number portability** — A person can keep their area code when they move. The map shows "where the phone number is from," not "where the person lives." The UI labels this clearly: "Contact regions by phone number."
- **International numbers** — Not mapped. Only US area codes are in the lookup table.
- **VoIP numbers** — May have area codes that don't reflect geography.

## File
`src/insightme/data/area_codes.py` — `AREA_CODE_COORDS` dict + `get_area_code_location()` function.

## Related Pages
- → [phone-normalization.md](phone-normalization.md) — Area codes extracted from normalized numbers
- → [ui-structure.md](ui-structure.md) — Map view page
- → [privacy.md](privacy.md) — Why we avoid external APIs
