# Standard jobs, computed metrics and focused review

Use `scripts/standard_plan.py` after confirming the parcel. Agent supplies one profile rather than writing each pipeline task or copying calculation values. The module builds registered pipeline operations and produces an assessment-draft.json plus a compact exception list. It does not discover unknown municipal services or infer planning permission.

```text
python scripts/standard_plan.py --profile confirmed-profile.json --out OUTPUT_DIR --plan-only
python scripts/standard_plan.py --profile confirmed-profile.json --out OUTPUT_DIR --resume
```

Profile fields: address, jurisdiction, boundary_file (WGS84 GeoJSON), boundary_source, boundary_sha256, confirmation_note; optional offline (default false), indicators (area, soil, wetlands, zoning, slope_full_area). Paths must be absolute. `sources` maps soil/wetlands/zoning to confirmed public ArcGIS layer URLs and geometry_server to a public GeometryServer URL. These sources can cover multiple municipalities; no per-town program is required. Missing sources become explicit exceptions for agent discovery.

For offline work, `saved` maps indicator names to saved response-wrapper JSON files. Preserve source, retrieved_at and data_date when available; never fabricate retrieval dates. Saved area evidence must contain the measured `summary` from the geodesic_area operation. Terrain uses the `terrain` object with the terrain worker's terrain, boundary, vertical_unit, source_metadata and optional cutoff arguments. The projected terrain boundary must correspond to the confirmed WGS84 parcel; CRS matching does not itself confirm that relationship. The worker retains source input hashes and processing parameters. Offline runs do not query live sources, even if a source URL is configured: the client allows cached responses only.

Standard jobs automatically query full-parcel soil/wetland/zoning intersections, measure area where configured, and run a supplied terrain export. The existing reusable pipeline handles concurrency, retries and checkpoints. Results populate metric values directly: CLI classes/proportions, measured area, wetland intersection count, zoning attributes and slope statistics. Soil outside the preferred range, unknown wetland regulatory constraints, incomplete terrain coverage and zoning interpretation remain needs_review. Missing provenance becomes skipped with a reason, while raw task results are retained. No intersection is not absence. Output dates identify generation separately from original retrieval.

Use the generated `automation-summary.json` first; inspect detailed files only for exceptions and judgement. Browser feeder selection, street imagery, by-law interpretation, source discovery and confirmation of data currency remain agent responsibilities. This feature is not an autonomous address-to-approval service.

## Multi-agent ownership

Run the generator in the assigned worker's directory and request only its owned indicators (land_environment: soil, wetlands, slope_full_area; planning: zoning). The coordinator may run area separately. The draft is not an approved agent result and does not overwrite coordinator/assessment.json or any worker result.json. Workers adapt confirmed draft metrics to their assigned result contract, retain other assigned indicators as sourced observations or explicit skips, and cite the saved evidence. Independent validation/review and assembly remain unchanged.

Include manifest_file pointing to the confirmed run's manifest.json for multi-agent work. Execution checks that its boundary fingerprint matches the profile and forces offline mode whenever the run manifest is offline, even if the profile requests live mode.

## Focused review

```text
python scripts/solar_agents.py review-diff --run RUN_DIR
python scripts/solar_agents.py review-diff --run RUN_DIR --baseline PREVIOUS_REVIEW_JSON
```

The command validates the current run, compares current file fingerprints with the previous review from the same run/boundary, and writes review/review-diff.json. It reports changed, removed and unchanged evidence and affected indicators. Any changed role result conservatively marks all its indicators affected; changed coordinator context marks every role affected. Reviewers also inspect cross-section impacts and limitations. An unchanged file is not automatic approval and a skip is not a failure.

The reviewer must still issue a review covering the full current reviewed_sha256 snapshot. New reviews may use the diff to focus effort while explicitly considering unchanged prior evidence. Changed files still require independent review. Neither a baseline file nor review-diff.json grants approval, removes blocking issues or bypasses assembly's exact-fingerprint gate. Retain the previous review separately before replacing review.json when tracking revisions.

Prior checks can be reused only when can_reuse_unchanged_prior_checks is true: the preserved baseline is ready, has no blocking issues, matches this run/boundary, and coordinator context is unchanged. The reviewer verifies unchanged hashes and prior coverage instead of repeating every previous raw-data reading. A rejected baseline or changed context expands the affected scope to all assigned indicators. Reviewers remain responsible for examining dependencies across sections and signing the complete current snapshot.
