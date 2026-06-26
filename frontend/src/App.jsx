import React from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./routes/ProtectedRoute";
import AdminRoute from "./routes/AdminRoute";
import HomeRoute from "./routes/HomeRoute";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import TrainingGuidePage from "./pages/TrainingGuidePage";
import QuizPage from "./pages/QuizPage";
import UserDashboardPage from "./pages/UserDashboardPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import LabelingPage from "./pages/LabelingPage";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import AdminUploadPage from "./pages/AdminUploadPage";
import AdminUsersPage from "./pages/AdminUsersPage";
import AdminRecordsPage from "./pages/AdminRecordsPage";
import AdminQuizPage from "./pages/AdminQuizPage";

function AppShell() {
  const location = useLocation();
  const hideNavbar = location.pathname === "/";

  return (
    <>
      {!hideNavbar ? <Navbar /> : null}
      <Routes>
        <Route path="/" element={<HomeRoute />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/panel" element={<UserDashboardPage />} />
          <Route path="/kilavuz" element={<TrainingGuidePage />} />
          <Route path="/sinav" element={<QuizPage />} />
          <Route path="/lider-tablosu" element={<ProtectedRoute requireExamPassed />}>
            <Route index element={<LeaderboardPage />} />
          </Route>
          <Route path="/etiketleme" element={<LabelingPage />} />
        </Route>

        <Route path="/giris" element={<LoginPage />} />
        <Route path="/kayit" element={<RegisterPage />} />

        <Route path="/admin" element={<AdminRoute />}>
          <Route index element={<AdminDashboardPage />} />
          <Route path="upload" element={<AdminUploadPage />} />
          <Route path="users" element={<AdminUsersPage />} />
          <Route path="records" element={<AdminRecordsPage />} />
          <Route path="quiz" element={<AdminQuizPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export default function App() {
  return <AppShell />;
}

