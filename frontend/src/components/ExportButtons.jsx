import React, { useState } from "react";
import { apiClient } from "../api/apiClient";

function buildExportUrl(path, filters = {}, options = {}) {
  const params = new URLSearchParams();
  if (filters.evrakId?.trim()) params.set("evrak_id", filters.evrakId.trim());
  const parsedUserId = Number(filters.userId?.trim());
  if (Number.isFinite(parsedUserId) && parsedUserId > 0) params.set("user_id", String(parsedUserId));
  if (options.includeText) params.set("include_text", "true");
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

async function downloadBlob(url, filename, mime) {
  const res = await apiClient.get(url, { responseType: "blob", timeout: 0 });
  const blob = new Blob([res.data], { type: mime || res.headers["content-type"] });
  const objectUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
}

async function getDownloadErrorMessage(err) {
  const data = err?.response?.data;
  if (data instanceof Blob) {
    const text = await data.text();
    try {
      const parsed = JSON.parse(text);
      if (typeof parsed?.detail === "string") return parsed.detail;
    } catch {
      return text || "Dosya indirilemedi.";
    }
  }
  return typeof data?.detail === "string" ? data.detail : "Dosya indirilemedi.";
}

export default function ExportButtons({ evrakId = "", userId = "" }) {
  const filters = { evrakId, userId };
  const [downloading, setDownloading] = useState(null);
  const [error, setError] = useState("");

  const handleDownload = async (kind, url, filename, mime) => {
    setDownloading(kind);
    setError("");
    try {
      await downloadBlob(url, filename, mime);
    } catch (err) {
      setError(await getDownloadErrorMessage(err));
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="grid" style={{ justifyItems: "end", gap: 8 }}>
      <div className="row" style={{ flexWrap: "wrap", justifyContent: "flex-end" }}>
        <button
          className="btn"
          type="button"
          disabled={!!downloading}
          onClick={() =>
            handleDownload(
              "json",
              buildExportUrl("/admin/export/json", filters),
              "labeling_records.json",
              "application/json"
            )
          }
        >
          {downloading === "json" ? "İndiriliyor..." : "JSON İndir"}
        </button>
        <button
          className="btn"
          type="button"
          disabled={!!downloading}
          onClick={() =>
            handleDownload(
              "json-text",
              buildExportUrl("/admin/export/json", filters, { includeText: true }),
              "labeling_records_with_text.json",
              "application/json"
            )
          }
        >
          {downloading === "json-text" ? "İndiriliyor..." : "JSON + Metin"}
        </button>
        <button
          className="btn"
          type="button"
          disabled={!!downloading}
          onClick={() =>
            handleDownload(
              "csv",
              buildExportUrl("/admin/export/csv", filters),
              "labeling_records.csv",
              "text/csv"
            )
          }
        >
          {downloading === "csv" ? "İndiriliyor..." : "CSV İndir"}
        </button>
        <button
          className="btn"
          type="button"
          disabled={!!downloading}
          onClick={() =>
            handleDownload(
              "csv-text",
              buildExportUrl("/admin/export/csv", filters, { includeText: true }),
              "labeling_records_with_text.csv",
              "text/csv"
            )
          }
        >
          {downloading === "csv-text" ? "İndiriliyor..." : "CSV + Metin"}
        </button>
        <button
          className="btn"
          type="button"
          disabled={!!downloading}
          onClick={() =>
            handleDownload(
              "excel",
              "/admin/export/excel",
              "labeling_records.xlsx",
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
          }
        >
          {downloading === "excel" ? "İndiriliyor..." : "Excel İndir"}
        </button>
        <button
          className="btn"
          type="button"
          disabled={!!downloading}
          onClick={() =>
            handleDownload(
              "backup",
              "/admin/backup",
              "backup.xlsx",
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
          }
        >
          {downloading === "backup" ? "İndiriliyor..." : "Excel Yedek"}
        </button>
        <button
          className="btn primary"
          type="button"
          disabled={!!downloading}
          onClick={() =>
            handleDownload(
              "db-backup",
              "/admin/backup/zip",
              "taxlabeltr_database_backup.zip",
              "application/zip"
            )
          }
        >
          {downloading === "db-backup" ? "İndiriliyor..." : "DB Yedeği"}
        </button>
      </div>
      {error ? (
        <div style={{ color: "var(--danger)", fontWeight: 800, fontSize: 13 }}>
          {error}
        </div>
      ) : null}
    </div>
  );
}
