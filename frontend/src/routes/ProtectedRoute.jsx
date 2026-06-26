import React from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import LoadingSpinner from "../components/LoadingSpinner";

export default function ProtectedRoute({ requireExamPassed = false }) {
  const { loading, isAuthenticated, examPassed, role } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingSpinner label="Yükleniyor..." />;
  if (!isAuthenticated) return <Navigate to="/" replace state={{ from: location }} />;

  if (requireExamPassed && !examPassed && role !== "admin") {
    return <Navigate to="/kilavuz" replace />;
  }

  return <Outlet />;
}

