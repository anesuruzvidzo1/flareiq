"use client";
import { useEffect, useMemo, useState } from "react";
import type { Feat, Summary, Activity } from "./types";
import Sidebar from "./Sidebar";
import FlareMap from "./FlareMap";

export default function Home() {
  const [feats, setFeats] = useState<Feat[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [query, setQuery] = useState("");
  const [activity, setActivity] = useState<Activity>("all");
  const [focus, setFocus] = useState<string | null>(null);

  useEffect(() => {
    fetch("/data/summary.json").then((r) => r.json()).then(setSummary).catch(() => {});
    fetch("/data/facilities.geojson").then((r) => r.json())
      .then((gj) => setFeats(gj.features)).catch(() => {});
  }, []);

  const q = query.trim().toLowerCase();
  const filtered = useMemo(() => {
    return feats.filter((f) => {
      const p = f.properties;
      if (!p.flagged) return false;
      if (q && !p.operator.toLowerCase().includes(q)) return false;
      if (activity === "flare" && p.flare <= p.vent) return false;
      if (activity === "vent" && p.vent <= p.flare) return false;
      return true;
    });
  }, [feats, q, activity]);

  const watchlist = useMemo(
    () => [...filtered].sort((a, b) => b.properties.co2e_t - a.properties.co2e_t).slice(0, 80),
    [filtered]
  );

  return (
    <div className="shell">
      <Sidebar
        summary={summary}
        watchlist={watchlist}
        totalFlagged={filtered.length}
        query={query}
        setQuery={setQuery}
        activity={activity}
        setActivity={setActivity}
        focus={focus}
        setFocus={setFocus}
      />
      <div className="mapwrap">
        <FlareMap all={feats} markers={filtered} focus={focus} setFocus={setFocus} />
        <div className="mlegend">
          <div className="r"><span className="badge" style={{ background: "#b5561f" }} />Flaring</div>
          <div className="r"><span className="badge" style={{ background: "#7c3aed" }} />Venting (methane)</div>
          <div className="r" style={{ marginTop: 4, color: "#79818f" }}>heat = CO₂e intensity</div>
        </div>
      </div>
    </div>
  );
}
