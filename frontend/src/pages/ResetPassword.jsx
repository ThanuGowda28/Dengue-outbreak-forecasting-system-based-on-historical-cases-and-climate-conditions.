import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FiArrowLeft, FiKey } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import FormInput from "../components/FormInput.jsx";
import { passwordError } from "../utils/authValidation.js";
import { resetPassword } from "../services/authService.js";

export default function ResetPassword() {
  const [form, setForm] = useState({ password: "", confirm_password: "" });
  const [errors, setErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function update(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
    setErrors((current) => ({ ...current, [event.target.name]: "" }));
  }

  async function submit(event) {
    event.preventDefault();
    const next = {};
    if (!form.password) next.password = "Create a new password.";
    else next.password = passwordError(form.password);
    if (!form.confirm_password) next.confirm_password = "Confirm your new password.";
    else if (form.password !== form.confirm_password) next.confirm_password = "Passwords do not match.";
    setErrors(next);
    if (!token) {
      setError("This password reset link is missing its token. Request a new link.");
      return;
    }
    if (Object.values(next).every((value) => !value)) {
      setLoading(true);
      setError("");
      try {
        await resetPassword({ ...form, token });
        setSubmitted(true);
      } catch (requestError) {
        setError(requestError.response?.data?.message || "Password could not be reset. Request a new link and try again.");
      } finally {
        setLoading(false);
      }
    }
  }

  return (
    <main className="auth-page container">
      <section className="auth-card">
        <Link className="back-link" to="/login"><FiArrowLeft /> Back to sign in</Link>
        <div className="auth-heading">
          <span className="auth-icon"><FiKey /></span>
          <span className="eyebrow">ACCOUNT RECOVERY</span>
          <h1>Choose a new password</h1>
          <p>Set a strong password using your secure, time-limited reset link.</p>
        </div>
        {submitted ? (
          <AlertMessage variant="success" message="Your password has been reset. You can now sign in with the new password." />
        ) : (
          <form onSubmit={submit} noValidate>
            {error && <AlertMessage message={error} />}
            <FormInput label="New password" name="password" type="password" autoComplete="new-password" value={form.password} onChange={update} error={errors.password} hint="At least 8 characters with uppercase, lowercase, number and symbol." required />
            <FormInput label="Confirm new password" name="confirm_password" type="password" autoComplete="new-password" value={form.confirm_password} onChange={update} error={errors.confirm_password} required />
            <button className="btn btn-primary w-100 btn-lg" type="submit" disabled={loading}>{loading ? "Saving…" : "Set new password"}</button>
          </form>
        )}
      </section>
    </main>
  );
}
