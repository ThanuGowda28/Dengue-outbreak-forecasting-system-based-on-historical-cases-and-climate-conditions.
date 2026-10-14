import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { FiArrowLeft, FiMail } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import FormInput from "../components/FormInput.jsx";
import { resendEmailVerification, verifyEmail } from "../services/authService.js";
import {
  isValidVerificationEmail,
  parseEmailVerificationQuery,
  verificationErrorMessage
} from "../utils/emailVerification.js";

export default function VerifyEmail() {
  const location = useLocation();
  const { token, email: queryEmail } = parseEmailVerificationQuery(location.search);
  const [email, setEmail] = useState(location.state?.email || queryEmail);
  const [status, setStatus] = useState(token ? "ready" : "missing");
  const [message, setMessage] = useState(location.state?.message || "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitVerification() {
    setBusy(true);
    setError("");
    setMessage("");
    setStatus("verifying");
    try {
      const response = await verifyEmail(token);
      setStatus("verified");
      setMessage(response.message);
    } catch (requestError) {
      setStatus("failed");
      setError(verificationErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function resend(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (!isValidVerificationEmail(email)) {
      setError("Enter a valid email address.");
      return;
    }
    setBusy(true);
    try {
      const response = await resendEmailVerification(email.trim());
      setMessage(response.message);
    } catch (requestError) {
      setError(verificationErrorMessage(requestError, "A verification email could not be requested."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page container">
      <section className="auth-card">
        <Link className="back-link" to="/"><FiArrowLeft /> Back to home</Link>
        <div className="auth-heading">
          <span className="auth-icon"><FiMail /></span>
          <span className="eyebrow">EMAIL VERIFICATION</span>
          <h1>Verify your email address</h1>
          <p>Confirm your email before signing in to DengueWatch.</p>
        </div>
        {message && <p className="alert alert-success" role="status">{message}</p>}
        {error && <AlertMessage message={error} />}
        {token && status !== "verified" && (
          <button
            className="btn btn-primary w-100 mb-3"
            type="button"
            onClick={submitVerification}
            disabled={busy || status === "verifying"}
          >
            {status === "verifying" ? "Verifying…" : "Verify email"}
          </button>
        )}
        {status === "verified" ? (
          <Link className="btn btn-primary w-100" to="/login">Continue to sign in</Link>
        ) : (
          <form onSubmit={resend}>
            <p className="text-secondary">Didn’t receive a link, or has it expired? Request another one.</p>
            <FormInput
              label="Email address"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <button className="btn btn-outline-primary w-100" type="submit" disabled={busy}>
              {busy ? "Please wait…" : "Resend verification email"}
            </button>
          </form>
        )}
        <p className="auth-switch"><Link to="/login">Return to sign in</Link></p>
      </section>
    </main>
  );
}
