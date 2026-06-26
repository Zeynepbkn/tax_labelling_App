import React, { useEffect, useState } from "react";
import { apiClient } from "../api/apiClient";
import LoadingSpinner from "../components/LoadingSpinner";

const emptyForm = {
  question_text: "",
  option_a: "",
  option_b: "",
  option_c: "",
  option_d: "",
  correct_option: "A",
  explanation: "",
  active: true
};

export default function AdminQuizPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get("/admin/quiz/questions");
      setRows(res.data || []);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Quiz soruları alınamadı.";
      setError(typeof msg === "string" ? msg : "Quiz soruları alınamadı.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const save = async () => {
    setError(null);
    try {
      if (editingId) {
        await apiClient.put(`/admin/quiz/questions/${editingId}`, form);
      } else {
        await apiClient.post("/admin/quiz/questions", form);
      }
      setForm(emptyForm);
      setEditingId(null);
      await load();
    } catch (err) {
      const msg = err?.response?.data?.detail || "Kaydedilemedi.";
      setError(typeof msg === "string" ? msg : "Kaydedilemedi.");
    }
  };

  const edit = (q) => {
    setEditingId(q.id);
    setForm({
      question_text: q.question_text || "",
      option_a: q.option_a || "",
      option_b: q.option_b || "",
      option_c: q.option_c || "",
      option_d: q.option_d || "",
      correct_option: q.correct_option || "A",
      explanation: q.explanation || "",
      active: q.active ?? true
    });
  };

  const del = async (id) => {
    if (!confirm("Silmek istediğinize emin misiniz?")) return;
    try {
      await apiClient.delete(`/admin/quiz/questions/${id}`);
      await load();
    } catch (err) {
      const msg = err?.response?.data?.detail || "Silinemedi.";
      setError(typeof msg === "string" ? msg : "Silinemedi.");
    }
  };

  if (loading) return <LoadingSpinner label="Quiz yönetimi yükleniyor..." />;

  return (
    <div className="container grid">
      <div className="card">
        <div style={{ fontWeight: 900, fontSize: 20 }}>Quiz Yönetimi</div>
        <div className="muted" style={{ marginTop: 6 }}>
          Soru ekle/düzenle/sil.
        </div>
      </div>

      {error ? <div className="card" style={{ color: "var(--danger)", fontWeight: 800 }}>{error}</div> : null}

      <div className="card grid">
        <div style={{ fontWeight: 900 }}>{editingId ? `Düzenle (#${editingId})` : "Yeni Soru"}</div>
        <textarea
          value={form.question_text}
          onChange={(e) => setForm((f) => ({ ...f, question_text: e.target.value }))}
          placeholder="Soru metni"
        />
        <input className="input" value={form.option_a} onChange={(e) => setForm((f) => ({ ...f, option_a: e.target.value }))} placeholder="Seçenek A" />
        <input className="input" value={form.option_b} onChange={(e) => setForm((f) => ({ ...f, option_b: e.target.value }))} placeholder="Seçenek B" />
        <input className="input" value={form.option_c} onChange={(e) => setForm((f) => ({ ...f, option_c: e.target.value }))} placeholder="Seçenek C" />
        <input className="input" value={form.option_d} onChange={(e) => setForm((f) => ({ ...f, option_d: e.target.value }))} placeholder="Seçenek D" />
        <div className="row">
          <label className="row" style={{ gap: 8 }}>
            <span className="muted">Doğru:</span>
            <select className="input" style={{ maxWidth: 120 }} value={form.correct_option} onChange={(e) => setForm((f) => ({ ...f, correct_option: e.target.value }))}>
              <option value="A">A</option>
              <option value="B">B</option>
              <option value="C">C</option>
              <option value="D">D</option>
            </select>
          </label>
          <label className="row" style={{ gap: 8 }}>
            <input type="checkbox" checked={form.active} onChange={(e) => setForm((f) => ({ ...f, active: e.target.checked }))} />
            <span className="muted">Aktif</span>
          </label>
        </div>
        <textarea
          value={form.explanation}
          onChange={(e) => setForm((f) => ({ ...f, explanation: e.target.value }))}
          placeholder="Açıklama (opsiyonel)"
        />
        <div className="row" style={{ justifyContent: "flex-end" }}>
          {editingId ? (
            <button className="btn" type="button" onClick={() => { setEditingId(null); setForm(emptyForm); }}>
              İptal
            </button>
          ) : null}
          <button className="btn primary" type="button" onClick={save}>
            Kaydet
          </button>
        </div>
      </div>

      <div className="card" style={{ overflow: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Soru</th>
              <th>Aktif</th>
              <th>İşlem</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((q) => (
              <tr key={q.id}>
                <td>{q.id}</td>
                <td>{q.question_text}</td>
                <td>{q.active ? "Evet" : "Hayır"}</td>
                <td className="row" style={{ gap: 8 }}>
                  <button className="btn" type="button" onClick={() => edit(q)}>
                    Düzenle
                  </button>
                  <button className="btn danger" type="button" onClick={() => del(q.id)}>
                    Sil
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

