import React from "react";

export default function LoadingSpinner({ label = "Yükleniyor..." }) {
  return (
    <div className="container">
      <div className="card row between">
        <div>
          <div style={{ fontWeight: 800, fontSize: 16 }}>{label}</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Lütfen bekleyin.
          </div>
        </div>
        <div className="badge">…</div>
      </div>
    </div>
  );
}

