import React from "react";

export default function StatCard({ title, value, subtitle }) {
  return (
    <div className="card">
      <div className="muted" style={{ fontSize: 12, fontWeight: 800, letterSpacing: 0.02, textTransform: "uppercase" }}>
        {title}
      </div>
      <div style={{ fontSize: 26, fontWeight: 900, marginTop: 6 }}>{value}</div>
      {subtitle ? (
        <div className="muted" style={{ marginTop: 6 }}>
          {subtitle}
        </div>
      ) : null}
    </div>
  );
}

