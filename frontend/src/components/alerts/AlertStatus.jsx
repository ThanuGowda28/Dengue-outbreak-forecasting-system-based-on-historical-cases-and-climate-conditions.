export default function AlertStatus({ status, type }) {
  const channel = type === "email" ? "Email" : type === "sms" ? "SMS" : "In-app";
  const text = status === "sent"
    ? type === "in_app" ? "✅ In-app notification" : `✅ ${channel} sent successfully`
    : status === "failed"
      ? `❌ ${channel} failed. Please try again later.`
      : status === "retrying"
        ? "Retrying delivery…"
        : status === "sending"
          ? "Sending…"
          : "Queued";
  return <span className={`alert-status alert-status-${status}`} role="status">{text}</span>;
}
