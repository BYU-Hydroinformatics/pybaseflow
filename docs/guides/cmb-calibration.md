# CMB Calibration Bridge

One of the most common challenges in baseflow separation is choosing appropriate parameters for recursive digital filters. The Eckhardt filter, for instance, requires a maximum baseflow index (BFImax) that is difficult to determine from streamflow data alone. The Conductivity Mass Balance (CMB) method offers a physically grounded alternative when specific conductance data is available, and baseflowx provides a direct calibration bridge between the two approaches.

## The Calibration Workflow

The idea is straightforward. If you have a period — even a relatively short one — where both streamflow and specific conductance were measured concurrently, you can use CMB to estimate a reference baseflow index. That reference BFI then serves as the BFImax parameter for the Eckhardt filter, which can be applied to the full streamflow record regardless of whether conductance data is available.

This workflow is well-established in the literature (Stewart et al., 2007; Zhang et al., 2021) and proceeds in three steps.

**Step 1.** Run CMB on the period with paired Q and SC data to obtain a reference baseflow time series.

**Step 2.** Compute the baseflow index from the CMB result: \(BFI_{CMB} = \sum b_{CMB} / \sum Q\).

**Step 3.** Use \(BFI_{CMB}\) as the BFImax parameter in the Eckhardt filter, applied to the full discharge record.

## Using `calibrate_eckhardt_from_cmb()`

baseflowx wraps this entire workflow into a single convenience function:

```python
from baseflowx.tracer import calibrate_eckhardt_from_cmb
import baseflowx

# Assume Q and SC are concurrent numpy arrays
cal = calibrate_eckhardt_from_cmb(Q, SC)

# The result contains everything you need
print(f"Calibrated BFImax: {cal['BFImax']:.3f}")
print(f"Recession coefficient: {cal['a']:.4f}")
print(f"SC_BF used: {cal['SC_BF']:.1f} uS/cm")
print(f"SC_RO used: {cal['SC_RO']:.1f} uS/cm")

# Apply calibrated Eckhardt to any streamflow record
b = baseflowx.eckhardt(Q_full_record, cal['a'], cal['BFImax'])
```

If you do not provide a recession coefficient, the function estimates one automatically from the streamflow using `strict_baseflow()` and `recession_coefficient()`. You can also supply your own end-member conductivities if you have independent estimates from well sampling or other sources:

```python
cal = calibrate_eckhardt_from_cmb(Q, SC, a=0.98, SC_BF=350, SC_RO=40)
```

## Step-by-Step Manual Approach

For more control over the process, you can run each step individually:

```python
from baseflowx.tracer import cmb, estimate_endmembers
from baseflowx.separation import strict_baseflow
from baseflowx.estimate import recession_coefficient
import baseflowx
import numpy as np

# 1. Estimate end-members from SC data
SC_BF, SC_RO = estimate_endmembers(SC, bf_percentile=99, ro_percentile=1)
print(f"End-members: SC_BF={SC_BF:.1f}, SC_RO={SC_RO:.1f}")

# 2. Run CMB separation
b_cmb = cmb(Q, SC, SC_BF=SC_BF, SC_RO=SC_RO)

# 3. Compute reference BFI
valid = np.isfinite(b_cmb) & (Q > 0)
BFI_ref = np.sum(b_cmb[valid]) / np.sum(Q[valid])
print(f"CMB reference BFI: {BFI_ref:.3f}")

# 4. Estimate recession coefficient
strict = strict_baseflow(Q)
a = recession_coefficient(Q, strict)

# 5. Apply calibrated Eckhardt
b_eck = baseflowx.eckhardt(Q, a, BFImax=BFI_ref)
```

## Caveats

Zhang et al. (2021) found that while cumulative baseflow from a CMB-calibrated Eckhardt filter matches CMB well at the annual scale (NSE 0.91–1.00), the daily baseflow series can be quite different (mean NSE of −0.30 across 26 stations). This suggests that CMB and digital filters may be measuring fundamentally different quantities at short timescales — CMB separates water by its geochemical origin, while filters separate by hydrograph shape.

In practice, this means the calibration bridge is most reliable for long-term water balance questions (mean annual baseflow, recharge estimation) rather than daily hydrograph reconstruction. For applications requiring accurate daily baseflow dynamics, consider using the CMB result directly where conductance data is available, and treat the Eckhardt extension as an approximation for periods without SC data.

## References

Stewart, M.T., Cimino, J. and Ross, M. (2007) Calibration of base flow separation methods with streamflow conductivity. *Groundwater* 45(1), 17–27.

Zhang, J. et al. (2021) Can the two-parameter recursive digital filter really be calibrated by the conductivity mass balance method? *HESS* 25, 1747–1760.

Eckhardt, K. (2005) How to construct recursive digital filters for baseflow separation. *Hydrological Processes* 19, 507–515.
