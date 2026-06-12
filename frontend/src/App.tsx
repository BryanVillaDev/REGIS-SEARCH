import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { useAuth } from "./state/AuthContext";
import { JobsPage } from "./pages/JobsPage";
import { LoginPage } from "./pages/LoginPage";
import { RecordPage } from "./pages/RecordPage";
import { SearchPage } from "./pages/SearchPage";

function ProtectedApp() {
  const { token, loading } = useAuth();

  if (loading) {
    return <div className="screen-center">Cargando sesion...</div>;
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/records/:aninuip" element={<RecordPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  const { token } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={token ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/*" element={<ProtectedApp />} />
    </Routes>
  );
}
