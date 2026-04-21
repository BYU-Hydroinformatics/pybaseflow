# Baseflow Explorer — Web App Plan

## Names

- **Package:** `baseflowx` (renamed from `pybaseflow` — see `plan_rename.md`)
- **Web app:** **Baseflow Explorer**
- **Public URL target:** TBD — depends on host (see Hosting). Candidates: `baseflow-explorer.fly.dev`, `baseflow-explorer.onrender.com`, or a custom subdomain.

Web app name alternates considered: *BaseflowLab*, *HydroSep*, *SepCompare*. Going with Baseflow Explorer — clear to hydrologists and students, hints at the interactive "pick a gage, see what happens" UX.

## Framework decision: Flask + Leaflet, not Streamlit

A Streamlit prototype was built and deployed to `baseflow-explorer.streamlit.app`. The all-method analysis + chart + CSV download work well, but the clickable CONUS gage map never became usable:

- Streamlit reruns the entire Python script on every map interaction, including pan/zoom. The map iframe re-mounts, tiles re-fade, MarkerCluster re-initializes — a visible lag every time the user moves the mouse.
- pydeck's `TileLayer` is silently dropped by Streamlit's component wrapper (verified in network tab — no ArcGIS/OSM tile requests ever leave the browser), so ArcGIS/OSM basemap options couldn't be offered.
- folium via `streamlit-folium` renders tiles but each rerun destroys and rebuilds the iframe, so pan/zoom lag is baked in.

The existing `BYU-Hydroinformatics/baseflow_analyst` repo (Flask + Jinja + Leaflet + leaflet.markercluster served from CDN) demonstrates that a map-heavy app of this kind is snappy and feels right when the map is a real client-side Leaflet page with AJAX endpoints behind it — not a server-rerun Streamlit component.

**Decision:** rewrite Baseflow Explorer as a Flask + Leaflet app, keeping the scope identical to what the Streamlit version already covers (all 10 methods, NWIS fetch, Plotly chart, CSV download). The Streamlit app at `baseflow-explorer.streamlit.app` can be retired or left as a secondary "simple" interface; primary URL and docs links move to the Flask build.

## Goal

A free, public web app that lets anyone:
1. Click a gage on a CONUS map, or type a USGS site ID directly.
2. Pull daily streamflow from NWIS for a chosen date range.
3. Run every separation algorithm in `baseflowx` and plot the results together.
4. Download results as CSV.

The app is a living demo — when `baseflowx` ships a new method on PyPI, a redeploy picks it up automatically.

## Hosting

Needs to support a Python web process (no longer Streamlit-specific), so the original Streamlit Cloud plan is out. Candidate platforms:

- **Fly.io** — generous free tier, Dockerfile-based, WebSocket support, easy `*.fly.dev` subdomain.
- **Render** — free tier for web services, similar `*.onrender.com` subdomain, sleeps after 15 min of inactivity (longer wake than Streamlit Cloud).
- **Hugging Face Spaces (Docker SDK)** — free, no sleep, supports Flask via a Dockerfile.
- **PythonAnywhere** — free tier explicitly supports Flask, never sleeps the app, but single-worker and older Python versions.

Lean toward **Fly.io** — simplest deploy, fast startup, and the free tier covers a demo easily. Fallback to Hugging Face Spaces if Fly's free tier proves noisy.

## Architecture

```
          ┌─────────────── browser ───────────────┐
          │  Leaflet (map + MarkerCluster)        │
          │       │                               │
          │       └── click a gage ──┐            │
          │                          ▼            │
          │                    AJAX: /analyze     │
          └──────────────────────┬────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     Flask application   │
                    │  /                      │ ← renders index.html
                    │  /sites.json            │ ← gage list for map
                    │  /analyze?site_id=&...  │ ← calls baseflowx
                    │  /static/*              │ ← css/js/snapshot
                    └────────────┬────────────┘
                                 │
                     ┌───────────▼───────────┐
                     │ baseflowx + NWIS pull │
                     └───────────────────────┘
```

- **Front end:** single HTML page, Leaflet 1.9 + leaflet.markercluster from CDN, a right-side panel that slides in on gage click. Plotly.js chart rendered client-side from the JSON the analyze endpoint returns.
- **Back end:** Flask app (`app.py`) with three JSON-returning endpoints plus the root page.
- **Data source:** `dataretrieval.nwis.get_dv` called server-side, cached with `functools.lru_cache` keyed by `(site_id, start, end)`. Site list served from a pre-built Parquet snapshot committed under `webapp/data/`.
- **Compute:** in-process call to `baseflowx`. Daily series at 20-year scale runs every method in well under a second (benchmarked in the 0.2.1 refactor).
- **Deploy artifact:** a `Dockerfile` that `pip install -r requirements.txt` and runs `gunicorn app:app`.

## UI sketch

