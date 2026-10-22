import { useState } from "react";
import { Link } from "react-router-dom";
import { FiArrowLeft, FiMail } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import FormInput from "../components/FormInput.jsx";
import { EMAIL_PATTERN } from "../utils/authValidation.js";
import { requestPasswordReset } from "../services/authService.js";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [demoResetUrl, setDemoResetUrl] = useState("");

  async function submit(event) {
    event.preventDefault();
    if (!EMAIL_PATTERN.test(email.trim())) {
      setError("Enter a valid email address.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const response = await requestPasswordReset(email.trim());
      setDemoResetUrl(response.demo_reset_url || "");
      setSubmitted(true);
    } catch (requestError) {
      setError(requestError.response?.data?.message || requestError.message || "Password recovery is currently unavailable. Please try again later.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page container">
      <section className="auth-card">
        <Link className="back-link" to="/login"><FiArrowLeft /> Back to sign in</Link>
        <div className="auth-heading">
          <span className="auth-icon"><FiMail /></span>
          <span className="eyebrow">ACCOUNT RECOVERY</span>
          <h1>Forgot your password?</h1>
          <p>Enter your email address to receive a secure, time-limited reset link.</p>
        </div>
        {submitted ? (
          <>
            <AlertMessage
              variant="success"
              message={demoResetUrl
                ? "SMTP is unavailable. A one-hour local demo reset link is ready."
                : "If an account exists for that email, password reset instructions have been sent."}
            />
            {demoResetUrl && (
              <a className="text-link d-block mb-3" href={demoResetUrl}>
                Open local demo password reset
              </a>
            )}
          </>
        ) : (
          <form onSubmit={submit} noValidate>
            {error && <AlertMessage message={error} />}
            <FormInput label="Email address" name="email" type="email" autoComplete="email" value={email} onChange={(event) => { setEmail(event.target.value); setError(""); }} required />
            <button className="btn btn-primary w-100 btn-lg" type="submit" disabled={loading}>{loading ? "Sending…" : "Continue"}</button>
          </form>
        )}
        <p className="auth-switch">Remembered your password? <Link to="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
