import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/apiClient";
import StatCard from "../components/StatCard";
import LoadingSpinner from "../components/LoadingSpinner";
import GamificationPanel from "../components/GamificationPanel";
import LeaderboardTable from "../components/LeaderboardTable";
import { useAuth } from "../contexts/AuthContext";
import { getBadgeForCompleted } from "../utils/badgeUtils";
import { formatTime } from "../utils/formatTime";

const RECORDS_PAGE_SIZE = 10;
const RECORD_SORT_OPTIONS = [
  { value: "newest", label: "En yeni kayıtlar" },
  { value: "question_count_asc", label: "Soru sayısı artan" },
];

export default function UserDashboardPage() {
  const { examPassed, currentUser, role } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [records, setRecords] = useState([]);
  const [recordsPage, setRecordsPage] = useState(1);
  const [recordsTotal, setRecordsTotal] = useState(0);
  const [recordSearchInput, setRecordSearchInput] = useState("");
  const [recordSearch, setRecordSearch] = useState("");
  const [recordSort, setRecordSort] = useState("newest");
  const [loading, setLoading] = useState(true);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    async function loadDashboard() {
      setLoading(true);
      setError(null);
      try {
        const [progRes, leaderboardRes] = await Promise.allSettled([
          apiClient.get("/labeling/my-progress"),
          apiClient.get("/labeling/leaderboard"),
        ]);
        if (!alive) return;
        if (progRes.status === "fulfilled") setData(progRes.value.data);
        if (leaderboardRes.status === "fulfilled") setLeaderboard(leaderboardRes.value.data);

        const failed = [progRes, leaderboardRes].find((result) => result.status === "rejected");
        if (failed) {
          const msg = failed.reason?.response?.data?.detail || "Bazı dashboard bilgileri alınamadı.";
          setError(typeof msg === "string" ? msg : "Bazı dashboard bilgileri alınamadı.");
        }
      } catch (err) {
        const msg = err?.response?.data?.detail || "İlerleme bilgisi alınamadı.";
        if (alive) setError(typeof msg === "string" ? msg : "İlerleme bilgisi alınamadı.");
      } finally {
        if (alive) setLoading(false);
      }
    }
    if (examPassed || role === "admin") loadDashboard();
    else setLoading(false);
    return () => {
      alive = false;
    };
  }, [examPassed, role]);

  useEffect(() => {
    let alive = true;
    async function loadRecords() {
      setRecordsLoading(true);
      try {
        const res = await apiClient.get("/labeling/my-records", {
          params: {
            page: recordsPage,
            page_size: RECORDS_PAGE_SIZE,
            evrak_id: recordSearch || undefined,
            sort: recordSort,
          },
        });
        if (!alive) return;
        const payload = res.data;
        setRecords(Array.isArray(payload) ? payload : payload?.items || []);
        setRecordsTotal(Array.isArray(payload) ? payload.length : payload?.total || 0);
      } catch (err) {
        const msg = err?.response?.data?.detail || "Kayıt listesi alınamadı.";
        if (alive) setError(typeof msg === "string" ? msg : "Kayıt listesi alınamadı.");
      } finally {
        if (alive) setRecordsLoading(false);
      }
    }
    if (examPassed || role === "admin") loadRecords();
    return () => {
      alive = false;
    };
  }, [examPassed, role, recordsPage, recordSearch, recordSort]);

  const applyRecordSearch = (event) => {
    event.preventDefault();
    setRecordsPage(1);
    setRecordSearch(recordSearchInput.trim());
  };

  const clearRecordSearch = () => {
    setRecordSearchInput("");
    setRecordSearch("");
    setRecordsPage(1);
  };

  const changeRecordSort = (event) => {
    setRecordSort(event.target.value);
    setRecordsPage(1);
  };

  const completed = data?.completed_count || 0;
  const badge = useMemo(() => getBadgeForCompleted(completed), [completed]);

  if (loading) return <LoadingSpinner label="Dashboard yükleniyor..." />;

  if (!examPassed && role !== "admin") {
    return (
      <div className="container">
        <div className="card">
          <div style={{ fontWeight: 900, fontSize: 20 }}>Hoş geldiniz, {currentUser?.kullanici_adi}</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Etiketlemeye başlamak için önce eğitim ve mini sınavı tamamlamalısınız.
          </div>
          <div className="row" style={{ justifyContent: "flex-end", marginTop: 12 }}>
            <button className="btn primary" onClick={() => navigate("/kilavuz")} type="button">
              Eğitime Git
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container grid">
      <div className="card row between">
        <div>
          <div style={{ fontWeight: 900, fontSize: 20 }}>Dashboard</div>
          <div className="muted" style={{ marginTop: 6 }}>
            İlerleme durumunuz ve temel metrikler.
          </div>
        </div>
        <div className="row" style={{ gap: 10 }}>
          <span className="badge">Rozet: {badge.label}</span>
          <button className="btn primary" onClick={() => navigate("/etiketleme")} type="button">
            Etiketlemeye Devam Et
          </button>
        </div>
      </div>

      {error ? <div className="card" style={{ color: "var(--danger)", fontWeight: 800 }}>{error}</div> : null}

      <div className="grid dashboardStats">
        <StatCard title="Skor" value={data?.total_score || 0} subtitle="lider tablosu" />
        <StatCard title="Tamamlanan Belge" value={completed} subtitle={badge.label} />
        <StatCard title="Bugün Tamamlanan" value={data?.today_completed_count || 0} />
        <StatCard
          title="Ortalama Süre"
          value={data?.avg_duration_seconds ? formatTime(Math.round(data.avg_duration_seconds)) : "-"}
          subtitle="(yaklaşık)"
        />
      </div>

      <GamificationPanel progress={data} />

      <LeaderboardCard leaderboard={leaderboard} />

      {recordsLoading || records.length > 0 || recordsTotal > 0 || recordSearch ? (
        <div className="card" style={{ overflow: "auto" }}>
          <div className="row between">
            <div style={{ fontWeight: 900, fontSize: 18 }}>Etiketlediğim belgeler</div>
            <span className="badge">
              {recordsTotal} kayıt | Sayfa {recordsPage}
            </span>
          </div>
          <div className="muted" style={{ marginTop: 6 }}>
            Hatalı olduğunu düşündüğünüz kayıtları açıp soru ve cevabı güncelleyebilirsiniz.
          </div>
          <form className="recordToolbar" onSubmit={applyRecordSearch}>
            <label className="recordControl">
              <span>Evrak ID ara</span>
              <input
                className="input"
                type="search"
                value={recordSearchInput}
                onChange={(event) => setRecordSearchInput(event.target.value)}
                placeholder="Örn. 4ile76x41d146v"
              />
            </label>
            <label className="recordControl">
              <span>Sıralama</span>
              <select className="input" value={recordSort} onChange={changeRecordSort}>
                {RECORD_SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="recordActions">
              <button className="btn primary" type="submit" disabled={recordsLoading}>
                Ara
              </button>
              <button className="btn" type="button" onClick={clearRecordSearch} disabled={recordsLoading && !recordSearch}>
                Temizle
              </button>
            </div>
          </form>
          {recordsLoading ? <InlineLoading label="Kayıtlar yükleniyor..." /> : null}
          <table className="table" style={{ marginTop: 12 }}>
            <thead>
              <tr>
                <th>Evrak</th>
                <th>Soru</th>
                <th>Tarih</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {!recordsLoading && records.length === 0 ? (
                <tr>
                  <td colSpan={4} className="muted">
                    Bu sayfada kayıt yok.
                  </td>
                </tr>
              ) : null}
              {records.map((r) => (
                <tr key={r.id}>
                  <td className="mono">{r.evrak_id}</td>
                  <td>{r.soru_sayisi}</td>
                  <td>{r.created_at ? new Date(r.created_at).toLocaleString("tr-TR") : "-"}</td>
                  <td>
                    <button
                      className="btn primary"
                      type="button"
                      onClick={() => navigate(`/etiketleme?duzenle=${r.id}`)}
                    >
                      Düzenle
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <PaginationControls
            page={recordsPage}
            pageSize={RECORDS_PAGE_SIZE}
            total={recordsTotal}
            onPageChange={setRecordsPage}
            loading={recordsLoading}
          />
        </div>
      ) : null}
    </div>
  );
}

function PaginationControls({ page, pageSize, total, onPageChange, loading = false }) {
  const totalPages = Math.max(1, Math.ceil((total || 0) / pageSize));
  const [jumpPage, setJumpPage] = useState(String(page));

  useEffect(() => {
    setJumpPage(String(page));
  }, [page]);

  if (totalPages <= 1) return null;
  const windowStart = Math.max(1, Math.min(page - 2, totalPages - 4));
  const windowEnd = Math.min(totalPages, windowStart + 4);
  const pages = Array.from({ length: windowEnd - windowStart + 1 }, (_, index) => windowStart + index);
  const startItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(total, page * pageSize);
  const goToPage = (nextPage) => onPageChange(clampPage(nextPage, totalPages));
  const submitJump = (event) => {
    event.preventDefault();
    const nextPage = Number.parseInt(jumpPage, 10);
    if (Number.isNaN(nextPage)) {
      setJumpPage(String(page));
      return;
    }
    goToPage(nextPage);
  };

  return (
    <div className="paginationPanel">
      <div className="muted" style={{ textAlign: "center" }}>
        Sayfa {page} / {totalPages} · {startItem}-{endItem} / {total} kayıt
      </div>
      <div className="paginationControls">
        <button className="btn" type="button" disabled={loading || page <= 1} onClick={() => goToPage(1)}>
          İlk
        </button>
        <button className="btn" type="button" disabled={loading || page <= 10} onClick={() => goToPage(page - 10)}>
          -10
        </button>
        <button className="btn" type="button" disabled={loading || page <= 1} onClick={() => goToPage(page - 1)}>
          Önceki
        </button>
        <div className="row paginationPages">
          {windowStart > 1 ? <span className="muted">...</span> : null}
          {pages.map((item) => (
            <button
              className={item === page ? "btn primary" : "btn"}
              disabled={loading}
              key={item}
              type="button"
              onClick={() => goToPage(item)}
            >
              {item}
            </button>
          ))}
          {windowEnd < totalPages ? <span className="muted">...</span> : null}
        </div>
        <button className="btn" type="button" disabled={loading || page >= totalPages} onClick={() => goToPage(page + 1)}>
          Sonraki
        </button>
        <button
          className="btn"
          type="button"
          disabled={loading || page + 10 > totalPages}
          onClick={() => goToPage(page + 10)}
        >
          +10
        </button>
        <button className="btn" type="button" disabled={loading || page >= totalPages} onClick={() => goToPage(totalPages)}>
          Son
        </button>
        <form className="paginationJump" onSubmit={submitJump}>
          <input
            className="input"
            type="number"
            min="1"
            max={totalPages}
            value={jumpPage}
            onChange={(event) => setJumpPage(event.target.value)}
            disabled={loading}
            aria-label="Sayfa numarası"
          />
          <button className="btn" type="submit" disabled={loading}>
            Git
          </button>
        </form>
      </div>
    </div>
  );
}

function clampPage(page, totalPages) {
  return Math.min(totalPages, Math.max(1, page));
}

function InlineLoading({ label }) {
  return (
    <div className="card row between" style={{ marginTop: 12 }}>
      <span style={{ fontWeight: 800 }}>{label}</span>
      <span className="badge">...</span>
    </div>
  );
}

function LeaderboardCard({ leaderboard }) {
  const current = leaderboard?.current_user;

  return (
    <div className="card" style={{ overflow: "auto" }}>
      <div className="row between">
        <div>
          <div style={{ fontWeight: 900, fontSize: 18 }}>Lider Tablosu</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Skora göre genel sıralama.
          </div>
        </div>
        {current ? (
          <span className="badge">
            Sen: #{current.rank} - {current.total_score ?? 0} skor
          </span>
        ) : null}
      </div>

      <LeaderboardTable leaderboard={leaderboard} compact />
    </div>
  );
}
