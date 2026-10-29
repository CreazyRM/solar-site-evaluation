# Source process and evidence rules

Derived from `ON Solar Site Evaluation Process.docx`, supplied in the user's Solar Site Evaluation folder. All five sections are supported. Credentials are excluded. User update: GeoWarehouse is unavailable and must not be used. See grid-planning.md for the last three sections and the complete final-report fields.

## Land Location and Size

1. Check the supplied address in Google Maps or another accessible location source.
2. Locate the same site using public municipal/county parcels or another authoritative public service. Visually cross-check because addresses may be inaccurate. This replaces the original GeoWarehouse step.
3. Record property identification number (PIN) and assessment roll number (ARN).
4. Use AgMaps Assessment Parcel search by ARN when accessible. Confirm the intended polygon; measure the outline in acres. A screenshot does not itself supply accurate coordinates.
5. Keep the identified parcel context for the next section.

Accept a supplied parcel polygon as an alternative; identify it as user-provided until independently verified. Prefer geodesic/equal-area measurement. Do not measure square degrees or raw Web Mercator square metres as true acreage. One acre is 4046.8564224 square metres.

## Soil and Slope

1. In AgMaps enable Environment/Base Data > Ontario Soil Survey Complex > Soil Capability for Agriculture.
2. Save a soil map with approximately 50% transparency and another view without that layer. Show the parcel or clearly label an unconfirmed point/context view.
3. Record wetlands, transmission lines, gas lines and railroads crossing or near the site. Nearby feature distance must be measured if stated; do not invent a universal buffer distance.
4. Default soil acceptance is classes 4, 5, 6, 7. Classes 1, 2, 3 need a favorable zoning/OPA exception. Record `needs_review` until a current applicable provision supports an exception. In land/soil-only mode, leave planning unresolved. These are user screening preferences, not a substitute for current legal requirements. Organic soil, water and unclassified units are not numeric classes 4-7.
5. The source excludes slopes **greater than 15%**. Compute `abs(elevation difference in metres) / horizontal ground distance in metres * 100`. At exactly 15%, it is not greater than the stated cutoff. A degree value requires conversion `100 * tan(angle)`.
6. Source example: `(126 - 119) / 127.04 * 100 = 5.5101%`, approximately 5.51%, rather than the rounded 5% in the document. That sample is below the cutoff.

## Evidence scope

- `verified`: retrieved/measured from an identified source with adequate spatial scope; this is not an engineering certification.
- `provided`: asserted or uploaded by the user, not independently verified.
- `estimated`: interpolation, sampled terrain, approximate boundary/area, or uncertain precision.
- `needs_review`: conflicting information, pending parcel confirmation, or a rule exception requiring review.
- `skipped`: not collected/calculated; value is null, and an individual reason is required.

For mixed soil units, `CLI1/2/3` and `PERCENT1/2/3` describe composition inside a mapped unit. They do not identify the precise location of each component. Intersecting unit classes are not parcel area percentages unless separately computed, and a point query does not describe the whole property.

Always separate point/profile evidence from parcel-wide coverage. Do not give an overall soil/slope Pass based on a partial sample. A skipped field must not be converted into a failed, passed, zero or false field.
