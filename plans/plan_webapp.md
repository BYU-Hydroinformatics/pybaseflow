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

---

## Prerequisite: drop numba entirely (shipped in 0.2.1)

Benchmarks on realistic daily series showed numba wasn't paying for itself:

- The slowest methods (`part`, `bflow`) are pure numpy and got zero speedup.
- Methods numba did help (`fixed`, `local`, `ukih`) were already sub-millisecond at 20-year scale.
- Cold-start JIT compile cost ~1.5s (first `fixed`: 1028 ms, first `local`: 345 ms, first `ukih`: 106 ms) — bad for Streamlit cold wakes and Pyodide.
- Removing numba trimmed `import baseflowx` from 814 ms to 340 ms and left steady-state totals within ~30 ms at 20-year scale.

So instead of an optional `[speed]` extra (which would over-promise), numba was removed: `@njit` decorators stripped, `prange` → `range`, `numba` dropped from `pyproject.toml`. Shipped as `baseflowx 0.2.1`.

---

## UI sketch

Sidebar:
- Gage selector: text input for site ID **plus** a dropdown of ~10 curated gages with known-interesting baseflow behavior (e.g. one spring-fed, one flashy, one snowmelt-dominated). BN77 from the docs example should be in there.
- Date range picker (default: last 5 water years).
- Method multi-select (default: all). Expose method-specific params behind an expander.

Main pane:
- Summary card: site name, drainage area, record period, mean Q.
- Hydrograph: log-scale Q on y-axis, one line per selected method + the raw streamflow.
- BFI table: baseflow index per method.
- Download buttons: CSV of all separations, PNG of plot.

## Phases

1. **Rename `pybaseflow` → `baseflowx`** — see `plan_rename.md`. Ship `baseflowx 0.2.0` + deprecation shim `pybaseflow 0.2.0`.
2. **Drop numba** (prerequisite above). Shipped as `baseflowx 0.2.1`.
3. **Scaffold Streamlit app** in a `/webapp` folder of the `baseflowx` repo.
   - `streamlit_app.py`, `requirements.txt` pinning `baseflowx>=0.2.1`.
   - Minimal working version: one gage, one method, one chart.
4. **Fill in methods + params** — wire up the full method set with per-method param controls.
5. **Polish** — curated gage list, site metadata lookup, download buttons, BFI table.
6. **Deploy to Streamlit Cloud** — connect repo, claim `baseflow-explorer.streamlit.app`, add badge in docs.
7. **Link from docs** — "Try it" callout on the docs landing page and each method page.
8. **(Later) Pyodide demo** — embed a lightweight version directly in MkDocs pages so readers can run an example without leaving the docs.

## Open questions

- **Repo layout:** `/webapp` subfolder in `baseflowx` vs. separate `baseflow-explorer` repo. Subfolder keeps the demo in sync with the library and is simpler. Lean toward subfolder.
- **Data fetch library:** `dataretrieval` (official USGS client, friendlier) vs. raw NWIS JSON via `requests` (fewer deps, faster cold start). Lean toward `dataretrieval`.
- **Curated gage list:** which 10? Need a spread of hydrologic regimes to showcase where each method shines or fails. Draft list TBD.
- **Parameter UX:** defaults only, or expose method-specific sliders? Start with defaults, add sliders in phase 4.
