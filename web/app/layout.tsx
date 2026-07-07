import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FlareIQ · Alberta flaring & venting intelligence",
  description:
    "Independent flaring and venting intelligence for every Alberta operator, from public AER and Petrinex data. Emissions hotspots, CO2e severity, and Directive 060 anomaly detection.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
