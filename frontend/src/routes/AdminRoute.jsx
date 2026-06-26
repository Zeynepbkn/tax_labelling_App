import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import LoadingSpinner from "../components/LoadingSpinner";

export default function AdminRoute() {
  const { loading, role, isAuthenticated } = useAuth();
  if (loading) return <LoadingSpinner label="Yükleniyor..." />;
  if (!isAuthenticated) return <Navigate to="/" replace />;
  if (role !== "admin") return <Navigate to="/panel" replace />;
  return <Outlet />;
}

