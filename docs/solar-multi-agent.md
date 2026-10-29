# Solar multi-agent workflow

The primary Codex agent coordinates; custom role files live in `.codex/agents/`. Three specialist workers run after parcel confirmation, then one independent reviewer runs. Model selection follows the user's current configuration. Three workers plus the primary fit the current four-slot environment. No extra API account is needed for this local Codex workflow.

## Start an assessment

```text
Use $solar-site-land-soil to assess all five sections for [Ontario address].
Use this project's multi-agent workflow. Act as coordinator, confirm the parcel
first, then delegate to land_environment, grid_access and planning in parallel.
Have evidence_reviewer audit the completed results before you assemble the final
English assessment and maps. Exclude GeoWarehouse and skip login-dependent data.
```

For limited work, request only Land Location and Size and Soil and Slope. The coordinator handles the first section and dispatches only land_environment. Initial custom-agent discovery may require a new Codex chat in this project; the current session can pass the role instructions directly to available workers. A role TOML configures instructions; it does not execute Python or launch an agent by itself.

## Coordinator preparation

Read the skill's process and source rules. Confirm the address and jurisdiction, identify a public assessment parcel and visually compare it. Then run, using an available Python runtime:

```text
python scripts/solar_agents.py init --parcel PATH_TO_CONFIRMED_PARCEL --address "SITE ADDRESS" --boundary-source "SOURCE URL OR FILE" --confirmation-note "HOW THE PARCEL WAS CONFIRMED" --out output/solar-site/NEW_RUN
```

Add `--mode land-soil` for the original two-section scope; add `--offline` for saved-evidence work. GeoJSON must contain exactly one Polygon or MultiPolygon feature, closed rings and WGS84 longitude/latitude coordinates. Other CRSs need explicit conversion first. The helper copies the boundary to inputs/parcel.geojson and records its SHA-256. Logical freezing is enforced by repeated hash checks, not filesystem read-only flags.

The coordinator completes `coordinator/assessment.json` before review. The initializer supplies honest placeholders for PIN, ARN and acreage; replace them with sourced measurements or individual skip reasons. It does not infer identifiers or confirm a parcel automatically. Keep unrelated old specialist metrics out of this coordinator file. Changing the boundary requires a new run and new specialist results.

Each assignment.json declares role, indicator ownership and relative output path. Give each worker the absolute run directory and assignment path. Workers read the shared inputs, use existing `pipeline.py` operations and write evidence/maps plus result.json only to their own directory. These instructions restrict ownership, not the parent's actual filesystem permissions. Shared browser interactions must use separate tabs or be serialized.

## Specialist result contract

Use `schemas/agent-result.schema.json`. Each result contains schema_version, run_id, agent, boundary_sha256, generated_at, metrics and summary. Each metric contains indicator, status, value, sources, spatial_scope, method, limitations, evidence_files and reason. Spatial scope is an explicit description (parcel-wide, intersecting mapping unit, sampled profile or surrounding extent).

A source has source_url, retrieved_at, data_date (null if unavailable) and evidence_locator. Local supplied evidence may use an absolute local file path in source_url. Non-skipped metrics need a non-null value, sources and at least one saved evidence file. Skipped metrics have value null and a distinct reason. Known statuses are verified, provided, estimated, needs_review and skipped. Never use zero or false for unavailable indicators. Metrics must exactly match the assignment; extra observations belong inside values, limitations or raw evidence.

Evidence paths are relative to the run directory and must resolve inside the worker's own directory. Copy supplied evidence there when needed; preserve its original provenance. Do not change raw evidence to fit a conclusion. Numeric calculations remain deterministic pipeline operations, not model arithmetic.

## Validation, independent review and assembly

For deterministic work, specialists can use the skill's standard_plan.py with a confirmed profile, requesting only their owned indicators and writing drafts inside their assigned directory. The coordinator can separately generate area metrics. Drafts do not replace result.json or constitute reviewed evidence. See skills/solar-site-land-soil/references/standard-automation.md for profile fields and exception handling.

After validation, `python scripts/solar_agents.py review-diff --run RUN_DIR --baseline PREVIOUS_REVIEW_JSON` generates a focus list of changed files and affected indicators. Omit --baseline for the first review. Preserve the old review separately when tracking revisions. The baseline must refer to the same run and boundary. Reviewer confirms the complete current snapshot and cross-section impacts; changed files still require independent review. The diff is not approval and does not relax assembly's review gate.

```text
python scripts/solar_agents.py validate --run output/solar-site/NEW_RUN
python scripts/solar_agents.py assemble --run output/solar-site/NEW_RUN
```

The validator checks required fields/types, dates, role ownership, complete requested indicators, source/evidence presence, skip semantics, and boundary integrity. It returns reviewed_sha256 for each specialist result, every cited worker evidence file and coordinator assessment. This is structural validation, not proof that a source supports a claim.

The reviewer independently reads those files and sources, then writes review/review.json according to `schemas/agent-review.schema.json`. Its reviewed_sha256 must exactly match the validator snapshot. A ready verdict means fit for a sourced partial report, not approval or full eligibility. An unresolved blocking issue prevents assembly. If any cited evidence, worker result or coordinator file changes, review must be repeated. Correct a worker file only through that worker; keep a concise revision record with the evidence.

Assembly merges owned metrics without silently overwriting any coordinator metric and calls the existing report generator in final/. It preserves source dates, source details, limitations, audit issues and null overall_project_decision. Combine maps through the existing gallery operation. PDF exports use the PDF skill only when requested. This helper is not an LLM scheduler: Codex performs actual delegation. A future web backend can reuse contracts and deterministic helpers while supplying its own agent runner, queue and permissions.

## Offline setup checks

```text
python -m unittest discover -s tests -p test_solar_agents.py -v
python skills/solar-site-land-soil/scripts/replay_case.py --site-dir output/solar-site/019471-highway-6-2026-10-02 --out output/solar-site/multi-agent-setup-replay --resume
```

The replay checks existing deterministic operations against retained case evidence. It does not launch live specialists, query current planning/grid data or prove current Codex custom-role discovery. Do not label generated fixtures or replay outputs as fresh site assessments.
