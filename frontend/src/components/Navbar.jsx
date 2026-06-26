import React from "react";
import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function Navbar() {
  const { isAuthenticated, currentUser, role, logout } = useAuth();

  return (
    <div className="nav">
      <div className="navInner">
        <Link to="/" className="row" style={{ gap: 10 }}>
          <div style={{ fontWeight: 900, letterSpacing: 0.2 }}>ÖzelgeLab</div>
          <span className="badge">TR</span>
        </Link>

        <div className="navLinks">
          {isAuthenticated ? (
            <>
              <NavLink className="badge" to="/panel">
                Dashboard
              </NavLink>
              <NavLink className="badge" to="/kilavuz">
                Kılavuz
              </NavLink>
              <NavLink className="badge" to="/etiketleme">
                Etiketleme
              </NavLink>
              <NavLink className="badge" to="/lider-tablosu">
                Lider Tablosu
              </NavLink>
              {role === "admin" ? (
                <>
                  <NavLink className="badge" to="/admin">
                    Admin Panel
                  </NavLink>
                  <NavLink className="badge" to="/admin/upload">
                    Veri Yükle
                  </NavLink>
                  <NavLink className="badge" to="/admin/records">
                    Kayıtlar
                  </NavLink>
                  <NavLink className="badge" to="/admin/users">
                    Kullanıcılar
                  </NavLink>
                </>
              ) : null}
              <span className="badge">
                {currentUser?.kullanici_adi} ({role})
              </span>
              <button className="btn danger" onClick={logout}>
                Çıkış
              </button>
            </>
          ) : (
            <>
              <NavLink className="badge" to="/giris">
                Giriş
              </NavLink>
              <NavLink className="badge" to="/kayit">
                Kayıt
              </NavLink>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

