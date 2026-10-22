import smtplib
import threading
import time
from collections import deque
from email.message import EmailMessage

from flask import current_app, request


_public_request_lock = threading.Lock()


def email_is_configured(recipient_setting: str | None = None) -> bool:
    required = (
        current_app.config.get("MAIL_SERVER"),
        current_app.config.get("MAIL_DEFAULT_SENDER"),
        current_app.config.get("MAIL_USERNAME"),
        current_app.config.get("MAIL_PASSWORD"),
    )
    return all(required) and (
        recipient_setting is None or bool(current_app.config.get(recipient_setting))
    )


def public_request_allowed(limit: int = 5) -> bool:
    now = time.monotonic()
    requests = current_app.extensions.setdefault("public_email_request_times", {})
    key = request.remote_addr or "unknown"
    with _public_request_lock:
        for address, timestamps in list(requests.items()):
            while timestamps and now - timestamps[0] >= 60:
                timestamps.popleft()
            if not timestamps:
                requests.pop(address, None)
        timestamps = requests.setdefault(key, deque())
        if len(timestamps) >= limit:
            return False
        timestamps.append(now)
        return True


def send_email(
    recipient: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> None:
    if not email_is_configured():
        raise RuntimeError("Email delivery is not configured.")

    message = EmailMessage()
    message["From"] = current_app.config["MAIL_DEFAULT_SENDER"]
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    server_name = current_app.config["MAIL_SERVER"]
    port = int(current_app.config.get("MAIL_PORT", 587))
    username = current_app.config.get("MAIL_USERNAME")
    password = current_app.config.get("MAIL_PASSWORD")
    timeout = int(current_app.config.get("MAIL_TIMEOUT_SECONDS", 15))
    if current_app.config.get("MAIL_USE_SSL", False):
        with smtplib.SMTP_SSL(server_name, port, timeout=timeout) as server:
            if username:
                server.login(username, password or "")
            server.send_message(message)
        return

    with smtplib.SMTP(server_name, port, timeout=timeout) as server:
        if current_app.config.get("MAIL_USE_TLS", True):
            server.starttls()
        if username:
            server.login(username, password or "")
        server.send_message(message)
