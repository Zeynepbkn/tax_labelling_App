import React from "react";

export default function WarningModal({
  open,
  warnings,
  onConfirm,
  onCancel,
  title = "Kalite Uyarıları",
  description = "Backend bazı uyarılar tespit etti. Düzenlemek isterseniz “Kontrol et”i seçin.",
  cancelLabel = "Kontrol et",
  confirmLabel = "Eminim",
}) {
  if (!open) return null;
  const showConfirm = typeof onConfirm === "function";

  return (
    <div className="modalOverlay" role="dialog" aria-modal="true">
      <div className="modal card">
        <div style={{ fontWeight: 900, fontSize: 18, marginBottom: 10 }}>{title}</div>
        <div className="muted" style={{ marginBottom: 10 }}>
          {description}
        </div>
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {warnings?.map((w, i) => (
            <li key={i} style={{ marginBottom: 8 }}>
              {w}
            </li>
          ))}
        </ul>
        <div className="row" style={{ justifyContent: "flex-end", marginTop: 14 }}>
          <button className="btn" onClick={onCancel} type="button">
            {cancelLabel}
          </button>
          {showConfirm ? (
            <button className="btn primary" onClick={onConfirm} type="button">
              {confirmLabel}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

