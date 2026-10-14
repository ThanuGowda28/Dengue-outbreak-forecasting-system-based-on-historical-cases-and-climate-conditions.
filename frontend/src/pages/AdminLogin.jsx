import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FiArrowLeft, FiLock } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import FormInput from "../components/FormInput.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { apiError } from "../utils/authValidation.js";

export default function AdminLogin() {
  const { adminLogin, isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState(null);
  const [verificationRequired, setVerificationRequired] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated && user?.role?.toLowerCase() === "admin") {
      navigate("/admin/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate, user?.role]);

  async function submit(event) {
    event.preventDefault();
    setError(null);
    setVerificationRequired(false);
    setSubmitting(true);
    try {
      await adminLogin(form);
      navigate("/admin/dashboard", { replace: true });
    } catch (requestError) {
      setError(apiError(requestError));
      setVerificationRequired(requestError.response?.data?.error === "email_not_verified");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page container">
      <section className="auth-card">
        <Link className="back-link" to="/"><FiArrowLeft /> Back to home</Link>
        <div className="auth-heading">
          <span className="auth-icon"><FiLock /></span>
          <span className="eyebrow">ADMINISTRATOR ACCESS</span>
          <h1>Sign in to the admin workspace</h1>
          <p>Use an existing administrator account.</p>
        </div>
        <AlertMessage message={error?.message} errors={error?.errors} />
        {verificationRequired && <p className="alert alert-info">Need a new link? <Link to="/verify-email" state={{ email: form.email }}>Resend verification email</Link></p>}
        <form onSubmit={submit}>
          <FormInput label="Email address" name="email" type="email" autoComplete="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} required />
          <FormInput label="Password" name="password" type="password" autoComplete="current-password" value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} required />
          <button className="btn btn-primary w-100 btn-lg" type="submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Administrator sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
