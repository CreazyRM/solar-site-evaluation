# Solar Atlas

This Site provides an Ontario study-area editor and a live, partial public-data screening workflow. It does not run the local Python/Codex multi-agent skill: a deployed agent/raster backend is still required for the skipped sections.

## Assessment application

- Banner appearance: `public/solar/banner-editor.js` contains the published title and position defaults. The homepage's **Adjust banner** panel previews title text, horizontal/vertical position, size, full-photo overlay and photo framing. **Save in this browser** writes validated local preferences; it does not publish shared changes. **Copy settings** copies a JSON preset for the site editor; **Reset** removes the browser override.
- UI: `public/solar/index.html`, `styles.css`, `workflow.js`; the original saved case remains separately dated in `report-data.js`.
- Routes: `GET /api/locate?address=...` (JSON) or `&stream=1` (progress NDJSON), optional `&location=N` for an ambiguous government address candidate; streaming `POST /api/evaluate` accepts `{address, geometry, parcel?}`. Discovery runs on the Site server with bounded public-source requests.
- Shared geometry: `public/solar/geometry.mjs`. Draw a polygon by clicking consecutive line-segment vertices. The browser and API intersect it with the matched parcel using pinned MIT polygon-clipping 0.15.7. Polygon holes and disconnected results are preserved. Empty intersections are rejected; original parcel data is unchanged. Selected area is an authalic-sphere estimate, not title acreage.
- Interactive report maps: `public/solar/report-map.mjs`. Saved evidence layers use `saved-map-layers.json` and georeferenced assets; the saved UTM slope grid was reprojected to EPSG:3857 for display without changing report statistics. Saved imagery remains dated. New reports provide street/satellite basemaps, separate study/parcel outlines and optional live Ontario soil/wetland reference tiles. Layer display does not update report findings.
- Province-wide parcel discovery: `lib/parcel-discovery.mjs` locates the address with NRCan, verifies the municipality against Ontario's municipal polygons, consults the official province-wide website directory (`lib/municipal-directory.json`, 441 imported records), and discovers public ArcGIS catalogue items and service directories. This is one generic workflow, not a maintained adapter for every municipality. Grey/Bruce remain validated source hints, not a coverage restriction. New address searches refresh sources; the separately opened Highway 6 example remains historical.
- Before querying a discovered layer, corroborate its publisher through an official municipal domain or a reciprocal official-site/GIS-organization link. Require polygon geometry and anonymous Query capability. A geocoder bounding box is only a search window and never a parcel boundary. If an interpolated address point falls on a road, actual service polygons within 35 m may be offered as explicitly unconfirmed nearby candidates. The user chooses and confirms the parcel.
- Source caching: `lib/source-cache.mjs` keeps validated service metadata for up to seven days in the Worker Cache API, with bounded per-worker memory as fallback. Caches are best-effort and may differ by server location; they are not a permanent registry database. Every reuse revalidates metadata and queries current geometry. Addresses and parcel results are not cached. Source timestamps, publisher checks, address-match status and discovery evidence accompany the chosen parcel in the report JSON.
- Discovery limits: 46 outbound requests and a 40-second starting deadline per lookup; a timeout receives at most one retry. Login failures, host errors, unavailable polygons and unverified publishers are reported separately. No credentials or paid sources are used. Missing public parcels fall back to user-defined study areas. AI source-review execution is not connected; the API returns a clearly marked `ai_fallback` handoff instead of claiming an agent ran. Public availability varies by jurisdiction and is not guaranteed across Ontario.
- Live queries: Ontario agricultural soil capability, mapped wetland intersections and municipality. Intersections do not establish clipped soil-class acreage or regulatory buffers.
- Unassessed: full-parcel slope, truck access, electrical phases, connection route, actual Hydro One capacity trials and operative zoning/Official Plan interpretation. These are explicitly skipped; no AI credentials or external agent service is configured.
- Original parcel geometry and the selected study geometry are stored separately in each report. A geometry SHA-256 identifies the study area. Editing invalidates displayed results and confirmation; results from an obsolete in-flight geometry are discarded.
- Reports are held in browser memory and can be downloaded as JSON or printed. There is no persistent job queue or report database.
- GeoWarehouse is excluded. No login, paid source, utility contact or application is performed. Timeouts receive at most one retry.

Run `node scripts/test-assessment.mjs` for deterministic clipping, multipart, hole, area, server-consistency and source-failure checks. Run `node scripts/test-parcel-discovery.mjs` for offline publisher verification, cache revalidation, authentication skip, untrusted-source rejection and address-matching fixtures. Public-source fetches can be unavailable independently of application health.

## Framework