Full-screen Leaflet map as the primary interface. Right-side panel slides in when a gage is clicked.

Map:
- CONUS view on first load. Basemap selector in the top-right corner of the map (Leaflet layers control): OpenStreetMap (default), ArcGIS Topo, ArcGIS Satellite, ArcGIS Terrain, CartoDB Positron. All served as XYZ tiles, no tokens.
- leaflet.markercluster for the 9,500 active gages (snapshot). Individual CircleMarkers at zoom ≥ 9, clusters otherwise.
- Selected gage highlighted with a red outlined marker layered on top of the cluster.

Right panel (slides in on click, hides on × or "back to map"):
- Site header: site ID, station name, drainage area, state.
- Date range picker (default: last 5 water years).
- Method multi-select (default: a sensible 4–5). Parameter sliders in a collapsible section.
- Plotly hydrograph: log-scale Q with one trace per selected method + raw streamflow.
- BFI summary table: baseflow index per method.
- CSV / PNG download buttons.

Top bar: app title, link to docs, link to GitHub.

## Gage map

The CONUS gage list is pre-computed into a Parquet snapshot committed at `webapp/data/nwis_dv_sites.parquet` (already built in the Streamlit prototype, ~500 KB, 9,519 sites). The Flask app serves it via `/sites.json` on first page load; Leaflet consumes the JSON to build the marker cluster.

- **Filter criteria:** active, daily-values, parameter code `00060` (discharge), CONUS bounding box.
- **Snapshot refresh:** regenerated periodically by the same script used to build it initially (`webapp/build_site_snapshot.py`). Not on every deploy.
- **Optional enhancements (later phases):** color markers by mean BFI for a selected method; size markers by drainage area; add a "curated highlights" overlay for known-interesting gages (BN77, plus a spring-fed / flashy / snowmelt-dominated set).

## Phases

Already shipped (Streamlit prototype work, much of it reusable):
- `baseflowx 0.2.1` on PyPI (rename + numba removal).
- Site snapshot Parquet at `webapp/data/nwis_dv_sites.parquet`.
- All separation methods proven to run on live NWIS data from the browser.

Remaining phases for the Flask rewrite:

1. **Scaffold Flask app** in `webapp/` (replacing the Streamlit files).
   - `app.py` with `/`, `/sites.json`, `/analyze` endpoints.
   - `templates/index.html` with Leaflet + cluster plugin.
   - `static/js/app.js` for map + analyze panel; `static/css/app.css` for styling.
   - `Dockerfile` + updated `requirements.txt` (drop `streamlit`, `streamlit-folium`, `folium`; add `flask`, `gunicorn`).
2. **Wire the map** — load snapshot, render cluster, basemap selector, click → open panel, highlight selected marker.
3. **Wire the analysis panel** — date range + method picker + parameter sliders, AJAX to `/analyze`, render Plotly, render BFI table, CSV download.
4. **Polish** — site metadata display, PNG download of the chart, responsive layout, loading states.
5. **Deploy to Fly.io** — `flyctl launch`, claim the app URL, set up auto-deploy on `git push` (or GH Action). Delete the old Streamlit Cloud app.
6. **Link from docs** — "Try it" badge/callout on the docs landing page and each method page, pointing at the new URL.
7. **(Later) Pyodide demo** — embed a trimmed baseflowx run directly in MkDocs pages so readers can run an example without leaving the docs.

## What to do with the existing Streamlit app

The Streamlit version at `baseflow-explorer.streamlit.app` is functional for the non-map parts. Options:

- **Retire it** after the Flask app is live and the docs link has been repointed. Simplest.
- **Leave it up as-is** with a banner linking to the Flask version. Low effort, some redundancy.
- **Use it for a different purpose** — e.g., a stripped-down single-gage "paste a site ID, see the chart" flow where a clickable map isn't needed.

Lean toward retire once the Flask app is live. The subdomain stays reserved on the Streamlit Cloud account in case we want it later.

## Open questions

- **Repo layout:** `/webapp` subfolder in `baseflowx` (keeps library and demo in sync, what we have now) vs. separate `baseflow-explorer` repo (cleaner deploy story, independent versioning). Lean toward subfolder still.
- **Data fetch library:** `dataretrieval` (official USGS client, friendlier) vs. raw NWIS JSON via `requests` (fewer deps, smaller Docker image). For a Flask app where cold-start size matters less than for Streamlit Cloud, lean toward `dataretrieval`.
- **Snapshot refresh cadence:** manual rebuild when drift becomes obvious vs. scheduled (weekly GH Action). Start manual; revisit if stale gages become an issue.
- **Auth / rate-limits:** none intended, but if Fly's free tier sees abuse, put the `/analyze` endpoint behind a simple per-IP rate limit.
- **Parameter UX:** defaults only, or expose method-specific sliders? Start with defaults + one slider per filter parameter (what the Streamlit version already has); revisit after dogfooding.
