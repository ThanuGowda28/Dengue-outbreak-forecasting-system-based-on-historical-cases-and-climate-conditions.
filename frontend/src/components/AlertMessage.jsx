function errorText(errors) {
  if (!errors) return null;
  if (typeof errors === "string") return errors;
  if (Array.isArray(errors)) return errors.join(" ");
  return Object.values(errors).flat().join(" ");
}

export default function AlertMessage({ message, errors, variant = "danger", onDismiss }) {
  const detail = errorText(errors);
  if (!message && !detail) return null;
  return (
    <div className={`alert alert-${variant} alert-dismissible`} role={variant === "danger" ? "alert" : "status"}>
      {message && <div>{message}</div>}
      {detail && <div className={message ? "mt-1" : ""}>{detail}</div>}
      {onDismiss && <button type="button" className="btn-close" aria-label="Dismiss" onClick={onDismiss} />}
    </div>
  );
}
