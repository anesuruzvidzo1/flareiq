"""FlareIQ, Piece 3c support: precompute dashboard summary JSON.

Province-wide KPIs, the flaring-up / venting-down trend, and the top operators by
CO2e, written to web/public/data/summary.json so the dashboard renders instantly.

Usage: python3 summary.py
"""
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
WEB = os.path.join(HERE, "..", "web", "public", "data")

GAS_DENSITY = 0.68
GWP100 = 28
FLARE_CO2E = 0.98 * (44 / 16) + 0.02 * GWP100


def main():
    df = pd.read_csv(os.path.join(DATA, "flare_vent_monthly.csv"))
    for c in ["flare", "vent", "gas_prod"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).clip(lower=0)
    df["year"] = df["ProductionMonth"].str[:4]
    df["co2e"] = df["vent"] * GAS_DENSITY * GWP100 + df["flare"] * GAS_DENSITY * FLARE_CO2E

    yearly = (df.groupby("year").agg(flare=("flare", "sum"), vent=("vent", "sum"))
                .round(0).astype(int).reset_index())
    trend = [{"year": r["year"], "flare": int(r["flare"]), "vent": int(r["vent"])}
             for _, r in yearly.iterrows()]

    ops = (df.groupby("OperatorName").agg(co2e=("co2e", "sum"), flare=("flare", "sum"),
                                          vent=("vent", "sum")).reset_index())
    ops = ops.sort_values("co2e", ascending=False)

    anom = pd.read_csv(os.path.join(DATA, "facility_anomalies.csv")).drop_duplicates("ReportingFacilityID")

    summary = {
        "generated": "2026-07",
        "period": f"{df['ProductionMonth'].min()} to {df['ProductionMonth'].max()}",
        "kpis": {
            "facilities": int(df["ReportingFacilityID"].nunique()),
            "operators": int(df["OperatorName"].nunique()),
            "flagged": int(anom["ReportingFacilityID"].nunique()),
            "total_flare": int(df["flare"].sum()),
            "total_vent": int(df["vent"].sum()),
            "total_co2e": int(df["co2e"].sum()),
        },
        "trend": trend,
        "top_operators": [
            {"operator": r["OperatorName"], "co2e": int(r["co2e"]),
             "flare": int(r["flare"]), "vent": int(r["vent"])}
            for _, r in ops.head(25).iterrows()
        ],
    }
    os.makedirs(WEB, exist_ok=True)
    with open(os.path.join(WEB, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print("wrote summary.json")
    print(f"  facilities {summary['kpis']['facilities']:,} | operators {summary['kpis']['operators']:,} "
          f"| flagged {summary['kpis']['flagged']:,}")
    print(f"  total CO2e {summary['kpis']['total_co2e']:,} t | "
          f"flare {summary['kpis']['total_flare']:,} | vent {summary['kpis']['total_vent']:,} (x10^3 m3)")


if __name__ == "__main__":
    main()
