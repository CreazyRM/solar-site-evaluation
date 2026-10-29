# Offline parcel slope worker

Use `scripts/terrain_slope.py` when a suitable public bare-earth terrain export and matching projected parcel are already available. Agent responsibilities: select the actual site boundary, obtain the terrain and matching projection, establish elevation units and source provenance, then dispatch one worker job. Do not rewrite gradients, clipping or map rendering for each site. Read only the returned task summary unless coverage warnings, conflicting results or a missing input need investigation.

```text
python scripts/terrain_slope.py --terrain terrain.tif --boundary parcel-projected.json --vertical-unit metres --cutoff 15 --source-metadata terrain-export.json --out OUTPUT_DIR
```

Dependencies: NumPy and Pillow. Use the host's existing runtime; this worker is optional and never installs packages or accesses the network. Missing dependencies mean an unavailable worker, not a flat site. The original assess.py/assess_full.py helpers still use the standard library. Future backend code can import `analyze` (arrays) or `run_job` (files) directly; neither depends on Codex.

Inputs:
- A north-up single-band PixelIsArea GeoTIFF with scale/tiepoint and an explicitly supported metre-based UTM EPSG code (NAD83 UTM, WGS84 UTM or ETRS89 UTM ranges listed in the code). Geographic, Web Mercator, rotated and pixel-point grids are rejected rather than treated as ground metres.
- One projected Esri polygon with `rings` and `spatialReference.wkid`, or the saved GeometryServer wrapper containing one geometry plus `request.outSR`. CRS must match the raster; there is no automatic reprojection. Rings must be closed, nonzero-area and represent a valid non-overlapping polygon/multipart geometry. Self-intersection/topology repair is outside this worker: prepare valid boundaries with a GIS tool.
- Explicit elevation units: metres or feet. Feet are converted before calculation. Vertical datum/acquisition date still require source review. GeoTIFF NoData is read when present; `--nodata` can override it. Nonfinite and extreme float sentinel values are excluded. Other finite sentinel values must be declared.
- Optional saved source-metadata JSON for source URL and retrieval timestamp. This does not establish terrain acquisition date or refresh historical data.

The DTM must enclose the whole parcel and preferably include at least a one-cell surrounding halo. Every slope requires all nine cells in its Horn kernel. The halo supports derivatives at the parcel edge; statistics are clipped to parcel cell centres after calculation. Holes are excluded and valid disjoint parts are supported. Boundary beyond the raster is rejected to prevent false full-coverage claims. Missing kernels reduce reported coverage; missing elevations are never treated as zero slope.

Outputs: `task-summary.json` and compact stdout (status, processing time, coverage, key metrics, warnings, artifact paths); `slope-statistics.json` (full statistics, input SHA-256 hashes, parameters and source provenance); `slope-map.png` (UTM aspect ratio, boundary, threshold and legend); `report.md` (English result and limits). Runtime is worker processing time, not total agent/network time. The worker does not change the source site report or assert current terrain conditions. It does not subtract soil/wetland exclusions or issue an overall project Pass/Fail.

Run `python scripts/self_test_terrain.py` for known-plane, strict threshold, missing-data, holes, disjoint parts, boundary extent and unit checks. A real-site replay against saved evidence verifies integration and reproducibility; it is not an independent ground survey.
