# Working with USGS Streamflow Data

baseflowx integrates directly with the USGS National Water Information System (NWIS) through the `fetch_usgs()` function in the `baseflowx.io` module, allowing you to retrieve daily streamflow and water-quality data without leaving your Python environment. This guide covers the NWIS API interface, parameter codes, data handling, and a complete worked example.

## The NWIS daily values service

The USGS operates the National Water Information System, which archives hydrological data from thousands of stream gauges across the United States. The NWIS daily values (DV) web service provides programmatic access to these records via a REST API that returns JSON-formatted time series. baseflowx wraps this API in the `fetch_usgs()` function, handling URL construction, HTTP requests, JSON parsing, and missing-value encoding so that you receive clean NumPy arrays ready for analysis.

Each parameter in NWIS is identified by a five-digit numeric code. The two codes most relevant to baseflow separation are:

| Parameter | NWIS code | Description |
|:---|:---:|:---|
| Discharge | `00060` | Daily mean streamflow (ft\(^3\)/s) |
| Specific conductance | `00095` | Daily mean SC (\(\mu\)S/cm at 25 \(^\circ\)C) |

You do not need to memorize these codes. The `fetch_usgs()` function accepts human-readable convenience names -- `'discharge'`, `'streamflow'`, `'sc'`, or `'specific_conductance'` -- and maps them internally. You can also pass the raw numeric code if you need a parameter not covered by the built-in aliases.

## Fetching data

The function signature requires a USGS site number, a start date, and an end date. Site numbers are strings (they often have leading zeros) and dates are formatted as `'YYYY-MM-DD'`.

```python
from baseflowx.io import fetch_usgs

# Fetch daily discharge for Fish River near Fort Kent, Maine
data = fetch_usgs('01013500', '2019-01-01', '2020-12-31', parameter='discharge')
```

The returned dictionary has the following structure:

```python
{
    'dates':      np.array([...]),   # array of datetime.date objects
    'values':     np.array([...]),   # float64 array of measurements (NaN for missing)
    'units':      'ft3/s',           # unit string from NWIS
    'site_id':    '01013500',        # echoed site number
    'parameter':  '00060',           # resolved NWIS parameter code
    'qualifiers': [[...], ...],      # per-timestep qualifier strings from NWIS
}
```

The `values` array is the primary output. It contains `np.float64` values with `np.nan` at any timestep where NWIS reported missing data (encoded as `-999999` or an empty string in the raw API response). The `dates` array contains Python `datetime.date` objects aligned one-to-one with the values.

The `qualifiers` field preserves the NWIS data-quality flags for each timestep. Common qualifiers include `'A'` (approved for publication), `'P'` (provisional, subject to revision), and `'e'` (estimated). These can be useful for flagging periods of reduced data reliability, though for most baseflow separation workflows the qualifiers can be safely ignored.

## Fetching specific conductance

To retrieve specific conductance for the CMB tracer method, simply change the `parameter` argument:

```python
sc_data = fetch_usgs('01013500', '2019-01-01', '2020-12-31', parameter='sc')
SC = sc_data['values']
```

