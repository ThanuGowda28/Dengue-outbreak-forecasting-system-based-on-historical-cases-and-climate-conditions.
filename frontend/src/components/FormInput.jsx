import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

export default function FormInput({
  label,
  name,
  type = "text",
  showPasswordToggle = false,
  value,
  onChange,
  error,
  hint,
  autoComplete,
  required = false,
  ...props
}) {
  const [passwordVisible, setPasswordVisible] = useState(false);
  const id = props.id || name;
  return (
    <div className="mb-3">
      <label className="form-label" htmlFor={id}>{label}{required && <span className="required-mark"> *</span>}</label>
      <div className={showPasswordToggle && type === "password" ? "password-input-wrap" : undefined}>
        <input
          {...props}
          id={id}
          name={name}
          type={showPasswordToggle && passwordVisible ? "text" : type}
          value={value}
          onChange={onChange}
          required={required}
          autoComplete={autoComplete}
          className={`form-control ${error ? "is-invalid" : ""} ${props.className || ""}`.trim()}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        />
        {showPasswordToggle && type === "password" && (
          <button
            type="button"
            className="password-visibility-toggle"
            onClick={() => setPasswordVisible((visible) => !visible)}
            aria-label={passwordVisible ? "Hide password" : "Show password"}
            aria-pressed={passwordVisible}
          >
            {passwordVisible ? <EyeOff size={17} /> : <Eye size={17} />}
          </button>
        )}
      </div>
      {error && <div className="invalid-feedback" id={`${id}-error`}>{error}</div>}
      {!error && hint && <div className="form-text" id={`${id}-hint`}>{hint}</div>}
    </div>
  );
}
