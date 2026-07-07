export type Props = {
  facility: string;
  operator: string;
  type: string;
  flare: number;
  vent: number;
  co2e_t: number;
  ml_anomaly: number | null;
  flagged: boolean;
  reason: string;
};
export type Feat = {
  geometry: { coordinates: [number, number] };
  properties: Props;
};
export type Summary = {
  period: string;
  kpis: {
    facilities: number; operators: number; flagged: number;
    total_flare: number; total_vent: number; total_co2e: number;
  };
  trend: { year: string; flare: number; vent: number }[];
};
export type Activity = "all" | "flare" | "vent";
