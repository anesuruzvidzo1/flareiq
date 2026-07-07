"""FlareIntel, Piece 1: build the core flare / vent / production dataset.

Parses the Petrinex Alberta conventional volumetric monthly files (Vol_*.csv.zip)
into one tidy per-facility, per-month table of flared gas, vented gas, and gas
production, all in 10^3 m3. Activity codes confirmed from the data:
FLARE, VENT, PROD; product GAS.

Usage: python3 build_dataset.py
"""
import glob
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

# only the columns we need, to keep memory sane across 53 files
COLS = ["ProductionMonth", "OperatorBAID", "OperatorName", "ReportingFacilityID",
        "ReportingFacilityType", "FacilitySection", "FacilityTownship",
        "FacilityRange", "FacilityMeridian", "ActivityID", "ProductID", "Volume"]
ACTS = {"FLARE", "VENT", "PROD"}


def load_month(path):
    df = pd.read_csv(path, compression="zip", usecols=COLS, dtype=str)
    df = df[(df["ProductID"] == "GAS") & (df["ActivityID"].isin(ACTS))].copy()
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
    return df.dropna(subset=["Volume"])


def main():
    files = sorted(glob.glob(os.path.join(DATA, "Vol_*.csv.zip")))
    print(f"parsing {len(files)} files: "
          f"{os.path.basename(files[0])} .. {os.path.basename(files[-1])}")
    raw = pd.concat([load_month(f) for f in files], ignore_index=True)
    print(f"gas FLARE/VENT/PROD rows: {len(raw):,}")

    # one row per facility-month, activity volumes pivoted into columns
    key = ["ProductionMonth", "OperatorBAID", "OperatorName", "ReportingFacilityID",
           "ReportingFacilityType", "FacilitySection", "FacilityTownship",
           "FacilityRange", "FacilityMeridian"]
    tidy = (raw.groupby(key + ["ActivityID"])["Volume"].sum()
               .unstack("ActivityID", fill_value=0.0)
               .reset_index()
               .rename(columns={"FLARE": "flare", "VENT": "vent", "PROD": "gas_prod"}))
    for c in ["flare", "vent", "gas_prod"]:
        if c not in tidy.columns:
            tidy[c] = 0.0

    out = os.path.join(DATA, "flare_vent_monthly.csv")
    tidy.to_csv(out, index=False)
    print(f"wrote {len(tidy):,} facility-months -> {out}")

    # first signal
    tidy["year"] = tidy["ProductionMonth"].str[:4]
    tidy["fv"] = tidy["flare"] + tidy["vent"]
    print("\n--- flared + vented gas by year (10^3 m3) ---")
    print(tidy.groupby("year")[["flare", "vent"]].sum().round(0).to_string())
    print("\n--- top 10 operators by total flare + vent (10^3 m3) ---")
    print(tidy.groupby("OperatorName")["fv"].sum()
          .sort_values(ascending=False).head(10).round(0).to_string())


if __name__ == "__main__":
    main()
