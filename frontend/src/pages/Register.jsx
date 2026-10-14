import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FiArrowLeft, FiUserPlus } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import FormInput from "../components/FormInput.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { apiError, EMAIL_PATTERN, passwordError, PHONE_PATTERN } from "../utils/authValidation.js";

const initialForm = {
  full_name: "",
  email: "",
  phone: "",
  district: "",
  state: "",
  password: "",
  confirm_password: ""
};

export default function Register() {
  const { register, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState({});
  const [requestError, setRequestError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate("/dashboard", { replace: true });
  }, [isAuthenticated, navigate]);

  function update(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: "" }));
  }

  function validate() {
    const next = {};
    if (!form.full_name.trim()) next.full_name = "Enter your full name.";
    else if (form.full_name.trim().length < 2 || form.full_name.trim().length > 150) {
      next.full_name = "Name must be between 2 and 150 characters.";
    }
    if (!form.email.trim()) next.email = "Enter your email address.";
    else if (form.email.trim().length > 254 || !EMAIL_PATTERN.test(form.email.trim())) next.email = "Enter a valid email address.";
    if (!form.phone.trim()) next.phone = "Enter your phone number.";
    else {
      const digits = form.phone.replace(/\D/g, "").length;
      if (form.phone.trim().length > 32 || !PHONE_PATTERN.test(form.phone.trim()) || digits < 7 || digits > 15) {
        next.phone = "Enter a valid phone number.";
      }
    }
    if (!form.district.trim()) next.district = "Enter your district.";
    else if (form.district.trim().length > 100) next.district = "District must be 100 characters or fewer.";
    if (!form.state.trim()) next.state = "Enter your state.";
    else if (form.state.trim().length > 100) next.state = "State must be 100 characters or fewer.";
    if (!form.password) next.password = "Create a password.";
    else next.password = passwordError(form.password);
    if (!form.confirm_password) next.confirm_password = "Confirm your password.";
    else if (form.password !== form.confirm_password) next.confirm_password = "Passwords do not match.";
    setErrors(next);
    return Object.values(next).every((message) => !message);
  }

  async function submit(event) {
    event.preventDefault();
    setRequestError(null);
    if (!validate()) return;
    setSubmitting(true);
    try {
      await register({
        ...form,
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        district: form.district.trim(),
        state: form.state.trim()
      });
      navigate("/verify-email", {
        replace: true,
        state: { email: form.email.trim() }
      });
    } catch (error) {
      const result = apiError(error);
      result.accountCreated = Boolean(error.response?.data?.account_created);
      setRequestError(result);
      if (result.errors && typeof result.errors === "object") {
        setErrors((current) => ({ ...current, ...Object.fromEntries(Object.entries(result.errors).map(([key, value]) => [key, Array.isArray(value) ? value[0] : value])) }));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page container">
      <section className="auth-card auth-card-wide">
        <Link className="back-link" to="/"><FiArrowLeft /> Back to home</Link>
        <div className="auth-heading">
          <span className="auth-icon"><FiUserPlus /></span>
          <span className="eyebrow">JOIN THE COMMUNITY</span>
          <h1>Create your account</h1>
          <p>Get access to DengueWatch community insights.</p>
        </div>
        <AlertMessage message={requestError?.message} errors={requestError?.errors && typeof requestError.errors !== "object" ? requestError.errors : null} />
        {requestError?.accountCreated && <Link className="text-link d-block mb-3" to="/verify-email" state={{ email: form.email.trim() }}>Continue to request another verification email</Link>}
        <form onSubmit={submit} noValidate>
          <FormInput label="Full name" name="full_name" autoComplete="name" value={form.full_name} onChange={update} error={errors.full_name} required />
          <FormInput label="Email address" name="email" type="email" autoComplete="email" value={form.email} onChange={update} error={errors.email} required />
          <FormInput label="Phone number" name="phone" type="tel" autoComplete="tel" value={form.phone} onChange={update} error={errors.phone} hint="Include your country code if needed." required />
          <FormInput label="District" name="district" autoComplete="address-level2" value={form.district} onChange={update} error={errors.district} required />
          <FormInput label="State" name="state" autoComplete="address-level1" value={form.state} onChange={update} error={errors.state} required />
          <FormInput label="Password" name="password" type="password" autoComplete="new-password" value={form.password} onChange={update} error={errors.password} hint="At least 8 characters with uppercase, lowercase, number and symbol." required />
          <FormInput label="Confirm password" name="confirm_password" type="password" autoComplete="new-password" value={form.confirm_password} onChange={update} error={errors.confirm_password} required />
          <button className="btn btn-primary w-100 btn-lg mt-2" type="submit" disabled={submitting}>
            {submitting && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
