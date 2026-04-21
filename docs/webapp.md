# Baseflow Explorer — Web App

**Baseflow Explorer** is an interactive, map-based web front end for the `baseflowx` library. It lets anyone — no Python install required — pick a USGS stream gage, pull its daily discharge record, and compare every baseflow separation method in the library side by side.

> **Status:** live deployment URL coming soon. The app lives at [`webapp/`](https://github.com/BYU-Hydroinformatics/baseflowx/tree/master/webapp) in the repo; clone the repo and run it locally via `python webapp/app.py` (see [Run locally](#run-locally) below).

## What it does

1. Opens on a zoomable map of every active USGS daily-values streamflow gage in the contiguous US (~9,500 sites, drawn from a pre-built snapshot bundled with the app).
2. Click any marker to load that gage into an analysis panel.
3. Pick a date range, a set of separation methods, and filter parameters. Analysis re-runs automatically on every change.
4. View the streamflow trace and each selected method's baseflow estimate on an interactive Plotly hydrograph.
5. Inspect per-method baseflow index (BFI) values in a summary table.
6. Download the full date × method matrix as CSV.

All ten core separation methods are wired up:

- **Recursive digital filters:** Lyne-Hollick, Eckhardt, Chapman, Chapman-Maxwell, BFlow
- **Graphical / recession-based:** Fixed interval, Sliding interval, Local minimum, UKIH, PART

Tracer methods (CMB) require conductivity data and are not currently exposed in the web app; use the Python library directly for those (see [Tracer-based methods](methods/tracer-methods.md)).

## How it works

```
           ┌──────────── browser ────────────┐
           │  Leaflet map + gage markers     │
           │  Plotly hydrograph              │
           │       │                         │
           │       └─── click + form ────┐   │
           └─────────────────────────────┼───┘
                                         │
                          ┌──────────────▼──────────────┐
                          │   Flask application (app.py) │
                          │    /             (index)    │
                          │    /sites.json   (markers)  │
                          │    /analyze      (baseflow) │
                          └──────────────┬──────────────┘
                                         │
                          ┌──────────────▼──────────────┐
                          │   baseflowx + USGS NWIS API │
                          └─────────────────────────────┘
```

- **Front end:** single HTML page, Leaflet 1.9 for the map (GPU-backed canvas rendering, no marker clustering required at 9,500 points), Plotly for the hydrograph. All map interactions — pan, zoom, click, hover — run purely in the browser with no server round-trip.
- **Back end:** Flask. Three endpoints: `/` (the page), `/sites.json` (the gage snapshot), and `/analyze` (runs the selected `baseflowx` methods against a site's NWIS data and returns the hydrograph + BFI as JSON).
- **Data:** daily streamflow fetched on demand via `dataretrieval.nwis.get_dv`. The NWIS pull is cached per `(site_id, start, end)` tuple so tweaking methods or parameters doesn't re-download.

Because map interactions happen client-side and only analysis requests hit the server, tweaking dates, methods, or parameters updates the chart in a fraction of a second on a warm cache.

## Features

### Map

- Every active CONUS daily-values discharge gage as an individual marker. No clustering.
- Basemap selector: ArcGIS Topo (default), ArcGIS Satellite, ArcGIS Streets, OpenStreetMap, CartoDB Positron.
- Hover a marker for site ID and station name. Click to load the gage.
- Selected gage is highlighted in red, layered over the main marker set.

### Analysis panel

- **Auto-run.** No "run" button; the analysis recomputes 250–500 ms after any form change. Stale responses are suppressed, so rapid changes only render the final result.
- **Per-method parameter dimming.** The filter parameters (Lyne-Hollick β, recession coefficient, Eckhardt BFImax, drainage area) fade to 40 % opacity when no selected method uses them, giving a visual hint of what actually affects the current run.
- **Resizable chart panel.** Drag the seam between the map and the chart to give the hydrograph more room.
- **Fullscreen expand** ⤢ button to push the chart to full viewport height.
- **Linear / log y-axis** toggle for the hydrograph. Linear by default.
- **CSV download.** One row per day, one column per selected method plus raw streamflow.

### Parameters

| Parameter                  | Default | Used by                                   |
|----------------------------|---------|-------------------------------------------|
| Start / end date           | last 5 y| all methods                                |
| Drainage area (km²)        | auto    | Fixed interval, Sliding interval, Local minimum, PART |
| Lyne-Hollick β             | 0.925   | Lyne-Hollick (directly); Local, UKIH (edge fill) |
| Recession coefficient a    | 0.925   | Eckhardt, Chapman, Chapman-Maxwell        |
| Eckhardt BFImax            | 0.80    | Eckhardt                                  |

Drainage area auto-populates from the NWIS site record when you click a marker.

## Run locally

Clone the repo and install the webapp's dependencies:

```bash
git clone https://github.com/BYU-Hydroinformatics/baseflowx.git
cd baseflowx
pip install -r webapp/requirements.txt
python webapp/app.py
```

Open `http://localhost:8080`. The app uses the version of `baseflowx` installed in your environment, so `pip install -e .` in the repo root lets you iterate on the library and see changes in the web app on reload.

## Deployment

The app ships with a `Dockerfile` that runs `gunicorn app:app` on port 8080. That's the artifact for any container host; [Fly.io](https://fly.io) is the current target (`flyctl launch` in `webapp/`). Other supported targets include Hugging Face Spaces (Docker SDK), Render, and any VPS with Docker.

The gage snapshot at `webapp/data/nwis_dv_sites.parquet` is regenerated periodically rather than at deploy time, because the state-by-state NWIS query that builds it takes about 20 seconds. That keeps the app's cold-start fast — the site list is ready in memory the moment the container boots.
