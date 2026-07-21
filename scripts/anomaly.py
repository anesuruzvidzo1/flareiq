"""FlareIntel, Piece 2a: regulation-grounded flare/vent anomaly detection.

Reads data/flare_vent_monthly.csv and builds a facility-level anomaly watchlist that
is NOT a black box. Every flag has a stated reason, grounded in:
  - AER Directive 060 thresholds (routine venting limit; 900 m3/day conservation trigger)
  - peer-relative flaring intensity (routine over-flaring vs same-type facilities)
  - a methane-weighted CO2e severity score (venting is ~7x worse than flaring per m3,
    using the AER's own published factors: see emissions.py)

The ML layer (Isolation Forest, temporal upset spikes) is Piece 2b.

Usage: python3 anomaly.py
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

# --- emissions factors: see emissions.py, derived from the AER's own convention ---
from emissions import co2e_tonnes  # noqa: E402

# --- AER Directive 060 site thresholds ---
VENT_ROUTINE_LIMIT = 3.0               # routine venting limit: 3,000 m3/month = 3 x10^3 m3/month
CONSERVATION_TRIGGER = 0.9 * 30.4      # 900 m3/day combined flare+vent -> ~27.4 x10^3 m3/month


def robust_z(s):
    med = s.median()
    mad = (s - med).abs().median()
    if mad == 0 or np.isnan(mad):
        return pd.Series(0.0, index=s.index)
    return 0.6745 * (s - med) / mad


def main():
    df = pd.read_csv(os.path.join(DATA, "flare_vent_monthly.csv"))
    for c in ["flare", "vent", "gas_prod"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0).clip(lower=0)
    nmonths = df["ProductionMonth"].nunique()

    g = (df.groupby(["ReportingFacilityID", "OperatorName", "ReportingFacilityType"])
           .agg(flare=("flare", "sum"), vent=("vent", "sum"), gas_prod=("gas_prod", "sum"),
                months=("ProductionMonth", "nunique")).reset_index())
    g["avg_flare_mo"] = g["flare"] / g["months"]
    g["avg_vent_mo"] = g["vent"] / g["months"]
    g["avg_fv_mo"] = g["avg_flare_mo"] + g["avg_vent_mo"]
    g["flare_intensity"] = g["flare"] / (g["flare"] + g["gas_prod"]).replace(0, np.nan)
    g["co2e_t"] = co2e_tonnes(g["vent"], g["flare"])

    # Directive 060 regulatory flags (on average monthly rates over active months)
    g["flag_vent_over_limit"] = g["avg_vent_mo"] > VENT_ROUTINE_LIMIT
    g["flag_conservation"] = g["avg_fv_mo"] > CONSERVATION_TRIGGER

    # peer-relative flaring-intensity outlier, WITHIN facility type, producing facilities only
    prod = g[(g["gas_prod"] > 0) & (g["flare"] > 0)].copy()
    prod["z_flare_int"] = prod.groupby("ReportingFacilityType")["flare_intensity"].transform(
        lambda s: robust_z(np.log1p(s)))
    g = g.merge(prod[["ReportingFacilityID", "z_flare_int"]], on="ReportingFacilityID", how="left")
    g["flag_intensity_outlier"] = (g["z_flare_int"] > 3.5).fillna(False)

    def reasons(r):
        out = []
        if r["flag_vent_over_limit"]:
            out.append(f"venting {r['avg_vent_mo']:.1f} above the 3.0/mo review threshold")
        if r["flag_conservation"]:
            out.append(f"flare+vent {r['avg_fv_mo']:.0f} above the 27/mo conservation-review threshold")
        if r["flag_intensity_outlier"]:
            out.append(f"flare intensity {r['flare_intensity']:.0%} (high for facility type)")
        return "; ".join(out)

    g["reason"] = g.apply(reasons, axis=1)
    watch = g[g["reason"] != ""].sort_values("co2e_t", ascending=False)
    watch.to_csv(os.path.join(DATA, "facility_anomalies.csv"), index=False)

    print(f"facilities: {len(g):,} | flagged: {len(watch):,} | months in data: {nmonths}")
    print(f"flags -> vent>limit: {int(g['flag_vent_over_limit'].sum()):,} | "
          f"conservation-trigger: {int(g['flag_conservation'].sum()):,} | "
          f"intensity-outlier: {int(g['flag_intensity_outlier'].sum()):,}")
    print("\ntop 12 anomalous facilities by CO2e (tonnes) over the period:")
    cols = ["OperatorName", "ReportingFacilityType", "co2e_t", "reason"]
    show = watch.head(12)[cols].copy()
    show["co2e_t"] = show["co2e_t"].round(0)
    print(show.to_string(index=False, max_colwidth=46))
    print("\ntop 10 operators by flagged-facility CO2e (tonnes):")
    ops = (watch.groupby("OperatorName")
           .agg(flagged_facilities=("ReportingFacilityID", "nunique"), co2e_t=("co2e_t", "sum"))
           .sort_values("co2e_t", ascending=False).head(10))
    print(ops.round(0).to_string())


if __name__ == "__main__":
    main()
