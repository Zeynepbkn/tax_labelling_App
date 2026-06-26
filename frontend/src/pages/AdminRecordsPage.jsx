import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/apiClient";
import LoadingSpinner from "../components/LoadingSpinner";
import ExportButtons from "../components/ExportButtons";
import { formatDocumentTextForReading } from "../utils/textFormatting";

const RECORDS_PAGE_SIZE = 10;

export default function AdminRecordsPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [listLoading, setListLoading] = useState(false);
  const [error, setError] = useState(null);
  const [evrakId, setEvrakId] = useState("");
  const [userId, setUserId] = useState("");

  const [selected, setSelected] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const load = async (nextPage = page) => {
    if (!loading) setListLoading(true);
    setError(null);
    try {
      const params = { page: nextPage, page_size: RECORDS_PAGE_SIZE };
      if (evrakId.trim()) params.evrak_id = evrakId.trim();
      if (userId.trim()) params.user_id = Number(userId.trim());
      const res = await apiClient.get("/admin/records", { params });
      const payload = res.data;
      setRows(Array.isArray(payload) ? payload : payload?.items || []);
      setTotal(Array.isArray(payload) ? payload.length : payload?.total || 0);
      setPage(nextPage);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Kayıtlar alınamadı.";
      setError(typeof msg === "string" ? msg : "Kayıtlar alınamadı.");
    } finally {
      setLoading(false);
      setListLoading(false);
    }
  };

  useEffect(() => {
    load(1);
  }, []);

  const compareLoad = async (evrak) => {
    setSelected(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      const res = await apiClient.get(`/admin/records/${encodeURIComponent(evrak)}`);
      setSelected({ evrak_id: evrak, rows: res.data || [] });
    } catch (err) {
      const msg = err?.response?.data?.detail || "Karşılaştırma alınamadı.";
      setError(typeof msg === "string" ? msg : "Karşılaştırma alınamadı.");
    } finally {
      setDetailLoading(false);
    }
  };

  const openRecord = async (record) => {
    setSelected({ single: record });
    setDetailError(null);

    if (!record?.evrak_id) return;

    setDetailLoading(true);
    try {
      const [docRes, recordRes] = await Promise.all([
        apiClient.get(`/documents/${encodeURIComponent(record.evrak_id)}`),
        apiClient.get(`/labeling/records/${record.id}`),
      ]);
      const questions = (recordRes.data?.questions || []).map((q) => ({
        order: q.question_order,
        text: q.question_text,
        chars: q.character_count,
      }));
      setSelected({
        single: {
          ...record,
          cevap: recordRes.data?.cevap || record.cevap,
          questions,
          ozelge_metni: docRes.data?.display_text || "",
        },
      });
    } catch (err) {
      const msg = err?.response?.data?.detail || "Özelge metni alınamadı.";
      setDetailError(typeof msg === "string" ? msg : "Özelge metni alınamadı.");
    } finally {
      setDetailLoading(false);
    }
  };

  const deleteRecord = async (record) => {
    if (!record?.id) return;
    const label = `${record.kullanici_adi || "Kullanıcı"} / ${record.evrak_id || "evrak"}`;
    if (!confirm(`${label} etiketleme kaydini silmek istediginize emin misiniz?`)) return;

    setDeletingId(record.id);
    setError(null);
    try {
      await apiClient.delete(`/admin/records/by-id/${record.id}`);
      setRows((current) => current.filter((row) => row.id !== record.id));
      setTotal((current) => Math.max(0, current - 1));
      setSelected((current) => {
        if (current?.single?.id === record.id) return null;
        if (current?.rows) {
          return { ...current, rows: current.rows.filter((row) => row.id !== record.id) };
        }
        return current;
      });
    } catch (err) {
      const msg = err?.response?.data?.detail || "Kayıt silinemedi.";
      setError(typeof msg === "string" ? msg : "Kayıt silinemedi.");
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) return <LoadingSpinner label="Kayıtlar yükleniyor..." />;

  return (
    <div className="container grid">
      <div className="card row between">
        <div>
          <div style={{ fontWeight: 900, fontSize: 20 }}>Etiketleme Kayıtları</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Filtreleme, detay ve export.
          </div>
        </div>
        <ExportButtons evrakId={evrakId} userId={userId} />
      </div>

      {error ? <div className="card" style={{ color: "var(--danger)", fontWeight: 800 }}>{error}</div> : null}

      <div className="card row" style={{ flexWrap: "wrap" }}>
        <input
          className="input"
          style={{ maxWidth: 260 }}
          placeholder="Evrak ID"
          value={evrakId}
          onChange={(event) => setEvrakId(event.target.value)}
        />
        <input
          className="input"
          style={{ maxWidth: 200 }}
          placeholder="User ID"
          value={userId}
          onChange={(event) => setUserId(event.target.value)}
        />
        <button className="btn primary" type="button" onClick={() => load(1)}>
          Filtrele
        </button>
      </div>

      <div className="card" style={{ overflow: "auto" }}>
        <div className="row between" style={{ marginBottom: 10 }}>
          <div className="muted">
            {total} kayıt | Sayfa {page}
          </div>
          <PaginationControls
            page={page}
            pageSize={RECORDS_PAGE_SIZE}
            total={total}
            onPageChange={load}
            loading={listLoading}
          />
        </div>
        {listLoading ? <InlineLoading label="Kayıtlar yükleniyor..." /> : null}
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Kullanıcı</th>
              <th>Evrak</th>
              <th>Soru</th>
              <th>Süre (sn)</th>
              <th>Tarih</th>
              <th>Detay</th>
              <th>Düzenle</th>
              <th>Karşılaştır</th>
              <th>Sil</th>
            </tr>
          </thead>
          <tbody>
            {!listLoading && rows.length === 0 ? (
              <tr>
                <td colSpan={10} className="muted">
                  Bu sayfada kayıt yok.
                </td>
              </tr>
            ) : null}
            {rows.map((record) => (
              <tr key={record.id}>
                <td>{record.id}</td>
                <td>
                  {record.kullanici_adi} <span className="muted">({record.user_id})</span>
                </td>
                <td className="mono">{record.evrak_id}</td>
                <td>{record.soru_sayisi}</td>
                <td>{record.belgeyi_tamamlama_suresi_seconds ?? "-"}</td>
                <td>{record.created_at ? new Date(record.created_at).toLocaleString("tr-TR") : "-"}</td>
                <td>
                  <button className="btn" type="button" onClick={() => openRecord(record)}>
                    Aç
                  </button>
                </td>
                <td>
                  <button
                    className="btn primary"
                    type="button"
                    onClick={() => navigate(`/etiketleme?duzenle=${record.id}`)}
                  >
                    Etiketleme
                  </button>
                </td>
                <td>
                  <button className="btn" type="button" onClick={() => compareLoad(record.evrak_id)}>
                    Gör
                  </button>
                </td>
                <td>
                  <button
                    className="btn danger"
                    type="button"
                    disabled={deletingId === record.id}
                    onClick={() => deleteRecord(record)}
                  >
                    {deletingId === record.id ? "Siliniyor..." : "Sil"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <PaginationControls
          page={page}
          pageSize={RECORDS_PAGE_SIZE}
          total={total}
          onPageChange={load}
          loading={listLoading}
        />
      </div>

      {detailLoading && selected?.rows ? <InlineLoading label="Karşılaştırma yükleniyor..." /> : null}

      {selected?.single ? (
        <div className="card">
          <div style={{ fontWeight: 900 }}>Kayıt Detayı</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Evrak: <span className="mono">{selected.single.evrak_id}</span> | Kullanıcı: {selected.single.kullanici_adi}
          </div>
          <div className="row" style={{ justifyContent: "flex-end", marginTop: 10 }}>
            <button
              className="btn danger"
              type="button"
              disabled={deletingId === selected.single.id}
              onClick={() => deleteRecord(selected.single)}
            >
              {deletingId === selected.single.id ? "Siliniyor..." : "Bu Kaydı Sil"}
            </button>
          </div>
          <div className="grid" style={{ marginTop: 12 }}>
            <div className="card">
              <div style={{ fontWeight: 800 }}>Özelge metni</div>
              {detailError ? (
                <div style={{ color: "var(--danger)", fontWeight: 800, marginTop: 8 }}>{detailError}</div>
              ) : null}
              {detailLoading ? (
                <InlineLoading label="Özelge metni yükleniyor..." />
              ) : (
                <pre className="card mono" style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>
                  {formatDocumentTextForReading(selected.single.ozelge_metni) || "-"}
                </pre>
              )}
            </div>
            <div className="card">
              <div style={{ fontWeight: 800 }}>Sorular</div>
              <ol style={{ margin: 0, paddingLeft: 18, marginTop: 8 }}>
                {(selected.single.questions || []).map((question) => (
                  <li key={question.order} style={{ marginBottom: 10 }}>
                    {question.text}
                    <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                      Karakter: {question.chars}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
            <div className="card">
              <div style={{ fontWeight: 800 }}>Cevap</div>
              <pre className="card mono" style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>
                {selected.single.cevap}
              </pre>
            </div>
          </div>
        </div>
      ) : null}

      {selected?.rows ? (
        <div className="card">
          <div style={{ fontWeight: 900 }}>Karşılaştırma</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Evrak: <span className="mono">{selected.evrak_id}</span> için tüm kullanıcı etiketlemeleri.
          </div>
          <div className="grid" style={{ marginTop: 12 }}>
            {selected.rows.map((record) => (
              <div className="card" key={record.id}>
                <div className="row between">
                  <div style={{ fontWeight: 900 }}>{record.kullanici_adi}</div>
                  <div className="row" style={{ gap: 8 }}>
                    <span className="badge">Soru: {record.soru_sayisi}</span>
                    <button
                      className="btn danger"
                      type="button"
                      disabled={deletingId === record.id}
                      onClick={() => deleteRecord(record)}
                    >
                      {deletingId === record.id ? "Siliniyor..." : "Sil"}
                    </button>
                  </div>
                </div>
                <div style={{ marginTop: 10, fontWeight: 800 }}>Sorular</div>
                <ol style={{ margin: 0, paddingLeft: 18, marginTop: 6 }}>
                  {(record.questions || []).map((question) => (
                    <li key={question.order} style={{ marginBottom: 8 }}>
                      {question.text}
                    </li>
                  ))}
                </ol>
                <div style={{ marginTop: 10, fontWeight: 800 }}>Cevap</div>
                <pre className="card mono" style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>
                  {record.cevap}
                </pre>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function PaginationControls({ page, pageSize, total, onPageChange, loading = false }) {
  const totalPages = Math.max(1, Math.ceil((total || 0) / pageSize));
  if (totalPages <= 1) return null;
  const windowStart = Math.max(1, Math.min(page - 2, totalPages - 4));
  const windowEnd = Math.min(totalPages, windowStart + 4);
  const pages = Array.from({ length: windowEnd - windowStart + 1 }, (_, index) => windowStart + index);
  const startItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(total, page * pageSize);

  return (
    <div className="grid" style={{ gap: 8 }}>
      <div className="muted" style={{ textAlign: "center" }}>
        Sayfa {page} / {totalPages} · {startItem}-{endItem} / {total} kayıt
      </div>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn" type="button" disabled={loading || page <= 1} onClick={() => onPageChange(page - 1)}>
          Önceki
        </button>
        {pages.map((item) => (
          <button
            className={item === page ? "btn primary" : "btn"}
            disabled={loading}
            key={item}
            type="button"
            onClick={() => onPageChange(item)}
          >
            {item}
          </button>
        ))}
        <button className="btn" type="button" disabled={loading || page >= totalPages} onClick={() => onPageChange(page + 1)}>
          Sonraki
        </button>
      </div>
    </div>
  );
}

function InlineLoading({ label }) {
  return (
    <div className="card row between" style={{ marginBottom: 12, marginTop: 12 }}>
      <span style={{ fontWeight: 800 }}>{label}</span>
      <span className="badge">...</span>
    </div>
  );
}