A clean full-stack starter running on [vinext](https://github.com/cloudflare/vinext), with optional Cloudflare D1 and Drizzle support.

## Prerequisites

- Node.js `>=22.13.0`
- Portable: Windows, macOS, or Linux; no Bash required
- Managed Linux: managed Linux runtime with Bash, `flock`, `curl`, `sha256sum`, and GNU `timeout`
- Git and `tar` (including Windows `tar.exe`) are required for publishing; portable publication does not require Bash

## Sites Lifecycle

The Sites initializer copies the shared starter and selects managed-linux only when `SITES_MANAGED_LINUX_CONTAINER=1`; otherwise it selects portable. It saves the selection only in ignored `.sites-runtime/execution-profile.json`. Both profiles copy/configure first, then use the plugin's separate `install-dependencies.mjs` step to measure installation independently. Edit source under `app/` and follow the Sites skill for installation, preview, builds, and publishing.

Run `node <plugin-root>/scripts/configure-execution-profile.mjs` only when the profile is unknown for the current checkout and environment. Profile changes do not alter tracked source or require reinstalling otherwise-valid dependencies; restart an existing preview to use the new selection. Do not commit or upload `.sites-runtime/`.

This starter does not use `wrangler.jsonc`.

Publish archives outside the source checkout or under its ignored `outputs/` directory. Local `.env*`, `.dev.vars*`, TypeScript build state, and tool runtime directories are ignored; keep the hosting manifest, migrations, and authored scripts in source control.

`install:ci` runs `npm ci` once against the shared lockfile, disables parent-workspace discovery, and includes required dev/optional dependencies despite production/omit settings. Sharp defaults to prebuilt binaries unless explicitly configured otherwise. Do not overlap installers.

- **Portable:** Preserve host HOME, npm cache, registry, proxy, temporary paths, retry/concurrency settings, and lifecycle-script policy. Use `--prefer-offline --no-audit --no-fund`.
- **Managed Linux:** Use the existing project-local HOME/cache/tmp setup and Linux install lock, tarball preflight, and timeout. Restore the image-seeded npm cache only when its lockfile hash matches; retain network fallback. Builds keep their existing timeout. These helpers are not invoked by the portable profile.

`scripts/sites-env.mjs` preserves the caller's HOME, npm cache, proxy, XDG, and temporary-directory configuration while defaulting Wrangler and Miniflare state to the checkout. If npm reports an unwritable cache, select a writable path with `npm_config_cache` for that install. The `dev` and `start` scripts also keep Wrangler logs inside the checkout. Generated `.sites-runtime/` and `.wrangler/` directories are disposable and ignored by Git.

On portable, `npm run dev` uses `vinext dev` with HMR, starting at port 5173. Vinext records the running server in ignored `.vinext/` state, rejects an ordinary duplicate launch, and recovers stale state after a stopped process; exactly simultaneous starts can race. Pass `--port <port>` or `--hostname <host>` after `npm run dev --` when needed; keep portable previews on loopback.

For managed Linux browser QA, follow the Sites skill's managed preview reference. The daemon runs the project's Vite dev script with `--host 0.0.0.0 --port 4173 --strictPort`; use the CLI's returned URL. The ignored local profile survives the daemon's cleared environment.

The portable profile simulates ChatGPT sign-in only for loopback development requests. Visit `/signin-with-chatgpt?return_to=/` to sign in as `local_seedy` (`seedy@sites.test`, display name `Seedy`) and `/signout-with-chatgpt?return_to=/` to sign out. The development cookie preserves that identity across server restarts. Mock auth is disabled in the managed-linux profile and is not included in production builds; hosted authentication remains dispatch-owned.

The Worker uses `vinext/server/fetch-handler`, including Vinext's config-aware image handling. After building, `npm start` runs that Worker locally through Wrangler on `127.0.0.1`, sharing `.wrangler/state` with dev preview and local D1 migrations; it does not deploy the site or simulate sign-in. Use the URL printed by the server. Pass `npm start -- --port <port>` to select a different built-preview port.

Local previews use Miniflare's placeholder `Request.cf` metadata without a network lookup. Set `CLOUDFLARE_CF_FETCH_ENABLED=true` to opt into fetching preview metadata; this setting does not change hosted request metadata.

Local tool usage metrics are disabled by default. Set `WRANGLER_SEND_METRICS=true` to opt in.

## Included Shape

- edit site code under `app/`
- `app/chatgpt-auth.ts` provides optional dispatch-owned ChatGPT sign-in helpers
- `.openai/hosting.json` declares optional Sites D1 and R2 bindings
- `vite.config.ts` simulates declared bindings for local development
- `worker/index.ts` is the production Worker entrypoint and preserves request-scoped connector bindings
- `scripts/vite/` contains the maintained Vite integrations and the vendored Sites plugin license
- `scripts/connector-preview/` contains the local connector preview Worker and session helpers
- the remaining `scripts/` files select execution profiles and run installation, development, and builds; the plugin's helpers orchestrate the Sites lifecycle
- `dist/` contains generated deployment output; `.vinext/`, `.wrangler/`, and `.sites-runtime/` contain ignored local tool state
- `db/index.ts` reads the D1 binding from the Cloudflare Worker environment
- `db/schema.ts` starts intentionally empty
- `@cloudflare/workers-types` provides Worker types; `cloudflare-env.d.ts` declares optional `DB`/`BUCKET` bindings—update these declarations if binding names change
- `examples/d1/` contains an optional D1 example surface
- `drizzle.config.ts` supports local migration generation when needed

## Workspace Auth Headers

Signed-in visitors receive both `oai-authenticated-user-id` and `oai-authenticated-user-email`. Private Sites require every visitor to sign in; public Sites may also have anonymous visitors, for whom neither header is present.

The user ID is stable for the same user on the same Site and different across Sites. Use it as the durable user key; use email and name for display or contact purposes.

SIWC-authenticated workspace sites may also receive `oai-authenticated-user-full-name` when the user's SIWC profile has a non-empty `name` claim. The full-name value is percent-encoded UTF-8 and is accompanied by `oai-authenticated-user-full-name-encoding: percent-encoded-utf-8`.

Treat the full name as optional and fall back to email when it is absent:

```tsx
import { headers } from "next/headers";

export default async function Home() {
  const requestHeaders = await headers();
  const userId = requestHeaders.get("oai-authenticated-user-id");
  const email = requestHeaders.get("oai-authenticated-user-email");
  const encodedFullName = requestHeaders.get("oai-authenticated-user-full-name");
  const fullName =
    encodedFullName &&
    requestHeaders.get("oai-authenticated-user-full-name-encoding") ===
      "percent-encoded-utf-8"
      ? decodeURIComponent(encodedFullName)
      : null;

  const displayName = fullName ?? email;
  // ...
}
```

## Optional Dispatch-Owned ChatGPT Sign-In

Import the ready-to-use helpers from `app/chatgpt-auth.ts` when the site needs optional or required ChatGPT sign-in:

- Use `getChatGPTUser()` for optional signed-in UI.
- Use the returned `userId` as the stable user key for user-owned records; do not use email as a durable identifier.
- Use `requireChatGPTUser(returnTo)` for server-rendered pages that should send anonymous visitors through Sign in with ChatGPT.
- In a Server Component, start sign-in with `<a href={chatGPTSignInPath(returnTo)} target="_top">`. The auth helper module is server-only; do not import it into a Client Component.
- Do not use `fetch`, XHR, a client-side router, or a framework link that can prefetch the sign-in route. SIWC must start as a top-level navigation.
- Never request the AuthAPI authorization endpoint directly. The dispatch-owned `/signin-with-chatgpt` route must start the SIWC flow.
- Use `chatGPTSignOutPath(returnTo)` for browser sign-out links or actions.
- Pass a same-origin relative `returnTo` path for the destination after sign-in or sign-out. The helper validates and safely encodes it.
- Mark protected pages with `export const dynamic = "force-dynamic"` because they depend on per-request identity headers.

Dispatch owns `/signin-with-chatgpt`, `/signout-with-chatgpt`, `/callback`, the OAuth cookies, and identity header injection. Do not implement app routes for those reserved paths. Routes that do not import and call the helper remain anonymous-compatible.

SIWC establishes identity only; it does not prove workspace membership. Use the Sites hosting platform's access policy controls for workspace-wide restrictions, or enforce explicit server-side membership or allowlist checks.

Use SIWC for account pages, user-specific dashboards, saved records, and write actions tied to the current ChatGPT user. Leave public content anonymous.

## Local D1 migrations

For a D1-backed local preview, generate SQL with `npm run db:generate`. Build once through the Sites skill's build entrypoint (or `npm run build` for standalone use) to generate `dist/server/wrangler.json`, rebuilding if bindings change. From the project root, apply each pending migration in order:

```sh
node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0000_example.sql
```

Replace the filename with the pending migration and `DB` with your D1 binding name if different. Use `.wrangler/state`, not `.wrangler/state/v3`; Wrangler adds the versioned directories. Do not replay migrations already applied locally. This updates only the preview database; publishing applies production migrations separately.

## Diagnostic Commands

- `npm run install:ci`: perform the one locked dependency install
- `npm run dev`: start the Vite/Vinext development server
- `npm run build`: build the deployable Sites artifact
- `npm run start`: preview the built Worker locally with D1/R2 support
- `npm run db:generate`: generate Drizzle migrations after schema changes

When using the Sites plugin, follow its skill instructions for installation, builds, and publishing. These npm commands remain available for standalone use.

The portable build runs Vinext directly without a host `timeout` command. The managed-linux build uses `scripts/build-verified.sh` and its existing `SITES_BUILD_TIMEOUT` setting.

## Learn More

- [vinext Documentation](https://github.com/cloudflare/vinext)
- [Drizzle D1 Guide](https://orm.drizzle.team/docs/get-started/d1-new)
