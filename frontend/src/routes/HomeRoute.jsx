import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import LoadingSpinner from "../components/LoadingSpinner";
import WelcomePage from "../pages/WelcomePage";

export default function HomeRoute() {
  const { loading, isAuthenticated } = useAuth();

  if (loading) return <LoadingSpinner label="Yükleniyor..." />;
  if (isAuthenticated) return <Navigate to="/panel" replace />;

  return <WelcomePage />;
}
