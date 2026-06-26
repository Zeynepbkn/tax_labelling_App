import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/apiClient";

const AuthContext = createContext(null);

function normalizeApiError(err, fallback = "Bir hata oluştu.") {
  const data = err?.response?.data;
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    const first = data.detail[0];
    if (first?.msg) {
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : null;
      const label = field === "password" ? "Şifre" : field === "email" ? "Email" : field === "kullanici_adi" ? "Kullanıcı adı" : null;
      return label ? `${label}: ${first.msg}` : first.msg;
    }
  }
  if (typeof data.detail === "object") return fallback;
  return fallback;
}

export function AuthProvider({ children }) {
  const navigate = useNavigate();
  const [token, setToken] = useState(() => localStorage.getItem("ozelgelab_token"));
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const isAuthenticated = !!token;
  const role = currentUser?.role || null;
  const examPassed = !!currentUser?.exam_passed;

  const logout = useCallback(() => {
    localStorage.removeItem("ozelgelab_token");
    setToken(null);
    setCurrentUser(null);
    navigate("/", { replace: true });
  }, [navigate]);

  useEffect(() => {
    const onUnauthorized = () => logout();
    window.addEventListener("auth:unauthorized", onUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", onUnauthorized);
  }, [logout]);

  const refreshMe = useCallback(async () => {
    if (!localStorage.getItem("ozelgelab_token")) {
      setCurrentUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await apiClient.get("/auth/me");
      setCurrentUser(me.data);
    } catch {
      logout();
    } finally {
      setLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  const login = useCallback(
    async (usernameOrEmail, password) => {
      const res = await apiClient.post("/auth/login", {
        username_or_email: usernameOrEmail,
        password
      });
      const newToken = res.data.access_token;
      localStorage.setItem("ozelgelab_token", newToken);
      setToken(newToken);
      await refreshMe();
      return res.data;
    },
    [refreshMe]
  );

  const register = useCallback(async (kullaniciAdi, email, password) => {
    try {
      const res = await apiClient.post("/auth/register", {
        kullanici_adi: kullaniciAdi,
        email,
        password
      });
      return { ok: true, data: res.data };
    } catch (err) {
      return { ok: false, message: normalizeApiError(err, "Kayıt başarısız.") };
    }
  }, []);

  const value = useMemo(
    () => ({
      token,
      currentUser,
      loading,
      isAuthenticated,
      role,
      examPassed,
      login,
      register,
      logout,
      refreshMe
    }),
    [token, currentUser, loading, isAuthenticated, role, examPassed, login, register, logout, refreshMe]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth AuthProvider içinde kullanılmalıdır.");
  return ctx;
}

