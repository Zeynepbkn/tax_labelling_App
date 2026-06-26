import React, { useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/apiClient";
import LoadingSpinner from "../components/LoadingSpinner";
import { useAuth } from "../contexts/AuthContext";

export default function AdminUsersPage() {
  const { currentUser } = useAuth();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [query, setQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [examFilter, setExamFilter] = useState("all");

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get("/admin/users");
      setRows(res.data || []);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Kullanıcılar alınamadı.";
      setError(typeof msg === "string" ? msg : "Kullanıcılar alınamadı.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const deleteUser = async (user) => {
    setError(null);
    if (user.id === currentUser?.id) {
      setError("Kendi admin kullanıcınızı silemezsiniz.");
      return;
    }
    if (!confirm(`${user.kullanici_adi} kullanıcısını silmek istediğinize emin misiniz? Bu kullanıcıya ait kayıtlar da silinebilir.`)) return;

    setDeletingId(user.id);
    try {
      await apiClient.delete(`/admin/users/${user.id}`);
      await loadUsers();
    } catch (err) {
      const msg = err?.response?.data?.detail || "Kullanıcı silinemedi.";
      setError(typeof msg === "string" ? msg : "Kullanıcı silinemedi.");
    } finally {
      setDeletingId(null);
    }
  };

  const filtered = useMemo(() => {
    return rows
      .filter((u) => {
        if (query.trim()) {
          const q = query.trim().toLowerCase();
          return (
            u.kullanici_adi?.toLowerCase().includes(q) ||
            u.email?.toLowerCase().includes(q) ||
            String(u.id).includes(q)
          );
        }
        return true;
      })
      .filter((u) => (roleFilter === "all" ? true : u.role === roleFilter))
      .filter((u) => {
        if (examFilter === "all") return true;
        return examFilter === "passed" ? !!u.exam_passed : !u.exam_passed;
      });
  }, [rows, query, roleFilter, examFilter]);

  if (loading) return <LoadingSpinner label="Kullanıcılar yükleniyor..." />;

  return (
    <div className="container grid">
      <div className="card row between">
        <div>
          <div style={{ fontWeight: 900, fontSize: 20 }}>Kullanıcılar</div>
          <div className="muted" style={{ marginTop: 6 }}>
            Kullanıcı listesi ve temel istatistikler.
          </div>
        </div>
        <span className="badge">Toplam: {rows.length}</span>
      </div>

      {error ? <div className="card" style={{ color: "var(--danger)", fontWeight: 800 }}>{error}</div> : null}

      <div className="card row" style={{ flexWrap: "wrap" }}>
        <input
          className="input"
          style={{ maxWidth: 320 }}
          placeholder="Ara: ad soyad / email / id"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select className="input" style={{ maxWidth: 220 }} value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
          <option value="all">Tum Roller</option>
          <option value="admin">Admin</option>
          <option value="labeler">Labeler</option>
        </select>
        <select className="input" style={{ maxWidth: 220 }} value={examFilter} onChange={(e) => setExamFilter(e.target.value)}>
          <option value="all">Sinav: Tumu</option>
          <option value="passed">Sinav: Gecti</option>
          <option value="notpassed">Sinav: Gecmedi</option>
        </select>
      </div>

      <div className="card" style={{ overflow: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Ad Soyad</th>
              <th>Email</th>
              <th>Rol</th>
              <th>Sinav</th>
              <th>Puan</th>
              <th>Tamamlanan</th>
              <th>Ort. Sure (sn)</th>
              <th>Son giris</th>
              <th>Islem</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((u) => (
              <tr key={u.id}>
                <td>{u.id}</td>
                <td>{u.kullanici_adi}</td>
                <td>{u.email}</td>
                <td>{u.role}</td>
                <td>{u.exam_passed ? "Gecti" : "Gecmedi"}</td>
                <td>{u.exam_score ?? "-"}</td>
                <td>{u.completed_documents ?? 0}</td>
                <td>{u.avg_duration_seconds ? Math.round(u.avg_duration_seconds) : "-"}</td>
                <td>{u.last_login_at ? new Date(u.last_login_at).toLocaleString("tr-TR") : "-"}</td>
                <td>
                  <button
                    className="btn danger"
                    type="button"
                    disabled={deletingId === u.id || u.id === currentUser?.id}
                    onClick={() => deleteUser(u)}
                  >
                    {deletingId === u.id ? "Siliniyor..." : "Sil"}
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