Not all USGS sites have continuous SC records. If no data are available for the requested site, parameter, and date range, `fetch_usgs()` raises a `ValueError` with a descriptive message. You can check data availability for a site on the [NWIS web interface](https://waterdata.usgs.gov/nwis) before attempting a programmatic fetch.

## Handling missing data

Real-world streamflow records frequently contain gaps due to equipment malfunction, ice-affected periods, or other causes. baseflowx's separation functions generally handle NaN values gracefully -- they propagate through arithmetic operations without corrupting adjacent values -- but extended gaps can affect filter initialization and the quality of the separated baseflow in the vicinity of the gap.

For short gaps (a few days), the simplest approach is often to interpolate before running the separation:

```python
import numpy as np

Q = data['values'].copy()
nans = np.isnan(Q)
if nans.any():
    x = np.arange(len(Q))
    Q[nans] = np.interp(x[nans], x[~nans], Q[~nans])
```

For longer gaps, it may be preferable to split the record into continuous segments and process each one independently, since interpolating across weeks or months of missing data introduces substantial artificial signal.

## Bundled sample data

For quick experimentation and reproducible examples, baseflowx ships with a bundled dataset from USGS site 01013500 (Fish River near Fort Kent, Maine) covering 2019--2020. This dataset is accessible without an internet connection via `load_sample_data()`:

```python
import baseflowx

data = baseflowx.load_sample_data()

# Returns a dict with:
#   'dates'   - numpy array of datetime.date objects
#   'Q'       - numpy array of discharge in ft3/s
#   'site_id' - '01013500'
#   'units'   - 'ft3/s'
```

The Fish River site was chosen because it represents a snowmelt-dominated regime with a strong seasonal cycle, clear baseflow recession periods in late summer and autumn, and a well-defined spring freshet -- features that exercise the full range of separation methods.

## Complete worked example

The following example demonstrates the end-to-end workflow: fetching data from NWIS, estimating parameters, running a separation, and computing the baseflow index.

```python
import numpy as np
import baseflowx
from baseflowx.io import fetch_usgs

# Fetch 5 years of daily discharge
data = fetch_usgs('01013500', '2015-01-01', '2020-12-31')
Q = data['values']
dates = data['dates']

# Handle any missing values
nans = np.isnan(Q)
if nans.any():
    x = np.arange(len(Q))
    Q[nans] = np.interp(x[nans], x[~nans], Q[~nans])

# Estimate the recession coefficient
strict = baseflowx.strict_baseflow(Q)
a = baseflowx.recession_coefficient(Q, strict)

# Run the Eckhardt filter with a literature BFImax
b_eck = baseflowx.eckhardt(Q, a, BFImax=0.80)
BFI = np.nansum(b_eck) / np.nansum(Q)
print(f"Recession coefficient: {a:.4f}")
print(f"BFI (Eckhardt, BFImax=0.80): {BFI:.3f}")

# Compare with the Lyne-Hollick 3-pass filter
b_lh = baseflowx.lh_multi(Q, beta=0.925, num_pass=3)
BFI_lh = np.nansum(b_lh) / np.nansum(Q)
print(f"BFI (Lyne-Hollick 3-pass): {BFI_lh:.3f}")

# Run BFlow for recession analysis
from baseflowx.estimate import bflow
result = bflow(Q)
print(f"Alpha factor (SWAT ALPHA_BF): {result['alpha_factor']:.5f}")
print(f"Baseflow days: {result['baseflow_days']:.1f}")
```

If specific conductance data are also available, you can extend this workflow with CMB calibration:

```python
from baseflowx.tracer import calibrate_eckhardt_from_cmb

# Fetch concurrent SC data (may cover a shorter period)
sc_data = fetch_usgs('01013500', '2019-01-01', '2020-12-31', parameter='sc')
SC = sc_data['values']

# Fetch matching Q for the same period
q_data = fetch_usgs('01013500', '2019-01-01', '2020-12-31')
Q_sc = q_data['values']

# Calibrate BFImax from the tracer data
cal = calibrate_eckhardt_from_cmb(Q_sc, SC)
print(f"CMB-calibrated BFImax: {cal['BFImax']:.3f}")
print(f"SC_BF = {cal['SC_BF']:.1f}, SC_RO = {cal['SC_RO']:.1f}")

# Apply calibrated Eckhardt to the full record
b_cal = baseflowx.eckhardt(Q, cal['a'], BFImax=cal['BFImax'])
```

## Error handling

The `fetch_usgs()` function raises two types of exceptions. A `ValueError` is raised if the parameter name is unrecognized (not one of the convenience names and not a valid numeric code) or if no data are returned for the given site, parameter, and date range. A `ConnectionError` is raised if the HTTP request to the NWIS API fails, which can happen due to network issues, NWIS server downtime, or request timeouts (the default timeout is 60 seconds). In production workflows, wrapping the fetch in a try/except block is recommended:

```python
try:
    data = fetch_usgs('01013500', '2015-01-01', '2020-12-31')
except ConnectionError as e:
    print(f"Could not reach NWIS: {e}")
except ValueError as e:
    print(f"Data issue: {e}")
```
