"""Endpoint public de formulaire de contact (PDS-122.1)."""

import logging
import smtplib
import time
from email.message import EmailMessage

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.presentation.api.v1.schemas import ContactRequest

logger = logging.getLogger(__name__)
contact_router = APIRouter()

# Rate-limit simple par IP : max 3 requêtes / 60 secondes
_contact_ratelimit: dict[str, list[float]] = {}


def _rate_limit_ok(ip: str) -> bool:
    now = time.monotonic()
    window: list[float] = [t for t in _contact_ratelimit.get(ip, []) if now - t < 60]
    _contact_ratelimit[ip] = window
    if len(window) >= 3:
        return False
    window.append(now)
    return True


@contact_router.post("/contact", status_code=200)
async def submit_contact(request: Request, body: ContactRequest) -> dict[str, str]:
    """Reçoit un message du formulaire de contact et l'envoie par email.

    Anti-spam : rate-limit par IP (3 req/min), toujours 200 pour éviter l'énumération.
    """
    _status_sent: dict[str, str] = {"status": "sent"}

    client_ip = request.client.host if request.client else "unknown"

    if not _rate_limit_ok(client_ip):
        return _status_sent

    settings = get_settings()

    smtp_host = settings.smtp_host
    smtp_port = settings.smtp_port
    smtp_user = settings.smtp_user
    smtp_password = settings.smtp_password
    smtp_from = settings.smtp_from

    if not smtp_host or not smtp_user:
        logger.warning("SMTP non configuré, contact non envoyé.")
        return _status_sent

    subject_map: dict[str, str] = {
        "surveillance": "Problème de surveillance",
        "paiement": "Problème de paiement",
        "donnees": "Question sur les données",
        "technique": "Problème technique",
        "autre": "Autre demande",
    }

    sujet_label = subject_map.get(body.concerne, body.concerne)

    msg = EmailMessage()
    msg["Subject"] = f"[PDS-Portail] Contact: {sujet_label}"
    msg["From"] = smtp_from
    msg["To"] = "schopfer@moustik.site"
    msg["Reply-To"] = body.email
    msg.set_content(
        f"Message reçu depuis le formulaire de contact PDS-Portail.\n\n"
        f"Concerne : {sujet_label}\n"
        f"Email de réponse : {body.email}\n\n"
        f"Message :\n{body.message}\n"
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password or "")
            server.send_message(msg)
    except Exception as exc:
        logger.exception("Erreur envoi email contact: %s", exc)
        return _status_sent

    return _status_sent
