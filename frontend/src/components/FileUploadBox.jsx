import React, { useRef, useState } from "react";

function formatErrorDetail(detail) {
  if (!detail) return "Yükleme başarısız.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || item?.message || JSON.stringify(item)).join(" ");
  }
  if (typeof detail === "object") {
    return detail.message || detail.error || JSON.stringify(detail, null, 2);
  }
  return "Yükleme başarısız.";
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

async function sha256File(file) {
  if (!window.crypto?.subtle) return null;
  const buffer = await file.arrayBuffer();
  const hashBuffer = await window.crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export default function FileUploadBox({ title, description, accept = ".json", onUpload, onCheckDuplicate, onUploadComplete }) {
  const inputRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedHash, setSelectedHash] = useState(null);
  const [duplicateCheck, setDuplicateCheck] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handlePick = () => inputRef.current?.click();

  const handleChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setResult(null);
    setDuplicateCheck(null);
    setSelectedHash(null);
    if (!file.name.toLowerCase().endsWith(".json")) {
      setError("Sadece .json dosyasi yukleyebilirsiniz.");
      setSelectedFile(null);
      e.target.value = "";
      return;
    }
    setSelectedFile(file);
    e.target.value = "";

    if (!onCheckDuplicate) return;
    setChecking(true);
    try {
      const hash = await sha256File(file);
      setSelectedHash(hash);
      if (hash) {
        const check = await onCheckDuplicate(hash);
        setDuplicateCheck(check);
      }
    } catch {
      setError("Dosya kontrolu yapilamadi; yine de yukleme yapabilirsiniz.");
    } finally {
      setChecking(false);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const res = await onUpload(selectedFile);
      setResult(res);
      setSelectedFile(null);
      setSelectedHash(null);
      setDuplicateCheck(null);
      onUploadComplete?.(res);
    } catch (err) {
      const status = err?.response?.status;
      const msg = err?.code === "ECONNABORTED" ? "Yükleme 5 dakikayı aştı." : formatErrorDetail(err?.response?.data?.detail);
      setError(status ? `${status}: ${msg}` : msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="row between">
        <div>
          <div style={{ fontWeight: 900 }}>{title}</div>
          {description ? (
            <div className="muted" style={{ marginTop: 6 }}>
              {description}
            </div>
          ) : null}
        </div>
        <button className="btn primary" onClick={handlePick} disabled={loading} type="button">
          Dosya Sec
        </button>
      </div>

      <input ref={inputRef} type="file" accept={accept} style={{ display: "none" }} onChange={handleChange} />

      {selectedFile ? (
        <div className="selectedUpload">
          <div>
            <div style={{ fontWeight: 900 }}>{selectedFile.name}</div>
            <div className="muted" style={{ marginTop: 4 }}>
              {formatBytes(selectedFile.size)}
              {selectedHash ? ` | SHA-256: ${selectedHash.slice(0, 12)}...` : ""}
            </div>
          </div>
          <button className="btn primary" onClick={handleUpload} disabled={loading || checking} type="button">
            {loading ? "Yükleniyor..." : checking ? "Kontrol ediliyor..." : "Yükle"}
          </button>
        </div>
      ) : null}

      {duplicateCheck?.exists ? (
        <div className="notice warning" style={{ marginTop: 12 }}>
          <div>Bu dosya daha önce yüklenmiş.</div>
          <div className="muted" style={{ marginTop: 6, fontWeight: 700 }}>
            {duplicateCheck.matches
              .slice(0, 3)
              .map((item) => `${item.filename} - ${new Date(item.created_at).toLocaleString("tr-TR")}`)
              .join(" | ")}
          </div>
        </div>
      ) : null}

      {error ? (
        <div className="notice danger" style={{ marginTop: 12 }}>
          {error}
        </div>
      ) : null}

      {result ? (
        <div style={{ marginTop: 12 }}>
          <div className="badge">Sonuç</div>
          <pre className="card mono" style={{ marginTop: 10, overflow: "auto" }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
