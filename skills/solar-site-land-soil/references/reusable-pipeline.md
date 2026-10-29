# Reusable execution instead of per-site scripts

Use `scripts/pipeline.py` as the normal entry point for deterministic work. Agent selects public sources, confirms the parcel and submits a JSON job. Do not generate new collection, gradient, clipping, plotting or PDF scripts for a routine site. Read compact task summaries first; inspect saved raw results only for source discovery, warnings or interpretation. Imagery judgement, feeder confirmation and operative planning interpretation stay with the agent.

## Available reusable operations

| Operation | Purpose |
|---|---|
| json / download | Anonymous JSON or bounded file download; provenance, timestamp and checksum |
| parcel_lookup | Exact configured address/ARN query; ambiguous matches are retained for review |
| query | Paginated parcel-intersection query of a supplied public ArcGIS layer |
| geodesic_area / project | GeometryServer geodesic area and explicit coordinate conversion |
| clip_areas | Batch intersection and geodesic area per zoning/soil/wetland polygon; retain boundary touches |
| image_export / terrain_export | Download georeferenced exports; terrain extent/resolution and halo calculated from projected parcel |
| osm | Bounded public infrastructure context; no inferred absence |
| soil_summary / route / capacity | Reuse existing classification, route-length and calculator-trial functions |
| pdf_text | Extract matching PDF pages for agent review; not legal interpretation |
| terrain | Existing GeoTIFF worker with unit/CRS/coverage checks |
| map / gallery | Boundary/soil/vector overlays with holes and self-contained HTML gallery |
| extend / assessment_update | Assemble supplied observations and computed metrics without rewriting source evidence |
| validate / report / pdf | Check results, generate English report/JSON and export report/maps/data PDFs |

## Job contract

```text
python scripts/pipeline.py --config job.json --out OUTPUT_DIR
python scripts/pipeline.py --config job.json --out OUTPUT_DIR --offline --resume
```

A job contains tasks with unique safe id, operation, args, and optional depends_on. Within args, `{"task":"earlier_task","select":["field","nested_field"]}` reads a prior result; it also establishes the dependency. A task reference is configuration data, not code. File paths are caller inputs; no developer-specific paths are required. For a minimal independent calculation:

```json
{"workers":4,"tasks":[{"id":"soil","operation":"soil_summary","args":{"features":"soil-query-evidence.json"}},{"id":"validation","operation":"validate","args":{"assessment":"assessment.json"}}]}
```

Use the documented Python signatures for operation arguments; modules are directly importable by a future web backend. `references/source-registry.json` contains previously used official discovery hints and their coverage, not guaranteed current endpoints. Confirm source metadata before selecting a service; Grey County services do not cover all Ontario municipalities.

Independent ready tasks run with up to four threads; dependencies run in later batches. A failed source skips its dependent tasks, while unrelated operations continue. Summary contains status, exceptions and result-file paths. Full responses stay in results and cached evidence. This is in-process task orchestration, not a background job service; a future web app must provide its own queue and access controls.

The HTTP cache key includes URL, parameters, request method and response type. TTL defaults to zero (refresh online). Opt into a positive TTL only for suitable data; capacity/planning freshness must be checked each assessment. Offline cache reuse preserves original retrieval timestamp and marks reuse, rather than pretending to fetch current data. Timeouts get one retry; login/denied results are not bypassed. No GeoWarehouse or credentials.

`--resume` reuses completed local computations only when code, arguments and input-file hashes match and outputs exist. Network operations still run through the freshness/cache rules. Output paths must remain in the task directory. Checkpoints allow interrupted jobs to continue; this is not a promise that every external source is available.

## Replay previous site evidence

```text
python scripts/replay_case.py --site-dir SAVED_SITE_DIR --out REPLAY_DIR --pdf
python scripts/replay_case.py --site-dir SAVED_SITE_DIR --out REPLAY_DIR --pdf --resume
```

This preset accepts the saved case directory layout from previous runs, discovers retained evidence under previous-* when necessary, and generates a job file. It does not embed a particular civic address or feeder. It reuses the saved assessment's observations and source timestamps without refreshing them. The current preset expects the saved Ontario case's metre-based terrain and 2015 imagery; other surveys require an explicit custom job, correct units and updated map captions. Missing mandatory inputs raise a clear error.

The preset performs validation, soil summary, terrain processing, map overlays, gallery and report generation; optional PDF output creates three documents. Saved zoning clips are drawn when available. This validates deterministic reuse, not a fresh site evaluation or independently verified planning/utility result. JSON remains complete; readable reports summarize long values and point to structured evidence. Use the available PDF workflow's artifact marker and render/inspect pages when generating PDFs through this pipeline.

## Dependencies and validation

Collection, GIS service calls and orchestration use the standard library. Terrain/maps require NumPy/Pillow; PDF export requires ReportLab/pypdf; PDF text uses pypdf. No automatic package installation. Pure numerical functions, file adapters and network collection are separate modules, so they can be reused without Codex.

Run the existing self_test.py, self_test_full.py, self_test_terrain.py and self_test_pipeline.py. The last accepts --work-dir for a permitted temporary directory. Coverage includes cache provenance, offline behavior, repeated-page detection, zero-area touches, failure isolation, resume invalidation, polygon holes and preservation of dates/values. Live source availability is checked when actually assessing a site; offline tests do not claim to verify current services.

## Migration from temporary code

| Previous temporary task | Reusable replacement |
|---|---|
| collect_public.py / refresh_solar_site.py | EvidenceClient; json/query/parcel_lookup/download; bounded task batches |
| solar_more_gis.py / solar_clip.py | gis_tasks.project, area, clip_areas; pipeline operations |
| solar_planning_sources.py | Source registry, configured downloads and pdf_text |
| finalize_assessment.py slope and maps | terrain_slope, site_maps and pipeline |
| finalize_full_solar.py calculations and assembly | assess_full, soil_summary, assessment_update and site_outputs |
| verify_solar_output.py | validate_report and task validation |
| export_solar.py | site_outputs.export_pdfs |
| update_solar_streetview_skill.py | One-time maintenance script; workflow retained as reference instructions, not a site-evaluation task |

Historical source scripts stay untouched for audit. Their site-specific conclusions, repair-by-string-replacement steps and old authentication probes are intentionally not reused as evaluation logic.
