# FlareIQ

**Live demo: (deploying)**

Independent flaring and venting intelligence for every Alberta operator, built from public
AER and Petrinex data. FlareIQ turns raw monthly volumetric reports into an emissions map,
a CO2e-weighted severity ranking, and a regulation-grounded anomaly watchlist. Vendors see
only their own customers; FlareIQ covers the whole province.

## What it does

- Parses 53 monthly Petrinex conventional volumetric files (2022 to 2026) into a tidy
  per facility, per month record of flared gas, vented gas, and gas production.
- Scores every facility for anomalies, grounded in AER Directive 060 thresholds, peer
  relative flaring intensity, and a methane weighted CO2e severity score.
- Adds an Isolation Forest for multivariate outliers and a temporal detector for
  non routine upset spikes.
- Geo encodes facilities from the Alberta Township System to lat and lon and renders an
  interactive map with a searchable operator watchlist.

## Why the numbers are framed carefully

- Venting is roughly eight to nine times worse than flaring per cubic metre, because vented
  gas is raw methane (GWP100 of 28) while flaring burns it to CO2. Severity is ranked by CO2e,
  not raw volume, so the worst climate emitters surface first.
- Exceeding a Directive 060 threshold means a facility is above a conservation review trigger,
  not that it is non compliant. Many facilities hold approvals.
- Facility locations are township centre approximations. Exact coordinates from the AER
  facility shapefile are the documented upgrade.
- All figures are independent estimates from public data, not endorsed by the AER.

## A finding

Across 2022 to 2025, reported venting fell about 33 percent while flaring rose about 13 percent,
consistent with operators shifting released methane to combustion, the direction Alberta's
methane rules intend.

## Pipeline

    pip3 install -r requirements.txt

    python3 scripts/build_dataset.py    # parse volumetric files -> flare_vent_monthly.csv
    python3 scripts/anomaly.py          # Directive 060 flags + CO2e severity -> facility_anomalies.csv
    python3 scripts/anomaly_ml.py       # Isolation Forest + temporal spikes -> facility_scores.csv
    python3 scripts/geo.py              # ATS -> lat/lon -> facilities.geojson
    python3 scripts/summary.py          # province wide KPIs -> web/public/data/summary.json

## Web

    cd web
    npm install
    npm run dev

Next.js and Leaflet, static first, deployable to Vercel. No API keys, free CARTO and
OpenStreetMap tiles.

## Data sources

- Petrinex Alberta conventional volumetric public data (CSV, monthly).
- AER Directive 060, Upstream Petroleum Industry Flaring, Incinerating, and Venting.
- Orphan Well Association cost basis and AER liability figures for context.
