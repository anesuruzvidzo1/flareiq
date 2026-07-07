"""FlareIntel, Piece 3a: geo-encode facilities to a map-ready GeoJSON.

Converts each facility's Alberta Township System (ATS/DLS) land location
(Township / Range / Meridian) to approximate lat/lon (township-center), attaches
flare / vent / CO2e and anomaly attributes, and writes a GeoJSON FeatureCollection.

Coordinate method: ATS is a regular grid (meridians 110/114/118 W; townships 6 mi
north of 49 N). Township-center accuracy (~few km), validated against known towns.
Exact per-facility coordinates (AER facility shapefile) are the documented upgrade.

Usage: python3 geo.py
"""
import json
import math
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

MERIDIAN_LON = {4: -110.0, 5: -114.0, 6: -118.0}
MILE_KM = 1.60934
TWP_DEG_LAT = 6 * MILE_KM / 110.574          # ~0.0873 deg lat per township (6 mi)


def dls_to_latlon(twp, rge, mer):
    try:
        twp, rge, mer = float(twp), float(rge), int(float(mer))
    except (TypeError, ValueError):
        return None, None
    if mer not in MERIDIAN_LON or twp < 1 or rge < 1 or twp > 130 or rge > 40:
        return None, None
    lat = 49.0 + (twp - 0.5) * TWP_DEG_LAT
    deg_per_mile_lon = MILE_KM / (111.320 * math.cos(math.radians(lat)))
    lon = MERIDIAN_LON[mer] - (rge - 0.5) * 6 * deg_per_mile_lon
    return round(lat, 4), round(lon, 4)


def mode_or_first(s):
    m = s.dropna()
    return m.mode().iat[0] if not m.mode().empty else (m.iat[0] if len(m) else np.nan)


def main():
    mon = pd.read_csv(os.path.join(DATA, "flare_vent_monthly.csv"))
    loc = (mon.groupby("ReportingFacilityID")
              .agg(FacilityTownship=("FacilityTownship", mode_or_first),
                   FacilityRange=("FacilityRange", mode_or_first),
                   FacilityMeridian=("FacilityMeridian", mode_or_first)).reset_index())

    fac = pd.read_csv(os.path.join(DATA, "facility_scores.csv"))
    fac = fac.sort_values("co2e_t", ascending=False).drop_duplicates("ReportingFacilityID")
    fac = fac.merge(loc, on="ReportingFacilityID", how="left")

    flagged = pd.read_csv(os.path.join(DATA, "facility_anomalies.csv"))
    flags = flagged.drop_duplicates("ReportingFacilityID")[["ReportingFacilityID", "reason"]]
    fac = fac.merge(flags, on="ReportingFacilityID", how="left")
    fac["flagged"] = fac["reason"].notna()

    fac = fac[(fac["flare"] + fac["vent"]) > 0].copy()
    coords = fac.apply(lambda r: dls_to_latlon(r["FacilityTownship"], r["FacilityRange"],
                                               r["FacilityMeridian"]), axis=1)
    fac["lat"] = [c[0] for c in coords]
    fac["lon"] = [c[1] for c in coords]
    geo = fac.dropna(subset=["lat", "lon"]).copy()

    # sanity check: Alberta is roughly lat 49-60, lon -110 to -120
    print(f"facilities with flare/vent: {len(fac):,} | geo-located: {len(geo):,} "
          f"({len(geo)/len(fac):.0%})")
    print(f"lat range {geo['lat'].min():.2f}..{geo['lat'].max():.2f}  "
          f"(Alberta ~49..60) | lon range {geo['lon'].min():.2f}..{geo['lon'].max():.2f}  "
          f"(Alberta ~-110..-120)")
    inbounds = geo[(geo.lat.between(48.9, 60.1)) & (geo.lon.between(-120.1, -109.9))]
    print(f"within Alberta bounds: {len(inbounds)/len(geo):.1%}")

    features = []
    for _, r in geo.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": {
                "facility": r["ReportingFacilityID"],
                "operator": r["OperatorName"],
                "type": r["ReportingFacilityType"],
                "flare": round(float(r["flare"]), 1),
                "vent": round(float(r["vent"]), 1),
                "co2e_t": round(float(r["co2e_t"]), 0),
                "ml_anomaly": round(float(r["ml_anomaly"]), 3) if pd.notna(r["ml_anomaly"]) else None,
                "flagged": bool(r["flagged"]),
                "reason": r["reason"] if pd.notna(r["reason"]) else "",
            },
        })
    fc = {"type": "FeatureCollection", "features": features}
    out = os.path.join(DATA, "facilities.geojson")
    with open(out, "w") as f:
        json.dump(fc, f)
    print(f"wrote {len(features):,} facility features -> {out} "
          f"({os.path.getsize(out)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
