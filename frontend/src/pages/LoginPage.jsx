import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function LoginPage() {
  const { login, refreshMe } = useAuth();
  const navigate = useNavigate();
  const [usernameOrEmail, setUsernameOrEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await login(usernameOrEmail, password);
      await refreshMe();
      // exam_passed durumuna göre yönlendirme
      if (res.exam_passed) navigate("/kilavuz", { replace: true });
      else navigate("/kilavuz", { replace: true });
    } catch (err) {
      const msg = err?.response?.data?.detail || "Kullanıcı adı veya şifre hatalı.";
      setError(typeof msg === "string" ? msg : "Kullanıcı adı veya şifre hatalı.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="card" style={{ maxWidth: 520, margin: "0 auto" }}>
        <div style={{ fontWeight: 900, fontSize: 20 }}>Giriş</div>
        <div className="muted" style={{ marginTop: 6 }}>
          Kullanıcı adı/email ve şifrenizle giriş yapın.
        </div>

        <form onSubmit={onSubmit} style={{ marginTop: 14 }} className="grid">
          <div>
            <div className="muted" style={{ fontSize: 13, marginBottom: 6 }}>
              Kullanıcı adı veya Email
            </div>
            <input
              className="input"
              placeholder="Ad Soyad veya Email"
              value={usernameOrEmail}
              onChange={(e) => setUsernameOrEmail(e.target.value)}
            />
          </div>
          <div>
            <div className="muted" style={{ fontSize: 13, marginBottom: 6 }}>
              Şifre
            </div>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {error ? <div style={{ color: "var(--danger)", fontWeight: 700 }}>{error}</div> : null}

          <button className="btn primary" disabled={loading} type="submit">
            {loading ? "Giriş yapılıyor..." : "Giriş Yap"}
          </button>
        </form>

        <div className="muted" style={{ marginTop: 12 }}>
          Hesabınız yok mu? <Link to="/kayit">Kayıt olun</Link>
        </div>
        <div className="muted" style={{ marginTop: 8 }}>
          <Link to="/">← Ana sayfaya dön</Link>
        </div>
      </div>
    </div>
  );
}

