# Baseflow Explorer — Web App Plan

## Names

- **Package:** `baseflowx` (renamed from `pybaseflow` — see `plan_rename.md`)
- **Web app:** **Baseflow Explorer**
- **Public URL target:** `baseflow-explorer.streamlit.app`

Web app name alternates considered: *BaseflowLab*, *HydroSep*, *SepCompare*. Going with Baseflow Explorer — clear to hydrologists and students, hints at the interactive "pick a gage, see what happens" UX.

## Goal

A free, public web app that lets anyone:
1. Enter a USGS stream gage ID (or pick from a short curated list).
2. Pull daily streamflow from NWIS for a chosen date range.
3. Run every separation algorithm in `baseflowx` and plot the results together.
4. Download results as CSV.

The app is a living demo — when `baseflowx` ships a new method on PyPI, a redeploy picks it up automatically.

## Hosting

**Streamlit Community Cloud.** Free, unlimited public apps, auto-redeploys on `git push`, custom `*.streamlit.app` subdomain. Apps sleep after ~7 days idle (30s cold start on wake) — acceptable for a docs-linked demo.

Fallback if sleep becomes a problem: Hugging Face Spaces (Streamlit SDK, no sleep, 16GB RAM free).

## Architecture

```
USGS NWIS  ──dataretrieval──>  Streamlit app  ──baseflowx──>  Plotly chart + CSV
                                      │
                                      └── @st.cache_data on NWIS pulls
```

- **Data source:** `dataretrieval.nwis.get_dv` (daily values service). No API key needed.
- **Compute:** in-process call to `baseflowx`. For daily series (<30 years = ~11k points) every method runs well under a second.
- **Caching:** `@st.cache_data` on the NWIS fetch keyed by `(site_id, start, end)` so the same gage doesn't re-download.
- **Plotting:** Plotly (interactive zoom/pan matters for hydrographs) over Matplotlib.

## UI sketch

Landing view is a map. Once a gage is picked (from the map or by site ID), the hydrograph + method controls take over as the main pane.

Sidebar:
- Gage selector: text input for site ID as a fallback/power-user path (the map is the primary picker).
- Date range picker (default: last 5 water years).
- Method multi-select (default: all). Expose method-specific params behind an expander.

Main pane (after a gage is selected):
- Summary card: site name, drainage area, record period, mean Q.
- Hydrograph: log-scale Q on y-axis, one line per selected method + the raw streamflow.
- BFI table: baseflow index per method.
- Download buttons: CSV of all separations, PNG of plot.

## Gage map

The app opens on a pydeck map of every active USGS daily-values streamflow gage in CONUS (~10k–20k sites). Clicking a marker loads that gage into the analysis view.

- **Data source:** NWIS site-info service via `dataretrieval.nwis.get_info` or the equivalent REST query, filtered to sites with parameter code `00060` (discharge) and an active daily-values record. The full site list changes rarely — pull it once on first cold start and cache aggressively (`@st.cache_data(ttl=7 * 24 * 3600)`); consider pre-computing a Parquet snapshot committed to the repo if NWIS latency hurts cold starts.
- **Rendering:** `pydeck` ScatterplotLayer over Carto basemap. GPU-backed, handles 100k+ points smoothly. No Mapbox token needed for Carto tiles.
- **Interaction:** click a marker → site ID populates, gage data loads automatically. Hover tooltip shows site ID, site name, and drainage area. Map state (pan/zoom) persists across reruns via `st.session_state`.
- **Fallback:** manual site-ID text input still lives in the sidebar for users who know the number they want — bypasses the map entirely.
- **Layer styling:** single-color scatter initially. Later enhancements (phase 5): color by mean BFI for a selected method, or size by drainage area.

## Phases

1. **Scaffold Streamlit app** in a `/webapp` folder of the `baseflowx` repo.
   - `streamlit_app.py`, `requirements.txt` pinning `baseflowx>=0.2.1`.
   - Minimal working version: one gage, one method, one chart.
2. **Fill in methods + params** — wire up the full method set with per-method param controls.
3. **Gage map** — pydeck map of all active CONUS daily-values gages as the landing view; click to load. Keep text-input fallback.
4. **Polish** — site metadata auto-lookup (drainage area from NWIS), richer BFI table, PNG download for the plot.
5. **Deploy to Streamlit Cloud** — connect repo, claim `baseflow-explorer.streamlit.app`, add badge in docs.
6. **Link from docs** — "Try it" callout on the docs landing page and each method page.
7. **(Later) Pyodide demo** — embed a lightweight version directly in MkDocs pages so readers can run an example without leaving the docs.

## Open questions

- **Repo layout:** `/webapp` subfolder in `baseflowx` vs. separate `baseflow-explorer` repo. Subfolder keeps the demo in sync with the library and is simpler. Lean toward subfolder.
- **Data fetch library:** `dataretrieval` (official USGS client, friendlier) vs. raw NWIS JSON via `requests` (fewer deps, faster cold start). Lean toward `dataretrieval`.
- **Gage map snapshot:** fetch NWIS site list at runtime (simple, always fresh) vs. commit a Parquet snapshot to the repo (faster cold starts, occasional stale). Lean toward runtime fetch with a 7-day cache; revisit if cold starts feel slow.
- **Curated highlights:** even with the full map, a handful of "known-interesting" gages (spring-fed, flashy, snowmelt-dominated, plus BN77) should probably be visually emphasized or listed in a "Start here" panel.
- **Parameter UX:** defaults only, or expose method-specific sliders? Start with defaults, add sliders in phase 4.
