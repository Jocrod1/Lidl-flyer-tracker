"""Send email notifications via SMTP.

Configuration comes from environment variables so credentials never live in
the repo:

    LIDL_SMTP_HOST      e.g. smtp.gmail.com
    LIDL_SMTP_PORT      default 587
    LIDL_SMTP_USER      login (often same as from-address)
    LIDL_SMTP_PASSWORD  app password / SMTP password
    LIDL_SMTP_FROM      defaults to LIDL_SMTP_USER
    LIDL_SMTP_USE_TLS   "1"/"0", default "1"

If LIDL_SMTP_HOST is unset, `send_email` prints the message instead of
sending it (dry-run), so the watcher can be exercised without credentials.
"""

from __future__ import annotations

import dataclasses
import os
import smtplib
from email.message import EmailMessage


@dataclasses.dataclass(frozen=True)
class SmtpConfig:
    host: str | None
    port: int
    user: str | None
    password: str | None
    from_addr: str | None
    use_tls: bool

    @classmethod
    def from_env(cls) -> "SmtpConfig":
        host = os.environ.get("LIDL_SMTP_HOST")
        user = os.environ.get("LIDL_SMTP_USER")
        return cls(
            host=host,
            port=int(os.environ.get("LIDL_SMTP_PORT", "587")),
            user=user,
            password=os.environ.get("LIDL_SMTP_PASSWORD"),
            from_addr=os.environ.get("LIDL_SMTP_FROM", user),
            use_tls=os.environ.get("LIDL_SMTP_USE_TLS", "1") != "0",
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.from_addr)


def send_email(
    to_addr: str,
    subject: str,
    body: str,
    config: SmtpConfig | None = None,
) -> bool:
    """Send a plaintext email. Returns True if it was actually sent.

    Falls back to printing the message when SMTP is not configured, so the
    watcher remains runnable (and testable) without real credentials.
    """
    config = config or SmtpConfig.from_env()

    if not config.is_configured:
        print("[email:dry-run] SMTP not configured, printing instead:\n")
        print(f"To: {to_addr}\nSubject: {subject}\n\n{body}\n")
        return False

    message = EmailMessage()
    message["From"] = config.from_addr
    message["To"] = to_addr
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(config.host, config.port, timeout=30) as smtp:
        if config.use_tls:
            smtp.starttls()
        if config.user and config.password:
            smtp.login(config.user, config.password)
        smtp.send_message(message)

    return True
