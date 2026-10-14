export default function FormInput({
  label,
  name,
  type = "text",
  value,
  onChange,
  error,
  hint,
  autoComplete,
  required = false,
  ...props
}) {
  const id = props.id || name;
  return (
    <div className="mb-3">
      <label className="form-label" htmlFor={id}>{label}{required && <span className="required-mark"> *</span>}</label>
      <input
        {...props}
        id={id}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        autoComplete={autoComplete}
        className={`form-control ${error ? "is-invalid" : ""} ${props.className || ""}`.trim()}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
      />
      {error && <div className="invalid-feedback" id={`${id}-error`}>{error}</div>}
      {!error && hint && <div className="form-text" id={`${id}-hint`}>{hint}</div>}
    </div>
  );
}
