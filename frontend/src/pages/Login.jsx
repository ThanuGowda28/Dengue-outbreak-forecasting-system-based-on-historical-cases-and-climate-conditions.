import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { FiArrowLeft, FiLock } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import FormInput from "../components/FormInput.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { apiError } from "../utils/authValidation.js";

export default function Login() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState(null);
  const [verificationRequired, setVerificationRequired] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate(location.state?.from?.pathname || "/dashboard", { replace: true });
  }, [isAuthenticated, location.state, navigate]);

  function update(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError(null);
    setVerificationRequired(false);
    setSubmitting(true);
    try {
      await login(form);
      navigate(location.state?.from?.pathname || "/dashboard", { replace: true });
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
          <span className="eyebrow">WELCOME BACK</span>
          <h1>Sign in to DengueWatch</h1>
          <p>Access your community health dashboard.</p>
        </div>
        {location.state?.notice && (
          <AlertMessage message={location.state.notice} variant="success" />
        )}
        <AlertMessage message={error?.message} errors={error?.errors} />
        {verificationRequired && <p className="alert alert-info">Need a new link? <Link to="/verify-email" state={{ email: form.email }}>Resend verification email</Link></p>}
        <form onSubmit={submit}>
          <FormInput label="Email address" name="email" type="email" autoComplete="email" value={form.email} onChange={update} required />
          <FormInput label="Password" name="password" type="password" autoComplete="current-password" value={form.password} onChange={update} required />
          <div className="d-flex justify-content-end mb-3"><Link className="text-link small" to="/forgot-password">Forgot password?</Link></div>
          <button className="btn btn-primary w-100 btn-lg" type="submit" disabled={submitting}>
            {submitting && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="auth-switch">New to DengueWatch? <Link to="/register">Create an account</Link></p>
        <p className="auth-switch"><Link to="/admin/login">Administrator sign in</Link></p>
      </section>
    </main>
  );
}
