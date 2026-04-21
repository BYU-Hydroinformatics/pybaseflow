from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st
from dataretrieval import nwis

import baseflowx as bf

SQMI_TO_KM2 = 2.58999
SITES_PATH = Path(__file__).parent / "data" / "nwis_dv_sites.parquet"

st.set_page_config(page_title="Baseflow Explorer", layout="wide")

st.title("Baseflow Explorer")
st.caption(
    "Compare baseflow separation methods from "
    f"[`baseflowx`](https://pypi.org/project/baseflowx/) v{bf.__version__} "
    "on USGS daily streamflow. Click a gage on the map to load it."
)


@st.cache_data(show_spinner=False)
def load_sites() -> pd.DataFrame:
    return pd.read_parquet(SITES_PATH)


@st.cache_data(show_spinner="Fetching USGS NWIS data…")
def fetch_dv(site_id: str, start: date, end: date) -> pd.DataFrame:
    df, _ = nwis.get_dv(
        sites=site_id, start=str(start), end=str(end), parameterCd="00060",
    )
    return df


sites = load_sites()

if "site_id" not in st.session_state:
    st.session_state.site_id = "01013500"
if "area_km2" not in st.session_state:
    row = sites[sites.site_no == st.session_state.site_id]
    if not row.empty and pd.notna(row.iloc[0].drain_area_sqmi):
        st.session_state.area_km2 = float(row.iloc[0].drain_area_sqmi) * SQMI_TO_KM2
    else:
        st.session_state.area_km2 = 500.0

# --- Map ---------------------------------------------------------------

with st.container():
    st.subheader("Pick a gage")

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=sites,
        get_position="[dec_long_va, dec_lat_va]",
        get_radius=2000,
        radius_min_pixels=2,
        radius_max_pixels=10,
        get_fill_color=[30, 144, 255, 180],
        pickable=True,
        auto_highlight=True,
    )
    view_state = pdk.ViewState(latitude=39.5, longitude=-98.5, zoom=3.2)
    tooltip = {
        "html": "<b>{site_no}</b><br/>{station_nm}<br/>Drainage: {drain_area_sqmi} mi²",
        "style": {"backgroundColor": "#222", "color": "#fff"},
    }
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style=None,  # Carto light
    )

    event = st.pydeck_chart(
        deck, on_select="rerun", selection_mode="single-object", height=480,
    )

    picked = None
    if event and getattr(event, "selection", None):
        objs = event.selection.get("objects", {}) if isinstance(event.selection, dict) else {}
        for layer_objs in objs.values():
            if layer_objs:
                picked = layer_objs[0]
                break

    if picked and picked.get("site_no") and picked["site_no"] != st.session_state.site_id:
        st.session_state.site_id = picked["site_no"]
        drain = picked.get("drain_area_sqmi")
        if drain is not None and pd.notna(drain):
            st.session_state.area_km2 = float(drain) * SQMI_TO_KM2
        st.rerun()

# --- Sidebar -----------------------------------------------------------

with st.sidebar:
    st.header("Data")
    st.text_input(
        "USGS site ID",
        key="site_id",
        help="Click a marker on the map, or type an 8-digit site number.",
    )
    today = date.today()
    start = st.date_input("Start", value=date(today.year - 5, 10, 1))
    end = st.date_input("End", value=today)
    st.number_input(
        "Drainage area (km²)",
        min_value=1.0,
        key="area_km2",
        help="Used by HYSEP (fixed/slide/local) and PART. Auto-filled from NWIS when a gage is clicked.",
    )

    st.header("Methods")
    all_methods = [
        "Lyne-Hollick", "Eckhardt", "Chapman", "Chapman-Maxwell", "BFlow",
        "Fixed interval", "Sliding interval", "Local minimum", "UKIH", "PART",
    ]
    selected = st.multiselect(
        "Select methods",
        options=all_methods,
        default=["Lyne-Hollick", "Eckhardt", "Chapman-Maxwell", "UKIH", "PART"],
    )

    with st.expander("Parameters"):
        beta = st.slider("Lyne-Hollick β", 0.50, 0.99, 0.925, 0.005)
        a = st.slider("Recession coefficient a", 0.50, 0.999, 0.925, 0.005)
        bfi_max = st.slider("Eckhardt BFImax", 0.10, 0.95, 0.80, 0.05)

