import React, { useCallback, useEffect, useState } from "react";
import FileUploadBox from "../components/FileUploadBox";
import { apiClient } from "../api/apiClient";

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function datasetLabel(type) {
  if (type === "training") return "Eğitim";
  if (type === "annotation") return "Özelge";
  return type || "-";
}

function summaryText(upload) {
  const summary = upload.summary || {};
  if (upload.dataset_type === "training") {
    return `${summary.documents_with_evrak_id || 0} evrak, ${summary.documents_with_text || 0} metin, ${
      summary.question_fields?.length || 0
    } soru alanı`;
  }
  if (upload.dataset_type === "annotation") {
    return `${summary.documents_with_evrak_oid || 0} evrak, ${summary.documents_with_html_text || 0} html, ${
      summary.documents_with_pdf_text || 0
    } pdf`;
  }
  return `${upload.total_items} kayıt`;
}

export default function AdminUploadPage() {
  const [uploads, setUploads] = useState([]);
  const [stats, setStats] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState(null);

  const loadUploads = useCallback(async () => {
    setHistoryError(null);
    setHistoryLoading(true);
    try {
      const [uploadsRes, statsRes] = await Promise.all([apiClient.get("/admin/uploads"), apiClient.get("/admin/dashboard")]);
      setUploads(uploadsRes.data);
      setStats(statsRes.data);
    } catch {
      setHistoryError("Yükleme geçmişi alınamadı.");
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUploads();
  }, [loadUploads]);

  const checkDuplicate = async (sha256) => {
    const res = await apiClient.get("/admin/uploads/check", { params: { sha256 } });
    return res.data;
  };

  const uploadTraining = async (file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await apiClient.post("/admin/upload-training-json", form, {
      headers: { "Content-Type": "multipart/form-data" }
    });
    return res.data;
  };

  const uploadAnnotation = async (file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await apiClient.post("/admin/upload-annotation-json", form, {
      headers: { "Content-Type": "multipart/form-data" }
    });
    return res.data;
  };

  return (
    <div className="container grid">
      <div className="card">
        <div style={{ fontWeight: 900, fontSize: 20 }}>Veri Yükleme</div>
        <div className="muted" style={{ marginTop: 6 }}>
          Eğitim örnekleri ve özelge etiketleme havuzu için ayrı JSON yükleme alanları.
        </div>
        {stats ? (
          <div className="uploadStats">
            <div>
              <div className="muted">Eğitim verisi</div>
              <div style={{ fontWeight: 900 }}>{stats.training_documents}</div>
            </div>
            <div>
              <div className="muted">Özelge verisi</div>
              <div style={{ fontWeight: 900 }}>{stats.annotation_documents}</div>
            </div>
            <div>
              <div className="muted">Kayıtlı yükleme</div>
              <div style={{ fontWeight: 900 }}>{uploads.length}</div>
            </div>
          </div>
        ) : null}
      </div>

      <section className="uploadSection">
        <div className="uploadSectionHeader">
          <div>
            <div className="sectionEyebrow">Eğitim Örnekleri</div>
            <h2>Labelled Data JSON</h2>
          </div>
          <span className="badge">training</span>
        </div>
        <FileUploadBox
          title="labelled_questions.json yükle"
          description="Etiketli eğitim örnekleri buradan yüklenir. Belgeler training split'iyle kaydedilir; soru_1..soru_7 alanları eğitim soru listesine aktarılır."
          onUpload={uploadTraining}
          onCheckDuplicate={checkDuplicate}
          onUploadComplete={loadUploads}
        />
      </section>

      <section className="uploadSection">
        <div className="uploadSectionHeader">
          <div>
            <div className="sectionEyebrow">Özelge Etiketleme</div>
            <h2>Özelge Verileri JSON</h2>
          </div>
          <span className="badge">annotation</span>
        </div>
        <FileUploadBox
          title="ozelge_veri.json yükle"
          description="Etiketleme yapılacak ham özelge verileri buradan yüklenir. evrakOid, evrak_id olarak kaydedilir; gösterilecek metin backend tarafından seçilir."
          onUpload={uploadAnnotation}
          onCheckDuplicate={checkDuplicate}
          onUploadComplete={loadUploads}
        />
      </section>

      <section className="uploadSection">
        <div className="uploadSectionHeader">
          <div>
            <div className="sectionEyebrow">Admin</div>
            <h2>Yükleme Geçmişi</h2>
          </div>
          <button className="btn" type="button" onClick={loadUploads} disabled={historyLoading}>
            Yenile
          </button>
        </div>

        <div className="card">
          {historyError ? <div className="notice danger">{historyError}</div> : null}
          {historyLoading ? <div className="muted">Yükleniyor...</div> : null}
          {!historyLoading && uploads.length === 0 ? <div className="muted">Henüz JSON yüklenmemiş.</div> : null}
          {!historyLoading && uploads.length > 0 ? (
            <div className="tableWrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Dosya</th>
                    <th>Tür</th>
                    <th>İçerik</th>
                    <th>Sonuç</th>
                    <th>Kontrol</th>
                    <th>Tarih</th>
                  </tr>
                </thead>
                <tbody>
                  {uploads.map((upload) => (
                    <tr key={upload.id}>
                      <td>
                        <div style={{ fontWeight: 900 }}>{upload.filename}</div>
                        <div className="muted">{formatBytes(upload.file_size_bytes)}</div>
                      </td>
                      <td>
                        <span className="badge">{datasetLabel(upload.dataset_type)}</span>
                      </td>
                      <td>
                        <div>{upload.total_items} veri</div>
                        <div className="muted">{summaryText(upload)}</div>
                      </td>
                      <td>
                        <div>{upload.added} eklendi</div>
                        <div className="muted">
                          {upload.skipped} atlandı, {upload.duplicates} tekrar
                        </div>
                      </td>
                      <td>
                        <div className="mono">{upload.sha256.slice(0, 12)}...</div>
                        <div className={upload.warnings_count ? "textWarning" : "muted"}>
                          {upload.warnings_count ? `${upload.warnings_count} uyarı` : "Uyarı yok"}
                        </div>
                      </td>
                      <td>
                        <div>{new Date(upload.created_at).toLocaleString("tr-TR")}</div>
                        <div className="muted">{upload.uploaded_by_username || "admin"}</div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
