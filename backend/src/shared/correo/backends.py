"""Adaptadores de proveedor de correo, elegidos por `EMAIL_BACKEND` en `.env`.

- console : imprime el correo (desarrollo / tests)
- smtp    : SMTP plano o STARTTLS (p. ej. MailHog en local)
- sendgrid: API HTTP de SendGrid
"""

from __future__ import annotations

import json
import logging
import smtplib
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from shared.config import get_settings

logger = logging.getLogger("cronos.correo")


def _solo_email(remitente: str) -> str:
    """`'CRONOS <x@y.com>'` -> `'x@y.com'`; deja intacto si ya es una dirección."""
    if "<" in remitente and ">" in remitente:
        return remitente.split("<", 1)[1].split(">", 1)[0].strip()
    return remitente.strip()


def _mensaje(asunto: str, a: str, html: str, texto: str) -> MIMEMultipart:
    s = get_settings()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = s.email_from
    msg["To"] = a
    msg.attach(MIMEText(texto, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def enviar_raw(asunto: str, a: str, html: str, texto: str, *, envio_id: int | None = None) -> str | None:
    """Envía el correo. Devuelve el `message_id` del proveedor cuando lo hay
    (solo SendGrid lo expone — vía cabecera `X-Message-Id`) para que 014 lo
    concilie con los webhooks de entrega (`envio.proveedor_message_id`).
    `envio_id` viaja como `custom_args` a SendGrid — no cambia el envío en sí,
    solo permite conciliar por nuestro propio id como respaldo si el
    `message_id` no calza exacto (SendGrid le añade un sufijo por destinatario)."""
    s = get_settings()
    backend = s.email_backend.lower()

    if backend == "console":
        logger.info("[correo:console] Para: %s | Asunto: %s\n%s", a, asunto, texto)
        return None

    if backend == "smtp":
        msg = _mensaje(asunto, a, html, texto)
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as srv:
            if s.smtp_tls:
                srv.starttls()
            if s.smtp_user:
                srv.login(s.smtp_user, s.smtp_password)
            srv.send_message(msg)
        return None

    if backend == "sendgrid":
        remitente = s.sendgrid_from_email or _solo_email(s.email_from)
        payload = {
            "personalizations": [{"to": [{"email": a}]}],
            "from": {"email": remitente},
            "subject": asunto,
            "content": [
                {"type": "text/plain", "value": texto},
                {"type": "text/html", "value": html},
            ],
        }
        if envio_id is not None:
            payload["custom_args"] = {"envio_id": str(envio_id)}
        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {s.sendgrid_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                logger.info("[correo:sendgrid] %s -> %s (HTTP %s)", asunto, a, resp.status)
                return resp.headers.get("X-Message-Id")
        except urllib.error.HTTPError as exc:  # noqa: PERF203
            detalle = exc.read().decode("utf-8", "replace")
            logger.error("[correo:sendgrid] rechazado (HTTP %s): %s", exc.code, detalle)
            raise

    raise RuntimeError(f"EMAIL_BACKEND desconocido: {s.email_backend}")
