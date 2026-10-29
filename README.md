# Ontario Solar Site Evaluation

Reusable Codex skill, Python calculations and evidence-review workflow for Ontario ground-mount solar screening.

## Scope

- Land location, public assessment parcels and acreage.
- Soil capability, wetlands and full-parcel slope.
- Access, connection-route geometry and actual utility capacity-test records.
- Zoning and Official Plan evidence.
- Maps, structured results and reports.

GeoWarehouse is excluded. Login-dependent indicators remain explicitly skipped. This project does not grant development approval, confirm title or reserve grid capacity. Public-source availability and coverage vary across Ontario.

## Setup

Use Python 3.11 or later:

```sh
python -m venv .venv
python -m pip install -r requirements.txt
python scripts/run_tests.py
```

Activate the virtual environment using the command appropriate for your shell before installing dependencies. NumPy/Pillow support terrain/maps; ReportLab/pypdf support PDF work. Standard collection and orchestration use the Python standard library. Optional pyproj improves local geodesic area measurement; without it the local fallback is explicitly estimated.

## Use with Codex

Install or copy `skills/solar-site-land-soil` to your own Codex skill directory. Keep this repository as the shared source of truth and update the installed copy after pulling changes. The repository contains project-level multi-agent helpers and role files; see `docs/solar-multi-agent.md` for setup and reviewer requirements.

```text
Use $solar-site-land-soil to evaluate [Ontario address].
```

The skill routes deterministic work through reusable programs. Agents confirm the parcel, select sources and interpret ambiguous imagery and planning provisions. Standard jobs produce metric drafts and exceptions; they do not replace independent review.

## Program entry points

```sh
python skills/solar-site-land-soil/scripts/pipeline.py --config job.json --out output/run
python skills/solar-site-land-soil/scripts/standard_plan.py --profile confirmed-profile.json --out output/draft
python scripts/solar_agents.py --help
```

Read `skills/solar-site-land-soil/references/standard-automation.md` and `reusable-pipeline.md` for input contracts. The multi-agent workflow requires a frozen confirmed boundary, exact indicator ownership, saved evidence and independent review. Model agents run through Codex; Python helpers do not themselves launch language models.

## Collaboration

Each collaborator uses their own account and local environment. Make changes on a branch, run offline tests, then merge reviewed changes. Keep source timestamps and uncertainty intact. Do not commit credentials, raw source documents, personal capstone files, output reports or caches. Historical case evidence is deliberately not included; offline replay commands require separately supplied saved evidence. Tests use synthetic fixtures only.

## Web integration

Python calculation and orchestration functions can be reused by a server backend. This repository is not a deployed website or public AI service. Authentication, task queues, browser execution, AI service credentials and hosting must be configured separately.