site_id = st.session_state.site_id
area_km2 = st.session_state.area_km2

# --- Analysis ----------------------------------------------------------

site_row = sites[sites.site_no == site_id]
site_name = site_row.iloc[0].station_nm if not site_row.empty else "(unknown)"

st.subheader(f"Analysis — {site_id}  ·  {site_name}")

if start >= end:
    st.error("End date must be after start date.")
    st.stop()

try:
    df = fetch_dv(site_id, start, end)
except Exception as e:
    st.error(f"Failed to fetch NWIS data for site `{site_id}`: {e}")
    st.stop()

if df is None or df.empty:
    st.warning("No daily-values data for this gage over the selected date range.")
    st.stop()

q_col = next(
    (c for c in df.columns if c.startswith("00060") and "Mean" in c and "cd" not in c),
    None,
)
if q_col is None:
    st.error(f"No daily discharge column found. Columns: {list(df.columns)}")
    st.stop()

Q_raw = df[q_col].astype(float).to_numpy()
dates = df.index.to_pydatetime() if hasattr(df.index, "to_pydatetime") else df.index
mask = np.isfinite(Q_raw) & (Q_raw > 0)
Q = Q_raw[mask]
dates = np.asarray(dates)[mask]

if len(Q) < 30:
    st.warning(f"Only {len(Q)} valid data points — results may not be meaningful.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Valid days", f"{len(Q):,}")
c2.metric("Mean Q", f"{np.mean(Q):,.1f} ft³/s")
c3.metric("Median Q", f"{np.median(Q):,.1f} ft³/s")
c4.metric("Drainage", f"{area_km2:,.0f} km²")

b_lh = bf.lh(Q, beta=beta)

runners = {
    "Lyne-Hollick":     lambda: bf.lh(Q, beta=beta),
    "Eckhardt":         lambda: bf.eckhardt(Q, a=a, BFImax=bfi_max),
    "Chapman":          lambda: bf.chapman(Q, a=a),
    "Chapman-Maxwell":  lambda: bf.chapman_maxwell(Q, a=a),
    "BFlow":            lambda: bf.bflow(Q)["baseflow"],
    "Fixed interval":   lambda: bf.fixed(Q, area=area_km2),
    "Sliding interval": lambda: bf.slide(Q, area=area_km2),
    "Local minimum":    lambda: bf.local(Q, b_lh, area=area_km2),
    "UKIH":             lambda: bf.ukih(Q, b_lh),
    "PART":             lambda: bf.part(Q, area=area_km2),
}

results: dict[str, np.ndarray] = {}
for name in selected:
    try:
        results[name] = np.asarray(runners[name]())[: len(Q)]
    except Exception as e:
        st.warning(f"{name} failed: {e}")

if not results:
    st.info("Pick at least one method in the sidebar to see separations.")
    st.stop()

fig = go.Figure()
fig.add_trace(
    go.Scatter(x=dates, y=Q, name="Streamflow", line=dict(color="black", width=1))
)
for name, b in results.items():
    fig.add_trace(go.Scatter(x=dates, y=b, name=name, line=dict(width=1.5)))
fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Discharge (ft³/s, log scale)",
    yaxis_type="log",
    height=550,
    legend=dict(orientation="h", yanchor="bottom", y=-0.25),
    margin=dict(l=40, r=20, t=20, b=20),
)
st.plotly_chart(fig, use_container_width=True)

total_q = float(np.sum(Q))
bfi_df = pd.DataFrame(
    {
        "Method": list(results.keys()),
        "BFI": [float(np.sum(b) / total_q) for b in results.values()],
        "Mean baseflow (ft³/s)": [float(np.mean(b)) for b in results.values()],
    }
)
st.subheader("Baseflow Index")
st.dataframe(
    bfi_df.style.format({"BFI": "{:.3f}", "Mean baseflow (ft³/s)": "{:,.1f}"}),
    hide_index=True,
    use_container_width=True,
)

out = pd.DataFrame({"date": dates, "Q_cfs": Q})
for name, b in results.items():
    out[name] = b
st.download_button(
    "Download separations as CSV",
    out.to_csv(index=False),
    file_name=f"{site_id}_baseflow.csv",
    mime="text/csv",
)
