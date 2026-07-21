"use client";
import type { Feat, Summary, Activity } from "./types";

function fmt(n: number) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(0) + "k";
  return String(Math.round(n));
}

function TrendLine({ summary }: { summary: Summary }) {
  const t = summary.trend.filter((y) => Number(y.year) >= 2022 && Number(y.year) <= 2025);
  if (t.length < 2) return null;
  const a = t[0], b = t[t.length - 1];
  const vPct = Math.round(((b.vent - a.vent) / a.vent) * 100);
  const fPct = Math.round(((b.flare - a.flare) / a.flare) * 100);
  return (
    <div className="trend">
      Since {a.year}, reported <b>venting is down {Math.abs(vPct)}%</b> while{" "}
      <b>flaring is up {fPct}%</b> — operators shifting released methane to combustion,
      the direction Alberta&apos;s methane rules intend.
    </div>
  );
}

export default function Sidebar(props: {
  summary: Summary | null;
  watchlist: Feat[];
  totalFlagged: number;
  query: string;
  setQuery: (s: string) => void;
  activity: Activity;
  setActivity: (a: Activity) => void;
  focus: string | null;
  setFocus: (s: string | null) => void;
}) {
  const { summary, watchlist, totalFlagged, query, setQuery, activity, setActivity, focus, setFocus } = props;

  return (
    <aside className="side">
      <div className="brand">
        <div className="wm">Flare<span>IQ</span></div>
        <p>Independent flaring &amp; venting intelligence for every Alberta operator, from public AER and Petrinex data.</p>
        <span className="chip">Public data · 2022–2026</span>
      </div>

      {summary && (
        <>
          <div className="kpis">
            <div className="kpi">
              <div className="n">{(summary.kpis.total_co2e / 1e6).toFixed(1)}<small> Mt</small></div>
              <div className="l">CO₂e</div>
            </div>
            <div className="kpi">
              <div className="n">{fmt(summary.kpis.flagged)}</div>
              <div className="l">Flagged</div>
            </div>
            <div className="kpi">
              <div className="n">{summary.kpis.operators}</div>
              <div className="l">Operators</div>
            </div>
          </div>
          <TrendLine summary={summary} />
        </>
      )}

      <div className="controls">
        <input
          className="search"
          placeholder="Search operator…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="toggles">
          {(["all", "flare", "vent"] as Activity[]).map((a) => (
            <button key={a} className={"tg" + (activity === a ? " on" : "")} onClick={() => setActivity(a)}>
              {a === "all" ? "All" : a === "flare" ? "Flaring" : "Venting"}
            </button>
          ))}
        </div>
      </div>

      <div className="wl-head">
        <h3>Anomaly watchlist</h3>
        <span>{totalFlagged.toLocaleString()} facilities</span>
      </div>
      <div className="wl">
        {watchlist.map((f, i) => {
          const p = f.properties;
          const venting = p.vent > p.flare;
          return (
            <div
              key={p.facility}
              className={"row" + (focus === p.facility ? " sel" : "")}
              onClick={() => setFocus(focus === p.facility ? null : p.facility)}
            >
              <div className="rank">{i + 1}</div>
              <div>
                <div className="op">
                  <span className="badge" style={{ background: venting ? "#7c3aed" : "#b5561f" }} />
                  {p.operator}
                </div>
                <div className="meta">{p.reason || `${p.type} facility`}</div>
              </div>
              <div className="co2">{fmt(p.co2e_t)}<small>t CO₂e</small></div>
            </div>
          );
        })}
        {watchlist.length === 0 && (
          <div style={{ padding: 20, color: "#79818f", fontSize: 13 }}>No facilities match.</div>
        )}
      </div>

      <div className="foot">
        Estimates from public data (AER Directive 060, Orphan Well Association cost basis, Petrinex
        volumetrics). CO₂e uses the AER&apos;s published ST60B factors: 16.1 tCO₂e per 10³m³ vented,
        2.3 flared (85% methane, 95% flare efficiency, GWP100 28). Above a Directive 060 threshold = conservation-review
        trigger, not a finding of non-compliance. Not affiliated with the AER.
      </div>
    </aside>
  );
}
