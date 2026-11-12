import { sanitizeUserMessage } from "../utils/apiErrors.js";

function errorText(errors) {
  if (!errors) return null;
  if (typeof errors === "string") return sanitizeUserMessage(errors);
  if (Array.isArray(errors)) return errors.map((error) => sanitizeUserMessage(error)).join(" ");
  return Object.values(errors).flat().map((error) => sanitizeUserMessage(error)).join(" ");
}

export default function AlertMessage({ message, errors, variant = "danger", onDismiss }) {
  const safeMessage = sanitizeUserMessage(message, "");
  const detail = errorText(errors);
  if (!safeMessage && !detail) return null;
  return (
    <div className={`alert alert-${variant} alert-dismissible`} role={variant === "danger" ? "alert" : "status"}>
      {safeMessage && <div>{safeMessage}</div>}
      {detail && <div className={safeMessage ? "mt-1" : ""}>{detail}</div>}
      {onDismiss && <button type="button" className="btn-close" aria-label="Dismiss" onClick={onDismiss} />}
    </div>
  );
}
