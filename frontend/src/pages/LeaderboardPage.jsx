import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/apiClient";
import LeaderboardTable from "../components/LeaderboardTable";
import LoadingSpinner from "../components/LoadingSpinner";
import StatCard from "../components/StatCard";

export default function LeaderboardPage() {
  const navigate = useNavigate();
  const [leaderboard, setLeaderboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await apiClient.get("/labeling/leaderboard");
        if (alive) setLeaderboard(res.data);
      } catch (err) {
        const msg = err?.response?.data?.detail || "Lider tablosu alınamadı.";
        if (alive) setError(typeof msg === "string" ? msg : "Lider tablosu alınamadı.");
      } finally {
        if (alive) setLoading(false);
      }
    }

    load();
    return () => {
      alive = false;
    };
  }, []);

  if (loading) return <LoadingSpinner label="Lider tablosu yükleniyor..." />;

  const current = leaderboard?.current_user;
  const leader = leaderboard?.entries?.[0];

  return (
    <div className="container grid">
      <div className="card row between leaderboardHeader">
        <div>
          <div style={{ fontWeight: 900, fontSize: 20 }}>Lider Tablosu</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Ekipteki skorlar ve senin sıralaman.
          </div>
        </div>
        <button className="btn primary" onClick={() => navigate("/etiketleme")} type="button">
          Etiketlemeye Devam Et
        </button>
      </div>

      {error ? <div className="card" style={{ color: "var(--danger)", fontWeight: 800 }}>{error}</div> : null}

      <div className="grid leaderboardSummary">
        <StatCard title="Benim Skorum" value={current?.total_score ?? 0} subtitle={current ? `#${current.rank}` : "-"} />
        <StatCard title="Benim Toplamım" value={current?.completed_count ?? 0} subtitle="belge" />
        <StatCard title="Bugün" value={current?.today_completed_count ?? 0} subtitle="belge" />
        <StatCard title="Lider" value={leader?.total_score ?? 0} subtitle={leader?.kullanici_adi || "-"} />
      </div>

      <div className="card" style={{ overflow: "auto" }}>
        <div className="row between">
          <div>
            <div style={{ fontWeight: 900, fontSize: 18 }}>Genel Sıra</div>
            <div className="muted" style={{ marginTop: 6 }}>
              Skor; toplam etiketleme, bugünkü tempo ve ejderha ödüllerinden hesaplanır.
            </div>
          </div>
          {current ? (
            <span className="badge">
              Sen: #{current.rank} - {current.total_score ?? 0} skor
            </span>
          ) : null}
        </div>

        <LeaderboardTable leaderboard={leaderboard} />
      </div>
    </div>
  );
}
