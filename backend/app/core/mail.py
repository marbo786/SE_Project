from email.message import EmailMessage
from pathlib import Path
import smtplib
import secrets
from .config import get_settings

def deliver_challenge(email: str, token: str, purpose: str):
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = email
    message["Subject"] = "Reset your SRS Reviewer password" if purpose == "reset" else "Verify your SRS Reviewer email"
    route = "reset-password" if purpose == "reset" else "verify-email"
    message.set_content(f"Open {settings.PUBLIC_URL}/{route}#token={token}\nThis link expires in 30 minutes. If you did not request it, ignore this message.")
    if settings.SMTP_HOST:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    elif settings.APP_ENV == "development":
        directory = Path(settings.MAIL_SINK_DIR)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{secrets.token_hex(16)}.eml").write_bytes(message.as_bytes())
    else:
        raise RuntimeError("Email delivery is not configured")
