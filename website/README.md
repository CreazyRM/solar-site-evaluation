# Solar Atlas website

Editable source for the Ontario Solar Site Assessment website, exported from the published Sites checkout. See `SOURCE.json` for the source revision. The owner's Site deployment identity and local runtime state are excluded.

## Run without Sites

Install Node.js 22.13 or later, then run:

```sh
git clone https://github.com/CreazyRM/solar-site-evaluation.git
cd solar-site-evaluation/website
node standalone-server.mjs
```

Open http://127.0.0.1:3000/solar/. This entry point needs no npm installation. It serves the existing frontend and the same public-data assessment modules. `npm run dev:standalone` runs the same server. Stop and restart after changing server modules; refresh the browser after changing frontend files.

The repository is private: collaborators need repository access before cloning. Use your own GitHub account; do not share personal access tokens.

`HOST` and `PORT` environment variables configure the listener; the default is local loopback. For example, in PowerShell:

```powershell
$env:PORT = '3001'
node standalone-server.mjs
```

For a Node hosting provider, configure its required host and port. The standalone adapter does not include the Sites access policy, ChatGPT sign-in, rate limits or durable cloud storage. Configure those services separately for a shared deployment. Only `public/` is served as static content.

## Where to edit

| Location | Purpose |
| --- | --- |
| `public/solar/index.html`, `styles.css`, `workflow.js`, `app.js` | Page layout, styling, address search and report interaction |
| `public/solar/banner-editor.js` | Banner defaults and browser-local appearance controls |
| `public/solar/geometry.mjs`, `report-map.mjs` | Polygon selection, parcel intersection and interactive report maps |
| `lib/parcel-discovery.mjs`, `public-data.mjs`, `source-cache.mjs` | Public-source discovery, requests and bounded metadata caching |
| `lib/assessment.mjs` | Public-data screening and explicit skipped indicators |
| `app/api/` | Sites/Vinext API wrappers |
| `standalone-server.mjs` | Framework-independent Node HTTP entry point |
| `public/solar/assets/`, `report-data.js`, `saved-map-layers.json` | Images and dated public example evidence already shipped with the Site |
| `../skills/solar-site-land-soil/` | Separate Python/Codex assessment skill |

VS Code, Cursor and other source-code development tools can edit this repository. Tools supporting a Node backend can run the standalone adapter. A static-only website builder can use the frontend but needs a separately hosted backend for address discovery and live screening. Matching server routes are `GET /api/locate?address=...` (optional `stream=1` and `location=N`) and streaming `POST /api/evaluate` with `{address, geometry, parcel?}`. Streaming responses use newline-delimited JSON; see `workflow.js` for the client contract.

## Current assessment scope

The website currently supports public parcel discovery, study-area geometry and area, and public soil, wetland and municipality queries. It is a partial screening workflow. Raster slope processing, street-level access/line review, Hydro One capacity trials, zoning and operative Official Plan review still require a connected backend/agent service and are explicitly skipped. Copying the code does not automatically run the Codex skill or grant use of anyone's ChatGPT account or quota. AI APIs, if added later, require your own server-side configuration.

Public parcel coverage and service schemas vary across Ontario. The current Bruce County joined-field/address matching limitation, including the Purple Valley test case, remains in this snapshot; this export does not fix that lookup. A geocoder extent is never treated as an ownership boundary. Preserve source dates and uncertainty when modifying assessments.

Banner preferences, saved reports and deletion state are browser-local; they are not a shared team database. Reference maps can make external tile requests. Outside Cloudflare Workers, metadata caching falls back to bounded process memory. Raw assessment archives and personal capstone files are not included; the dated example assets already displayed by the website are included. Keep third-party license notices with vendored code and retain source attribution for evidence assets.

## Verify offline

```sh
node scripts/test-assessment.mjs
node scripts/test-parcel-discovery.mjs
node scripts/test-standalone.mjs
```

These checks cover geometry, saved/mocked source behavior and the standalone HTTP adapter. They do not establish current planning status, fresh grid capacity or live source availability.

## Optional Sites/Vinext development

For the original framework workflow, install dependencies with `npm run install:ci`, then use `npm run dev` (normally port 5173) or `npm run build`. This requires dependency downloads; the standalone workflow above does not. The framework wrapper includes Sites/Cloudflare integration and is distinct from the dependency-free adapter.

See [README.sites.md](README.sites.md) for the retained implementation and framework details. The sanitized `.openai/hosting.json` has no owner project ID. Register a separate Site before publishing your own copy with Sites. The existing owner's live website is unchanged by this GitHub export.

## Refresh the source snapshot

From the repository root:

```sh
python scripts/sync_website.py --source /absolute/path/to/clean/site-checkout
```

The exporter copies tracked files, sanitizes deployment identity, preserves this README and the standalone adapter, and records the source revision. It does not delete stale exported files; review the Git diff for source removals before committing a refresh. Do not point it at a checkout containing credentials or private assessment archives.
