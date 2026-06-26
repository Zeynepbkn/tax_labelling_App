import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient } from "../api/apiClient";
import GamificationPanel from "../components/GamificationPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import StatCard from "../components/StatCard";

export default function AdminDashboardPage() {
  const [data, setData] = useState(null);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [res, progressRes] = await Promise.all([
          apiClient.get("/admin/dashboard"),
          apiClient.get("/labeling/my-progress"),
        ]);
        if (!alive) return;
        setData(res.data);
        setProgress(progressRes.data);
      } catch (err) {
        const msg = err?.response?.data?.detail || "Dashboard alınamadı.";
        setError(typeof msg === "string" ? msg : "Dashboard alınamadı.");
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, []);

  if (loading) return <LoadingSpinner label="Admin dashboard yükleniyor..." />;

  return (
    <div className="container grid">
      <div className="card">
        <div className="row between">
          <div>
            <div style={{ fontWeight: 900, fontSize: 20 }}>Admin Dashboard</div>
            <div className="muted" style={{ marginTop: 6 }}>
              Sistem istatistikleri.
            </div>
          </div>
          <Link className="btn primary" to="/admin/upload">
            Veri Yükle
          </Link>
        </div>
      </div>

      {error ? <div className="notice danger">{error}</div> : null}

      {progress ? <GamificationPanel progress={progress} /> : null}

      {data ? (
        <>
          <div className="grid dashboardStats">
            <StatCard title="Toplam Kullanıcı" value={data.total_users} />
            <StatCard title="Sınavı Geçen" value={data.passed_users} />
            <StatCard title="Toplam Kayıt" value={data.total_labeling_records} />
          </div>
          <div className="grid dashboardStats">
            <StatCard title="Eğitim Belgesi" value={data.training_documents} />
            <StatCard title="Annotation Belgesi" value={data.annotation_documents} />
            <StatCard title="Bugünkü Kayıt" value={data.today_labeling_records} />
          </div>
          <div className="card">
            <div style={{ fontWeight: 900 }}>Top Etiketleyiciler</div>
            <div className="muted" style={{ marginTop: 6 }}>
              En çok etiketleme yapan kullanıcılar.
            </div>
            <table className="table" style={{ marginTop: 10 }}>
              <thead>
                <tr>
                  <th>Kullanıcı</th>
                  <th>Adet</th>
                </tr>
              </thead>
              <tbody>
                {(data.top_labelers || []).map((u) => (
                  <tr key={u.user_id}>
                    <td>{u.kullanici_adi}</td>
                    <td>{u.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </div>
  );
}

