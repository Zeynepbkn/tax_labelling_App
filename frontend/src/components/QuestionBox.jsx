import React from "react";

export default function QuestionBox({ index, value, onChange, onRemove, canRemove }) {
  return (
    <div className="card" style={{ padding: 12 }}>
      <div className="row between" style={{ marginBottom: 8 }}>
        <div style={{ fontWeight: 800 }}>Soru {index + 1}</div>
        {canRemove ? (
          <button className="btn danger" onClick={onRemove} type="button">
            Sil
          </button>
        ) : (
          <span className="badge">Zorunlu</span>
        )}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Mükellefin sorusunu bağlamıyla birlikte buraya yapıştırın..."
      />
      <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
        Karakter: {value?.trim()?.length || 0} (öneri: ≥150)
      </div>
    </div>
  );
}

