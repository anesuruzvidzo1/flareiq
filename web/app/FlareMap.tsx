"use client";
import { useEffect, useRef } from "react";
import "leaflet/dist/leaflet.css";
import type { Feat } from "./types";

export default function FlareMap({
  all, markers, focus, setFocus,
}: {
  all: Feat[];
  markers: Feat[];
  focus: string | null;
  setFocus: (s: string | null) => void;
}) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<any>(null);
  const L = useRef<any>(null);
  const heat = useRef<any>(null);
  const layer = useRef<any>(null);
  const byId = useRef<Record<string, any>>({});

  // init once
  useEffect(() => {
    let dead = false;
    (async () => {
      const Lm = (await import("leaflet")).default as any;
      await import("leaflet.heat");
      if (dead || !el.current || map.current) return;
      L.current = Lm;
      map.current = Lm.map(el.current, { preferCanvas: true, zoomControl: true }).setView([54.3, -114.8], 5);
      Lm.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
        attribution: "&copy; OpenStreetMap &copy; CARTO", subdomains: "abcd", maxZoom: 12,
      }).addTo(map.current);
    })();
    return () => { dead = true; if (map.current) { map.current.remove(); map.current = null; } };
  }, []);

  // heat layer from all facilities (once data arrives)
  useEffect(() => {
    const iv = setInterval(() => {
      if (!map.current || !L.current || !all.length || heat.current) return;
      clearInterval(iv);
      const pts = all.map((f) => {
        const [lon, lat] = f.geometry.coordinates;
        return [lat, lon, Math.log1p(f.properties.co2e_t || 0)];
      });
      const mx = Math.max(1, ...pts.map((p) => p[2]));
      heat.current = L.current.heatLayer(
        pts.map((p) => [p[0], p[1], p[2] / mx]),
        { radius: 11, blur: 16, maxZoom: 9, minOpacity: 0.22 }
      ).addTo(map.current);
    }, 120);
    return () => clearInterval(iv);
  }, [all]);

  // markers rebuilt when the filtered set changes
  useEffect(() => {
    const iv = setInterval(() => {
      if (!map.current || !L.current) return;
      clearInterval(iv);
      if (layer.current) layer.current.remove();
      byId.current = {};
      const g = L.current.layerGroup();
      [...markers]
        .sort((a, b) => b.properties.co2e_t - a.properties.co2e_t)
        .slice(0, 900)
        .forEach((f) => {
          const [lon, lat] = f.geometry.coordinates;
          const p = f.properties;
          const color = p.vent > p.flare ? "#7c3aed" : "#b5561f";
          const m = L.current.circleMarker([lat, lon], {
            radius: 3 + Math.min(9, Math.log1p(p.co2e_t) / 1.6),
            color, weight: 1, fillColor: color, fillOpacity: 0.6,
          }).bindPopup(
            `<b>${p.operator}</b><br>${p.facility} · ${p.type}<br>` +
            `Flare ${p.flare.toLocaleString()} · Vent ${p.vent.toLocaleString()} (×10³m³)<br>` +
            `<b>${Math.round(p.co2e_t).toLocaleString()} t CO₂e</b><br>` +
            `<span style="color:#79818f">${p.reason || ""}</span>`
          );
          m.on("click", () => setFocus(p.facility));
          m.addTo(g);
          byId.current[p.facility] = m;
        });
      g.addTo(map.current);
      layer.current = g;
    }, 120);
    return () => clearInterval(iv);
  }, [markers, setFocus]);

  // fly to focused facility
  useEffect(() => {
    if (!map.current || !focus) return;
    const m = byId.current[focus];
    if (m) {
      map.current.flyTo(m.getLatLng(), 9, { duration: 0.8 });
      setTimeout(() => m.openPopup(), 850);
    }
  }, [focus]);

  return <div ref={el} style={{ height: "100%", width: "100%" }} />;
}
