"""
Validation cryptographique des webhooks Polar (TDD, ADR-032).

Cette fonction garantit la sécurité cryptographique du webhook et est protégée contre
9 failles documentées dans ADR-032 (Sécurité des webhooks Polar — attaques et mitigations).

Failles mitigées :
1. Raw Body (ADR-032 #1) — hachage sur les bytes exacts (pas JSON parsé)
2. Timing Attacks (ADR-032 #2) — comparaison constant-time via hmac.compare_digest()
3. Replay Attacks (ADR-032 #3) — vérification du timestamp (max 5 min)
4. Idempotence (ADR-032 #4) — webhook reçu 2x ne crée pas de doublons (via UNIQUE DB)
5. Malformed Header (ADR-032 #5) — parsing format "sha256=..."
6. Invalid Hex (ADR-032 #6) — validation hexadécimale signature
7. Clock Skew (ADR-032 #10) — tolérance ±60s futur
8. Wrong Secret (ADR-032 #11) — rejet si secret configuré erroné
9. Event Dedup (ADR-032 #12) — webhook dupliqué accepté (DB gérera UNIQUE)

Approche TDD : 16 tests d'attaque écrits avant l'implémentation, déterministe avec
now_provider injectable (pas de datetime.now() nu).

Référence complète : ADR-032, SPEC-011 § 3.3, PDS-89-Security.
"""

import hmac
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, ConfigDict


class WebhookVerificationError(Exception):
    """Exception levée lors d'une vérification de signature échouée ou d'un rejeu détecté."""

    pass


class PolarWebhookData(BaseModel):
    """Payload de données spécifique au type d'événement."""

    model_config = ConfigDict(
        extra="allow"
    )  # Permettre des champs additionnels (Polar peut en ajouter)


class PolarWebhookEvent(BaseModel):
    """
    Modèle Pydantic pour un événement webhook Polar.

    Valide automatiquement la structure après signature vérifiée.
    Supporte order.created et subscription.cancelled.
    """

    id: str
    type: str  # "order.created", "subscription.cancelled", etc.
    data: dict[str, Any]
    timestamp: str

    model_config = ConfigDict(extra="allow")  # Tolérer les champs additionnels de Polar


def verify_polar_webhook(
    body: bytes,
    signature_header: str,
    secret: str,
    timestamp: str,
    now_provider: Callable[[], datetime] | None = None,
) -> bool:
    """
    Vérifie la signature HMAC-SHA256 d'un webhook Polar et valide le timestamp.

    Cette fonction implémente les 9 mitigations de sécurité décrites dans ADR-032.

    Args:
        body: Corps brut de la requête HTTP (bytes) — JAMAIS parsé JSON avant signature.
              Faille #1 (Raw Body) : utiliser request.body() ou await request.body(),
              pas request.json().
        signature_header: Valeur du header X-Polar-Signature (format: "sha256=<hexdigest>").
                         Failles #5, #6 : parsing et validation hex format.
        secret: Secret webhook configuré (POLAR_WEBHOOK_SECRET).
                Faille #11 (Wrong Secret) : testé avec secret erroné doit échouer.
        timestamp: Timestamp ISO 8601 du webhook (extrait de payload ou header).
                  Failles #3, #10 : rejecter si > 5 min ou > 60s futur (clock skew).
        now_provider: Fonction injectable pour les tests (par défaut: datetime.now(timezone.utc)).
                      Permet le déterminisme strict en tests sans mock global.
                      Exemple : lambda: datetime.now(timezone.utc)

    Returns:
        True si signature valide ET timestamp OK (5 min max + clock skew ±60s).

    Raises:
        WebhookVerificationError: Si signature invalide, timestamp expiré, ou format malformé.

    Sécurité mitigée (ADR-032) :
        - Signature sur body BRUT (bytes), pas JSON parsé (Faille #1) ✓
        - hmac.compare_digest() timing-safe (Faille #2) ✓
        - Timestamp vérification 5 min + ±60s (Failles #3, #10) ✓
        - Webhook 2x accepté par verify() (DB gérera UNIQUE, Failles #4, #12) ✓
        - Validation format "sha256=<64 hex>" (Failles #5, #6) ✓
        - Secret erroné rejette (Faille #11) ✓
        - Aucune info leak par timing (constant-time) ✓

    Exemple:
        # Dans un endpoint FastAPI :
        @app.post("/webhooks/polar")
        async def webhook_polar(request: Request):
            body = await request.body()
            sig = request.headers.get("x-polar-signature")
            event_data = request.json()  # JSON seulement APRÈS vérification

            verify_polar_webhook(
                body=body,
                signature_header=sig,
                secret=settings.polar_webhook_secret,
                timestamp=event_data["timestamp"]
            )

            # Traiter l'événement (safe)
            event = PolarWebhookEvent(**event_data)
            if event.type == "order.created":
                # Créer watcher, etc.
                pass

    Tests TDD (16 tests dans test_webhooks_security.py) :
        - 2 tests Raw Body
        - 3 tests Timing Attacks
        - 4 tests Replay Attacks
        - 1 test Idempotence
        - 1 test Malformed Header
        - 1 test Wrong Secret
        - 1 test Nominal
        - 2 tests Pydantic parsing
        - 1 test Pydantic reject
    """
    if now_provider is None:

        def _default_now_provider() -> datetime:
            return datetime.now(UTC)

        now_provider = _default_now_provider

    # 1) Vérifier d'abord le timestamp pour réduire les surfaces d'attaque temporelle.
    try:
        webhook_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WebhookVerificationError("Invalid timestamp format") from exc

    now = now_provider()
    if now - webhook_time > timedelta(minutes=5):
        raise WebhookVerificationError("Webhook too old (replay attack)")
    if webhook_time - now > timedelta(seconds=60):
        raise WebhookVerificationError("Webhook timestamp too far in future")

    # 2) Parser le header attendu puis valider une empreinte SHA256 hexadécimale.
    if not signature_header.startswith("sha256="):
        raise WebhookVerificationError("Invalid signature header format")

    hex_signature = signature_header[7:]
    if len(hex_signature) != 64:
        raise WebhookVerificationError("Invalid signature hex format")
    if not all(char in "0123456789abcdef" for char in hex_signature):
        raise WebhookVerificationError("Invalid signature hex format")

    # 3) Calculer le HMAC sur le body brut (bytes), sans re-sérialisation JSON.
    computed_hmac = hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()

    # 4) Comparaison en temps constant contre les attaques de timing.
    if not hmac.compare_digest(computed_hmac, hex_signature):
        raise WebhookVerificationError("Invalid signature")

    return True
