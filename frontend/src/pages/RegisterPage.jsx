import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { isValidPersonFullName, normalizeFullName } from "../utils/validators";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [kullaniciAdi, setKullaniciAdi] = useState("");
  const [email, setEmail] = useState("");
  const [emailWarning, setEmailWarning] = useState(null);
  const [password, setPassword] = useState("");
  const [passwordWarning, setPasswordWarning] = useState(null);
  const [password2, setPassword2] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const onPasswordChange = (e) => {
    const value = e.target.value;
    setPassword(value);
    if (value.length > 0 && value.length < 6) {
      setPasswordWarning("Şifre en az 6 karakterli olmalıdır.");
    } else {
      setPasswordWarning(null);
    }
  };

  const onEmailChange = (e) => {
    const value = e.target.value;
    const atIndex = value.indexOf("@");
    const localPart = atIndex === -1 ? value : value.slice(0, atIndex);

    if (localPart.length > 25) {
      // @ işaretinden önceki kısmı en fazla 25 karaktere kırp
      const trimmedLocal = localPart.slice(0, 25);
      const rest = atIndex === -1 ? "" : value.slice(atIndex);
      setEmail(trimmedLocal + rest);
      setEmailWarning("En fazla 25 harfli mail ismi yazılabilir.");
      return;
    }

    setEmail(value);
    setEmailWarning(null);
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (password !== password2) {
      setError("Şifreler eşleşmiyor.");
      return;
    }
    if (password.length < 6) {
      setError("Şifre en az 6 karakter olmalıdır.");
      return;
    }

    const normalizedName = normalizeFullName(kullaniciAdi);
    if (!isValidPersonFullName(normalizedName)) {
      setError("Kullanıcı adı olarak gerçek ad ve soyad girilmelidir.");
      return;
    }

    setLoading(true);
    const res = await register(normalizedName, email, password);
    setLoading(false);
    if (res.ok) {
      navigate("/giris", { replace: true });
    } else {
      setError(res.message || "Kayıt başarısız.");
    }
  };

  return (
    <div className="container">
      <div className="card" style={{ maxWidth: 560, margin: "0 auto" }}>
        <div style={{ fontWeight: 900, fontSize: 20 }}>Kayıt</div>
        <div className="muted" style={{ marginTop: 6 }}>
          Yeni kullanıcı oluşturun. Rol varsayılan olarak <b>labeler</b> olacaktır.
        </div>

        <form onSubmit={onSubmit} style={{ marginTop: 14 }} className="grid">
          <div>
            <div className="muted" style={{ fontSize: 13, marginBottom: 6 }}>
              Ad Soyad
            </div>
            <input
              className="input"
              placeholder="Ad Soyad"
              value={kullaniciAdi}
              onChange={(e) => setKullaniciAdi(e.target.value)}
            />
          </div>
          <div>
            <div className="muted" style={{ fontSize: 13, marginBottom: 6 }}>
              Email
            </div>
            <input className="input" value={email} onChange={onEmailChange} />
            {emailWarning ? (
              <div style={{ color: "var(--danger)", fontWeight: 700, fontSize: 13, marginTop: 6 }}>
                {emailWarning}
              </div>
            ) : null}
          </div>
          <div>
            <div className="muted" style={{ fontSize: 13, marginBottom: 6 }}>
              Şifre
            </div>
            <input className="input" type="password" value={password} onChange={onPasswordChange} />
            {passwordWarning ? (
              <div style={{ color: "var(--danger)", fontWeight: 700, fontSize: 13, marginTop: 6 }}>
                {passwordWarning}
              </div>
            ) : null}
          </div>
          <div>
            <div className="muted" style={{ fontSize: 13, marginBottom: 6 }}>
              Şifre tekrar
            </div>
            <input className="input" type="password" value={password2} onChange={(e) => setPassword2(e.target.value)} />
          </div>

          {error ? <div style={{ color: "var(--danger)", fontWeight: 700 }}>{error}</div> : null}

          <button className="btn primary" disabled={loading} type="submit">
            {loading ? "Kaydediliyor..." : "Kayıt Ol"}
          </button>
        </form>

        <div className="muted" style={{ marginTop: 12 }}>
          Zaten hesabınız var mı? <Link to="/giris">Giriş yapın</Link>
        </div>
        <div className="muted" style={{ marginTop: 8 }}>
          <Link to="/">← Ana sayfaya dön</Link>
        </div>
      </div>
    </div>
  );
}
