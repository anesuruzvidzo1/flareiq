"""FlareIntel: emission factors, single source of truth.

Every CO2e number in this project comes from here. The factors follow the AER's
own published convention so FlareIntel's numbers reconcile with ST60B rather
than quietly diverging from the regulator everyone else cites.

Source: AER ST60B: Upstream Petroleum Industry Emissions Report.
  "The AER uses a conservative approach and assumes a 95 percent flare
   conversion efficiency and 85 percent mole fraction of methane content."
  Published factors: flared gas 2.3 tCO2e per 10^3 m3, vented gas 16.1 tCO2e
  per 10^3 m3.

The factors below are derived, not copied, so the assumptions stay visible.
The assertions at the bottom check the derivation against what the AER
publishes, so a bad edit fails on import instead of shipping silently.

All volumes in this project are in 10^3 m3 (Petrinex reporting unit).
"""

# --- assumptions, each traceable to a source ---
CH4_MOLE_FRACTION = 0.85          # AER ST60B: 85% methane content of the gas stream
CH4_DENSITY_KG_PER_M3 = 0.6785    # AER ST60B: methane density used in its MtCO2e formula
GWP100_CH4 = 28                   # IPCC AR5 100-yr GWP for methane, used by AER and ECCC
FLARE_EFFICIENCY = 0.95           # AER ST60B: 95% conversion, so 5% methane slip
CO2_PER_T_CH4_BURNED = 44 / 16    # stoichiometric: 2.75 t CO2 per t CH4 fully combusted

# tonnes of methane in 10^3 m3 of raw gas, after the 85% mole fraction
T_CH4_PER_E3M3 = 1000 * CH4_MOLE_FRACTION * CH4_DENSITY_KG_PER_M3 / 1000

# venting: all of the methane reaches the atmosphere
VENT_TCO2E_PER_E3M3 = T_CH4_PER_E3M3 * GWP100_CH4

# flaring: the burned share becomes CO2, the slip share stays methane
FLARE_TCO2E_PER_E3M3 = T_CH4_PER_E3M3 * (
    FLARE_EFFICIENCY * CO2_PER_T_CH4_BURNED
    + (1 - FLARE_EFFICIENCY) * GWP100_CH4
)

# how much worse venting is than flaring, per unit volume. ~7x under AER factors.
VENT_TO_FLARE_RATIO = VENT_TCO2E_PER_E3M3 / FLARE_TCO2E_PER_E3M3


def co2e_tonnes(vent, flare):
    """CO2e in tonnes from vented and flared volumes, both in 10^3 m3.

    Works elementwise on pandas Series as well as on scalars.
    """
    return vent * VENT_TCO2E_PER_E3M3 + flare * FLARE_TCO2E_PER_E3M3


# --- derivation must reproduce the AER's published factors ---
assert round(VENT_TCO2E_PER_E3M3, 1) == 16.1, VENT_TCO2E_PER_E3M3
assert round(FLARE_TCO2E_PER_E3M3, 1) == 2.3, FLARE_TCO2E_PER_E3M3


if __name__ == "__main__":
    print(f"methane per 10^3 m3 raw gas : {T_CH4_PER_E3M3:.4f} t CH4")
    print(f"vented                      : {VENT_TCO2E_PER_E3M3:.2f} tCO2e   (AER publishes 16.1)")
    print(f"flared                      : {FLARE_TCO2E_PER_E3M3:.2f} tCO2e   (AER publishes 2.3)")
    print(f"venting vs flaring          : {VENT_TO_FLARE_RATIO:.1f}x worse per m3")
