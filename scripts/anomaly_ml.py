"""FlareIntel, Piece 2b: ML + temporal anomaly detection.

Layers on Piece 2a (regulation-grounded flags):
  - Isolation Forest: unsupervised multivariate anomaly score over facility features
  - temporal upset-spike detection: months where a facility's flare jumps far above
    its own baseline (non-routine / upset events)
  - intensity-outlier watchlist as a first-class view (punching above weight)
  - a data spot-check on the top venting facility

Framing note: exceeding a Directive 060 threshold means a facility is above the
conservation-REVIEW threshold, not that it is non-compliant (many hold approvals).

Usage: python3 anomaly_ml.py
"""
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

GAS_DENSITY = 0.68
GWP100 = 28
FLARE_CO2E_PER_TCH4 = 0.98 * (44 / 16) + 0.02 * GWP100


def robust_z(s):
    med = s.median()
    mad = (s - med).abs().median()
    return pd.Series(0.0, index=s.index) if (mad == 0 or np.isnan(mad)) else 0.6745 * (s - med) / mad


def main():
    df = pd.read_csv(os.path.join(DATA, "flare_vent_monthly.csv"))
    for c in ["flare", "vent", "gas_prod"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).clip(lower=0)

    fac = (df.groupby(["ReportingFacilityID", "OperatorName", "ReportingFacilityType"])
             .agg(flare=("flare", "sum"), vent=("vent", "sum"), gas_prod=("gas_prod", "sum"),
                  months=("ProductionMonth", "nunique"), flare_std=("flare", "std")).reset_index())
    fac["flare_std"] = fac["flare_std"].fillna(0)
    fac["flare_mean_mo"] = fac["flare"] / fac["months"]
    fac["flare_volatility"] = (fac["flare_std"] / fac["flare_mean_mo"].replace(0, np.nan)).fillna(0)
    # intensity only meaningful for producing facilities (plants/gathering have no PROD -> would be trivially 1.0)
    fac["flare_intensity"] = np.where(fac["gas_prod"] > 0, fac["flare"] / (fac["flare"] + fac["gas_prod"]), np.nan)
    fac["vent_intensity"] = np.where(fac["gas_prod"] > 0, fac["vent"] / (fac["vent"] + fac["gas_prod"]), np.nan)
    fac["co2e_t"] = fac["vent"] * GAS_DENSITY * GWP100 + fac["flare"] * GAS_DENSITY * FLARE_CO2E_PER_TCH4

    # Isolation Forest on facilities that actually flare or vent
    act = fac[(fac["flare"] + fac["vent"]) > 0].copy()
    feats = ["flare", "vent", "gas_prod", "flare_volatility"]  # intensity excluded: invalid for non-producing facilities
    X = act[feats].copy()
    for c in ["flare", "vent", "gas_prod"]:
        X[c] = np.log1p(X[c])
    Xs = StandardScaler().fit_transform(X.fillna(0))
    iso = IsolationForest(n_estimators=300, contamination=0.02, random_state=0)
    iso.fit(Xs)
    act["ml_anomaly"] = -iso.score_samples(Xs)
    fac = fac.merge(act[["ReportingFacilityID", "OperatorName", "ReportingFacilityType", "ml_anomaly"]],
                    on=["ReportingFacilityID", "OperatorName", "ReportingFacilityType"], how="left")

    # temporal upset spikes: per-facility flare vs its own baseline
    fdf = df[df["flare"] > 0].copy()
    fdf["z"] = fdf.groupby("ReportingFacilityID")["flare"].transform(robust_z)
    spikes = fdf[(fdf["z"] > 4) & (fdf["flare"] > 20)].sort_values("flare", ascending=False)

    fac.to_csv(os.path.join(DATA, "facility_scores.csv"), index=False)

    # data spot-check: top venting facility's monthly series
    tvrow = fac.sort_values("vent", ascending=False).iloc[0]
    tv = df[df["ReportingFacilityID"] == tvrow["ReportingFacilityID"]]["vent"]
    print("=== spot-check: top venting facility monthly vent (10^3 m3) ===")
    print(f"{tvrow['OperatorName']} | {tvrow['ReportingFacilityID']} | months={len(tv)} | "
          f"min {tv.min():.1f}  median {tv.median():.1f}  max {tv.max():.1f}  mean {tv.mean():.1f}")

    print("\n=== top 10 ML anomalies (Isolation Forest, multivariate) ===")
    ml = fac.sort_values("ml_anomaly", ascending=False).head(10)
    print(ml[["OperatorName", "ReportingFacilityType", "flare", "vent", "flare_intensity",
              "flare_volatility", "ml_anomaly"]].round(3).to_string(index=False, max_colwidth=30))

    print("\n=== top 10 intensity outliers (share of gas flared, vs same facility type) ===")
    io = fac[(fac["gas_prod"] > 0) & (fac["flare"] > 0)].copy()
    io["z"] = io.groupby("ReportingFacilityType")["flare_intensity"].transform(lambda s: robust_z(np.log1p(s)))
    io = io[io["z"] > 3.5].sort_values("flare_intensity", ascending=False).head(10)
    print(io[["OperatorName", "ReportingFacilityType", "flare", "gas_prod", "flare_intensity",
              "co2e_t"]].round(3).to_string(index=False, max_colwidth=30))

    print("\n=== top 10 temporal upset spikes (flare far above facility's own baseline) ===")
    print(spikes.head(10)[["ProductionMonth", "OperatorName", "ReportingFacilityType", "flare", "z"]]
          .round(2).to_string(index=False, max_colwidth=30))


if __name__ == "__main__":
    main()
