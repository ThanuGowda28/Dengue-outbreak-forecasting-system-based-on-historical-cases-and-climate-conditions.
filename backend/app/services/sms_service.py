import requests
from flask import current_app


class SmsDeliveryError(RuntimeError):
    """Raised when Twilio cannot accept an SMS message."""


def send_sms(recipient: str, message: str) -> None:
    account_sid = current_app.config.get("TWILIO_ACCOUNT_SID")
    auth_token = current_app.config.get("TWILIO_AUTH_TOKEN")
    from_number = current_app.config.get("TWILIO_FROM_NUMBER")
    if not all((account_sid, auth_token, from_number)):
        raise SmsDeliveryError("SMS delivery is not configured.")

    try:
        response = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
            auth=(account_sid, auth_token),
            data={"From": from_number, "To": recipient, "Body": message},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        status = getattr(error.response, "status_code", None)
        reason = f" (HTTP {status})" if status else ""
        raise SmsDeliveryError(f"Twilio SMS delivery failed{reason}.") from error
