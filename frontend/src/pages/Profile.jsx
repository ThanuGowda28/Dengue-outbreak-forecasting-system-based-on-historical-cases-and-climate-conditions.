import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FiKey, FiSave, FiShield, FiUser } from "react-icons/fi";
import AlertMessage from "../components/AlertMessage.jsx";
import FormInput from "../components/FormInput.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { apiError, passwordError, PHONE_PATTERN } from "../utils/authValidation.js";

export default function Profile() {
  const { user, updateProfile, changePassword } = useAuth();
  const [profile, setProfile] = useState({ full_name: "", email: "", phone: "", district: "", state: "" });
  const [password, setPassword] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [profileNotice, setProfileNotice] = useState(null);
  const [passwordNotice, setPasswordNotice] = useState(null);
  const [profileErrors, setProfileErrors] = useState({});
  const [passwordErrors, setPasswordErrors] = useState({});
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    setProfile({
      full_name: user?.full_name || user?.name || "",
      email: user?.email || "",
      phone: user?.phone || "",
      district: user?.district || "",
      state: user?.state || ""
    });
  }, [user]);

  function updateProfileField(event) {
    setProfile((current) => ({ ...current, [event.target.name]: event.target.value }));
    setProfileErrors((current) => ({ ...current, [event.target.name]: "" }));
  }
  function updatePasswordField(event) {
    setPassword((current) => ({ ...current, [event.target.name]: event.target.value }));
    setPasswordErrors((current) => ({ ...current, [event.target.name]: "" }));
  }

  async function saveProfile(event) {
    event.preventDefault();
    const errors = {};
    if (!profile.full_name.trim()) errors.full_name = "Name is required.";
    else if (profile.full_name.trim().length < 2 || profile.full_name.trim().length > 150) errors.full_name = "Name must be between 2 and 150 characters.";
    const phoneDigits = profile.phone.replace(/\D/g, "").length;
    if (profile.phone.trim().length > 32 || !PHONE_PATTERN.test(profile.phone.trim()) || phoneDigits < 7 || phoneDigits > 15) errors.phone = "Enter a valid phone number.";
    if (!profile.district.trim()) errors.district = "District is required.";
    else if (profile.district.trim().length > 100) errors.district = "District must be 100 characters or fewer.";
    if (!profile.state.trim()) errors.state = "State is required.";
    else if (profile.state.trim().length > 100) errors.state = "State must be 100 characters or fewer.";
    setProfileErrors(errors);
    if (Object.keys(errors).length) return;
    setSavingProfile(true);
    setProfileNotice(null);
    try {
      await updateProfile({
        full_name: profile.full_name.trim(),
        phone: profile.phone.trim(),
        district: profile.district.trim(),
        state: profile.state.trim()
      });
      setProfileNotice({ variant: "success", message: "Your profile has been updated." });
    } catch (error) {
      setProfileNotice(apiError(error));
    } finally {
      setSavingProfile(false);
    }
  }

  async function savePassword(event) {
    event.preventDefault();
    const errors = {};
    if (!password.current_password) errors.current_password = "Enter your current password.";
    if (!password.new_password) errors.new_password = "Enter a new password.";
    else errors.new_password = passwordError(password.new_password);
    if (!password.confirm_password) errors.confirm_password = "Confirm your new password.";
    else if (password.confirm_password !== password.new_password) errors.confirm_password = "Passwords do not match.";
    setPasswordErrors(errors);
    if (Object.values(errors).some(Boolean)) return;
    setSavingPassword(true);
    setPasswordNotice(null);
    try {
      const response = await changePassword(password);
      setPassword({ current_password: "", new_password: "", confirm_password: "" });
      setPasswordNotice({ variant: "success", message: response.message || "Your password has been changed." });
    } catch (error) {
      setPasswordNotice(apiError(error));
    } finally {
      setSavingPassword(false);
    }
  }

  return (
    <main className="content-shell container py-5">
      <div className="page-heading">
        <span className="eyebrow">ACCOUNT SETTINGS</span>
        <h1>Your profile</h1>
        <p>Manage your personal details and account security.</p>
      </div>
      <div className="row g-4">
        <div className="col-lg-6">
          <section className="settings-card">
            <div className="settings-card-heading"><span className="feature-icon"><FiUser /></span><div><h2>Personal information</h2><p>Update the details associated with your account.</p></div></div>
            <AlertMessage variant={profileNotice?.variant || "danger"} message={profileNotice?.message} errors={profileNotice?.errors} />
            <form onSubmit={saveProfile} noValidate>
              <FormInput label="Full name" name="full_name" autoComplete="name" value={profile.full_name} onChange={updateProfileField} error={profileErrors.full_name} required />
              <FormInput label="Email address" name="email" type="email" autoComplete="email" value={profile.email} disabled readOnly />
              <div className={`alert ${user?.is_verified ? "alert-success" : "alert-warning"}`} role="status">
                <FiShield className="me-2" />
                {user?.is_verified
                  ? "Email address verified"
                  : <>Email address not verified. <Link to="/verify-email" state={{ email: user?.email }}>Request a verification link</Link></>}
              </div>
              <FormInput label="Phone number" name="phone" type="tel" autoComplete="tel" value={profile.phone} onChange={updateProfileField} error={profileErrors.phone} required />
              <FormInput label="District" name="district" autoComplete="address-level2" value={profile.district} onChange={updateProfileField} error={profileErrors.district} required />
              <FormInput label="State" name="state" autoComplete="address-level1" value={profile.state} onChange={updateProfileField} error={profileErrors.state} required />
              <button className="btn btn-primary" type="submit" disabled={savingProfile}><FiSave className="me-2" />{savingProfile ? "Saving…" : "Save changes"}</button>
            </form>
          </section>
        </div>
        <div className="col-lg-6">
          <section className="settings-card">
            <div className="settings-card-heading"><span className="feature-icon"><FiKey /></span><div><h2>Change password</h2><p>Choose a strong password you have not used before.</p></div></div>
            <AlertMessage variant={passwordNotice?.variant || "danger"} message={passwordNotice?.message} errors={passwordNotice?.errors} />
            <form onSubmit={savePassword} noValidate>
              <FormInput label="Current password" name="current_password" type="password" autoComplete="current-password" value={password.current_password} onChange={updatePasswordField} error={passwordErrors.current_password} required />
              <FormInput label="New password" name="new_password" type="password" autoComplete="new-password" value={password.new_password} onChange={updatePasswordField} error={passwordErrors.new_password} hint="At least 8 characters with uppercase, lowercase, number and symbol." required />
              <FormInput label="Confirm new password" name="confirm_password" type="password" autoComplete="new-password" value={password.confirm_password} onChange={updatePasswordField} error={passwordErrors.confirm_password} required />
              <button className="btn btn-outline-primary" type="submit" disabled={savingPassword}>{savingPassword ? "Updating…" : "Update password"}</button>
            </form>
          </section>
        </div>
      </div>
    </main>
  );
}
