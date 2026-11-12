import { lazy, Suspense } from "react";
import { Route, Routes, useLocation, Link } from "react-router-dom";
import { useAuth } from "./context/AuthContext.jsx";
import Navbar from "./components/Navbar.jsx";
import Footer from "./components/Footer.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import LoadingSpinner from "./components/LoadingSpinner.jsx";
import AppErrorBoundary from "./components/AppErrorBoundary.jsx";
import { FiArrowLeft } from "react-icons/fi";

const HomePage = lazy(() => import("./pages/HomePage.jsx"));
const Login = lazy(() => import("./pages/Login.jsx"));
const AdminLogin = lazy(() => import("./pages/AdminLogin.jsx"));
const Register = lazy(() => import("./pages/Register.jsx"));
const VerifyEmail = lazy(() => import("./pages/VerifyEmail.jsx"));
const ProfileWorkspace = lazy(() => import("./pages/ProfileWorkspace.jsx"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword.jsx"));
const ResetPassword = lazy(() => import("./pages/ResetPassword.jsx"));
const InformationPage = lazy(() => import("./pages/InformationPage.jsx"));
const FAQ = lazy(() => import("./pages/FAQ.jsx"));
const Contact = lazy(() => import("./pages/Contact.jsx"));
const DashboardLayout = lazy(() => import("./layouts/DashboardLayout.jsx"));
const Dashboard = lazy(() => import("./pages/Dashboard.jsx"));
const AdminDashboard = lazy(() => import("./pages/AdminDashboard.jsx"));
const Prediction = lazy(() => import("./pages/Prediction.jsx"));
const Forecasting = lazy(() => import("./pages/Forecasting.jsx"));
const Weather = lazy(() => import("./pages/WeatherDashboard.jsx"));
const RiskMap = lazy(() => import("./pages/RiskMap.jsx"));
const History = lazy(() => import("./pages/History.jsx"));
const Reports = lazy(() => import("./pages/Reports.jsx"));
const HospitalFinder = lazy(() => import("./pages/HospitalFinder.jsx"));
const Settings = lazy(() => import("./pages/Settings.jsx"));
const Alerts = lazy(() => import("./pages/Alerts.jsx"));
const AdminAlerts = lazy(() => import("./pages/AdminAlerts.jsx"));
const AdminWorkspace = lazy(() => import("./pages/AdminWorkspace.jsx"));
const AdminHospitals = lazy(() => import("./pages/AdminHospitals.jsx"));

function DashboardHome() {
  const { user } = useAuth();
  return user?.role?.toLowerCase() === "admin" ? <AdminDashboard /> : <Dashboard />;
}

function NotFound() {
  return (
    <main className="not-found-page">
      <span className="not-found-code">404</span>
      <h1>We couldn’t find that page.</h1>
      <p>Check the address or return to the project home page.</p>
      <Link className="btn btn-primary" to="/"><FiArrowLeft className="me-2" />Back to home</Link>
    </main>
  );
}

function AppRoutes() {
  const { loading } = useAuth();
  const location = useLocation();
  const dashboardMode = [
    "/dashboard", "/admin", "/prediction", "/forecasting", "/weather", "/risk-map",
    "/history", "/profile", "/settings", "/alerts", "/reports", "/hospitals", "/users",
    "/admin/alerts",
    "/admin/hospitals",
    "/datasets", "/climate-data", "/train-model"
  ].some((path) => location.pathname === path || location.pathname.startsWith(`${path}/`));
  if (loading) return <LoadingSpinner label="Checking your session…" />;

  return (
    <>
      {!dashboardMode && <Navbar />}
      <Suspense fallback={<LoadingSpinner label="Loading page…" />}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/about" element={<InformationPage />} />
          <Route path="/climate" element={<InformationPage />} />
          <Route path="/symptoms" element={<InformationPage />} />
          <Route path="/prevention" element={<InformationPage />} />
          <Route path="/privacy-policy" element={<InformationPage />} />
          <Route path="/terms-of-use" element={<InformationPage />} />
          <Route path="/faq" element={<FAQ />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/login" element={<Login />} />
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<DashboardLayout />}>
              <Route path="/dashboard" element={<DashboardHome />} />
              <Route path="/prediction" element={<Prediction />} />
              <Route path="/forecasting" element={<Forecasting />} />
              <Route path="/weather" element={<Weather />} />
              <Route path="/risk-map" element={<RiskMap />} />
              <Route path="/history" element={<History />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/profile" element={<ProfileWorkspace />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/hospitals" element={<HospitalFinder />} />
            </Route>
          </Route>
          <Route element={<ProtectedRoute roles={["admin"]} />}>
            <Route element={<DashboardLayout />}>
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
              <Route path="/users" element={<AdminWorkspace />} />
              <Route path="/admin/predictions" element={<AdminWorkspace />} />
              <Route path="/datasets" element={<AdminWorkspace />} />
              <Route path="/climate-data" element={<AdminWorkspace />} />
              <Route path="/train-model" element={<AdminWorkspace />} />
              <Route path="/admin/alerts" element={<AdminAlerts />} />
              <Route path="/admin/hospitals" element={<AdminHospitals />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
      {!dashboardMode && <Footer />}
    </>
  );
}

export default function App() {
  return (
    <AppErrorBoundary>
      <AppRoutes />
    </AppErrorBoundary>
  );
}
