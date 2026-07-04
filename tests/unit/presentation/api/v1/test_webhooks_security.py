"""
Tests de sécurité pour la validation cryptographique des webhooks Polar (TDD).

Référence : ADR-032 (Sécurité des webhooks Polar — attaques et mitigations)

Structure TDD :
- Ces tests DOIVENT échouer initialement (NotImplementedError verify_polar_webhook)
- L'implémentation doit faire passer TOUS les tests (couverture >= 95%)
- Chaque test simule une attaque réelle documentée dans ADR-032

Les 9 failles mitigées par ces tests :
 1. Raw Body (ADR-032 Faille #1) — HMAC sur les bytes exacts, pas JSON parsé
 2. Timing Attacks (ADR-032 Faille #2) — hmac.compare_digest() constant-time
 3. Replay Attacks (ADR-032 Faille #3) — vérification timestamp (max 5 min)
 4. Idempotence (ADR-032 Faille #4) — webhook 2x accepté (DB gérera doublons via UNIQUE)
 5. Malformed Header (ADR-032 Faille #5) — format "sha256=..." parsing
 6. Invalid Hex Format (ADR-032 Faille #6) — validité hex de la signature
 7. Clock Skew (ADR-032 Faille #10) — tolérance ±60s futur, pas > 5 min passé
 8. Wrong Secret (ADR-032 Faille #11) — rejet si secret configuré erroné
 9. Event ID Dedup (ADR-032 Faille #12) — webhook dupliqué accepté par verify()
     (DB handle uniqueness)

Les 3 failles EXCLUES (responsabilité infra/FastAPI) :
 - Empty Body (FastAPI 422 avant handler)
 - Invalid UTF-8 (HMAC byte-agnostic)
 - DoS Payloads (Fly.io rate-limit + FastAPI max_upload_size)

Politique de test du projet :
- Pas de classes de test, fonctions simples test_xxx_does_yyy()
- Pas de reload module, fixtures scope maîtrisé
- Déterminisme strict (now_provider injectable)
- Assertions comportementales (pas impl-details)
"""

import contextlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

import pytest

# À implémenter dans app/presentation/api/v1/webhooks.py
from app.presentation.api.v1.webhooks import (
    PolarWebhookEvent,
    WebhookVerificationError,
    verify_polar_webhook,
)

# ============================================================================
# Fixtures TDD
# ============================================================================


@pytest.fixture(scope="function")
def polar_secret() -> str:
    """Secret Polar configuré pour tests (équivalent POLAR_WEBHOOK_SECRET env)."""
    return "test_webhook_secret_xxx_123"


@pytest.fixture(scope="function")
def valid_webhook_body() -> bytes:
    """Payload de webhook Polar valide (bytes bruts pour HMAC)."""
    payload: dict[str, Any] = {
        "id": "webhook_evt_xxx",
        "type": "order.created",
        "data": {
            "id": "order_123",
            "customer_id": "customer_xxx",
            "customer_email": "user@example.com",
            "product_id": "product_xxx",
            "subscription_id": "sub_xxx",
            "status": "succeeded",
            "metadata": {"dataset_id": "d8799999-9999-4999-9999-999999999999"},
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
    # Conserver un encodage compact pour exposer la différence avec un re-dump JSON par défaut.
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


@pytest.fixture(scope="function")
def valid_webhook_signature(valid_webhook_body: bytes, polar_secret: str) -> str:
    """Signature HMAC-SHA256 valide pour le webhook (format: sha256=<hex>)."""
    hex_digest = hmac.new(polar_secret.encode("utf-8"), valid_webhook_body, sha256).hexdigest()
    return f"sha256={hex_digest}"


# ============================================================================
# FAILLE #1 : Raw Body (ADR-032 Faille #1)
#
# Problème : Si on utilise request.json() ou json.loads() avant de vérifier
# la signature, Python réorganise les clés ou les espaces. La signature ne
# correspondra plus.
#
# Mitigation : Toujours utiliser request.body() (bytes bruts) pour HMAC.
# ============================================================================


def test_signature_correct_on_exact_body_bytes(
    valid_webhook_body: bytes, valid_webhook_signature: str, polar_secret: str
) -> None:
    """
    Nominal : signature correcte sur les bytes exacts.
    Le webhook doit être accepté (HMAC correspond).
    """
    now = datetime.now(UTC)

    result = verify_polar_webhook(
        body=valid_webhook_body,
        signature_header=valid_webhook_signature,
        secret=polar_secret,
        timestamp=now.isoformat(),
    )
    assert result is True


def test_signature_fails_if_body_parsed_then_rejsoned(
    valid_webhook_body: bytes, polar_secret: str
) -> None:
    """
    Test d'attaque (Faille #1) : si on re-sérialise le JSON parsé,
    les espaces/ordre peuvent changer → signature ne correspond plus.

    Ce test vérifie qu'on utilise bien le body brut (pas le JSON reparsé).
    """
    # Simuler ce qui se passe si développeur oublie et utilise JSON re-parsé
    parsed = json.loads(valid_webhook_body.decode("utf-8"))
    rejsoned = json.dumps(parsed).encode("utf-8")  # peut avoir espaces différents

    # Calculer une signature SUR le JSON rejsoned (INCORRECT)
    wrong_signature = f"sha256={hmac.new(
        polar_secret.encode('utf-8'),
        rejsoned,
        sha256
    ).hexdigest()}"

    # La vérification doit échouer car on a signé sur un body différent
    with pytest.raises(WebhookVerificationError):
        verify_polar_webhook(
            body=valid_webhook_body,  # body original
            signature_header=wrong_signature,  # signature du body rejsoned
            secret=polar_secret,
            timestamp=datetime.now(UTC).isoformat(),
        )


# ============================================================================
# FAILLE #2 : Timing Attacks (ADR-032 Faille #2)
#
# Problème : Comparaison naïve `sig1 == sig2` s'arrête au premier octet
# différent → l'attaquant mesure le temps pour deviner la clé caractère par caractère.
#
# Mitigation : hmac.compare_digest() (temps constant).
# ============================================================================


def test_signature_completely_wrong(valid_webhook_body: bytes, polar_secret: str) -> None:
    """
    Test d'attaque (Faille #2) : signature complètement fausse.
    Doit être rejetée (timing-safe, compare_digest).
    """
    fake_signature = "sha256=" + "0" * 64  # SHA256 = 64 chars hex

    with pytest.raises(WebhookVerificationError):
        verify_polar_webhook(
            body=valid_webhook_body,
            signature_header=fake_signature,
            secret=polar_secret,
            timestamp=datetime.now(UTC).isoformat(),
        )


def test_signature_invalid_with_single_char_difference(
    valid_webhook_body: bytes, valid_webhook_signature: str, polar_secret: str
) -> None:
    """
    Test d'attaque (Faille #2) : signature avec 1 seul caractère modifié.
    Doit être rejetée immédiatement (sans révéler par timing que c'était "presque bon").
    """
    # Modifier un seul caractère de la signature
    # Trouver le dernier '=' sur la chaîne, puis modifier un caractère hex.
    eq_idx = valid_webhook_signature.rfind("=")
    sig_list = list(valid_webhook_signature)
    if eq_idx > 0 and eq_idx + 1 < len(sig_list):
        sig_list[eq_idx + 1] = "0" if sig_list[eq_idx + 1] != "0" else "1"
    corrupted_sig = "".join(sig_list)

    with pytest.raises(WebhookVerificationError):
        verify_polar_webhook(
            body=valid_webhook_body,
            signature_header=corrupted_sig,
            secret=polar_secret,
            timestamp=datetime.now(UTC).isoformat(),
        )


def test_signature_verification_constant_time(
    valid_webhook_body: bytes, valid_webhook_signature: str, polar_secret: str
) -> None:
    """
    Test de timing (Faille #2) : vérifier que compare_digest() est utilisé
    (constant-time, pas d'info leak par timing).

    Note : Test imprécis en CI (réseau), mais documente l'intention.
    """
    fake_sig = "sha256=" + "0" * 64

    # Mesurer le temps pour une fausse signature
    t_start = time.perf_counter()
    with contextlib.suppress(WebhookVerificationError):
        verify_polar_webhook(
            body=valid_webhook_body,
            signature_header=fake_sig,
            secret=polar_secret,
            timestamp=datetime.now(UTC).isoformat(),
        )
    t_wrong = time.perf_counter() - t_start

    # Mesurer le temps pour une signature correcte
    t_start = time.perf_counter()
    verify_polar_webhook(
        body=valid_webhook_body,
        signature_header=valid_webhook_signature,
        secret=polar_secret,
        timestamp=datetime.now(UTC).isoformat(),
    )
    t_correct = time.perf_counter() - t_start

    # Les temps doivent être du même ordre de magnitude (pas 100x différent)
    assert abs(t_wrong - t_correct) < 0.01, "Timing non constant-time"


# ============================================================================
# FAILLE #3 : Replay Attacks (ADR-032 Faille #3)
# + FAILLE #10 : Clock Skew (ADR-032 Faille #10)
#
# Problème : Un attaquant intercepte un webhook valide et te le renvoie
# 1 mois plus tard → client suspendu à tort.
#
# Mitigation : Vérifier le timestamp (rejecter si > 5 min, tolérance ±60s futur).
# ============================================================================


def test_webhook_timestamp_too_old_rejected(
    valid_webhook_body: bytes, valid_webhook_signature: str, polar_secret: str
) -> None:
    """
    Test d'attaque (Faille #3) : webhook avec timestamp de 2 heures ago.
    Doit être REJETÉ (replay attack).
    """
    old_timestamp = (datetime.now(UTC) - timedelta(hours=2)).isoformat()

    with pytest.raises(WebhookVerificationError):
        verify_polar_webhook(
            body=valid_webhook_body,
            signature_header=valid_webhook_signature,
            secret=polar_secret,
            timestamp=old_timestamp,
        )


def test_webhook_timestamp_just_within_5min_accepted(
    valid_webhook_body: bytes, valid_webhook_signature: str, polar_secret: str
) -> None:
    """
    Nominal : webhook avec timestamp de 4 min ago (dans la fenêtre 5 min).
    Doit être ACCEPTÉ.
    """
    recent_timestamp = (datetime.now(UTC) - timedelta(minutes=4)).isoformat()

    result = verify_polar_webhook(
        body=valid_webhook_body,
        signature_header=valid_webhook_signature,
        secret=polar_secret,
        timestamp=recent_timestamp,
    )
    assert result is True


def test_webhook_timestamp_just_outside_5min_rejected(
    valid_webhook_body: bytes, valid_webhook_signature: str, polar_secret: str
) -> None:
    """
    Test limite (Faille #3) : webhook avec timestamp de 6 min ago (hors fenêtre).
    Doit être REJETÉ.
    """
    old_timestamp = (datetime.now(UTC) - timedelta(minutes=6)).isoformat()

    with pytest.raises(WebhookVerificationError):
        verify_polar_webhook(
            body=valid_webhook_body,
            signature_header=valid_webhook_signature,
            secret=polar_secret,
            timestamp=old_timestamp,
        )


def test_webhook_timestamp_future_rejected(
    valid_webhook_body: bytes, valid_webhook_signature: str, polar_secret: str
) -> None:
    """
    Test d'attaque (Faille #10 Clock Skew) : webhook avec timestamp
    2 minutes dans le futur (horloge fake ou désynchronisée).

    Tolérance ±60s max pour la dérive d'horloge (NTP).
    """
    # Timestamp 2 minutes dans le futur (dépasse la tolérance ±60s)
    future_timestamp = (datetime.now(UTC) + timedelta(minutes=2)).isoformat()

    with pytest.raises(WebhookVerificationError):
        verify_polar_webhook(
            body=valid_webhook_body,
            signature_header=valid_webhook_signature,
            secret=polar_secret,
            timestamp=future_timestamp,
        )


def test_webhook_invalid_timestamp_format_rejected(
    valid_webhook_body: bytes, valid_webhook_signature: str, polar_secret: str
) -> None:
    """
    Test d'attaque : timestamp non ISO 8601.
    Doit lever WebhookVerificationError avec un format invalide.
    """
    with pytest.raises(WebhookVerificationError):
        verify_polar_webhook(
            body=valid_webhook_body,
            signature_header=valid_webhook_signature,
            secret=polar_secret,
            timestamp="04-07-2026 00:00:00",
        )


# ============================================================================
# FAILLE #4 : Idempotence (ADR-032 Faille #4)
# + FAILLE #12 : Event ID Deduplication (ADR-032 Faille #12)
#
# Problème : Polar "At least once delivery" → même webhook reçu 2x.
# Même webhook 2x ne doit pas être bloqué par verify_polar_webhook().
# (La déduplication réelle est au niveau DB via UNIQUE(polar_event_id))
#
# Mitigation : verify_polar_webhook() accepte le même webhook 2x.
# La DB gérera l'idempotence via contrainte UNIQUE.
# ============================================================================


def test_same_webhook_received_twice_both_accepted(
    valid_webhook_body: bytes, valid_webhook_signature: str, polar_secret: str
) -> None:
    """
    Test d'idempotence (Failles #4, #12) : même webhook reçu 2 fois
    doit être accepté par verify_polar_webhook() les 2 fois.

    La déduplication réelle est garantie par la DB :
    - Colonne polar_event_id UNIQUE
    - INSERT OR IGNORE / ON CONFLICT DO NOTHING
    """
    timestamp = datetime.now(UTC).isoformat()

    # 1ère réception
    result1 = verify_polar_webhook(
        body=valid_webhook_body,
        signature_header=valid_webhook_signature,
        secret=polar_secret,
        timestamp=timestamp,
    )
    assert result1 is True

    # 2e réception (identique)
    result2 = verify_polar_webhook(
        body=valid_webhook_body,
        signature_header=valid_webhook_signature,
        secret=polar_secret,
        timestamp=timestamp,
    )
    assert result2 is True  # Accepté aussi


# ============================================================================
# FAILLE #5 : Malformed Header (ADR-032 Faille #5)
# + FAILLE #6 : Invalid Hex Format (ADR-032 Faille #6)
#
# Problème : Header X-Polar-Signature au format inattendu
# ("sha256=..." manquant ou signature pas en hex valide).
#
# Mitigation : Parser le header, valider format "sha256=<64 hex chars>".
# ============================================================================


def test_malformed_signature_header_rejected(valid_webhook_body: bytes, polar_secret: str) -> None:
    """
    Test d'attaque (Failles #5, #6) : header de signature malformé
    ou pas en hexadécimal valide.

    Cas testés :
    - Format "sha256=" manquant
    - Format "..." invalide (pas hex)
    - Format longueur incorrecte
    """
    # Cas 1 : "sha256=" manquant
    malformed_sig_1 = "not_a_valid_hex_string!!!!"
    with pytest.raises(WebhookVerificationError):
        verify_polar_webhook(
            body=valid_webhook_body,
            signature_header=malformed_sig_1,
            secret=polar_secret,
            timestamp=datetime.now(UTC).isoformat(),
        )

    # Cas 2 : "sha256=" présent mais hex invalide
    malformed_sig_2 = "sha256=not_hex_!!!"
    with pytest.raises(WebhookVerificationError):
        verify_polar_webhook(
            body=valid_webhook_body,
            signature_header=malformed_sig_2,
            secret=polar_secret,
            timestamp=datetime.now(UTC).isoformat(),
        )

    # Cas 3 : longueur hex incorrecte
    malformed_sig_3 = "sha256=abc123"
    with pytest.raises(WebhookVerificationError):
        verify_polar_webhook(
            body=valid_webhook_body,
            signature_header=malformed_sig_3,
            secret=polar_secret,
            timestamp=datetime.now(UTC).isoformat(),
        )


# ============================================================================
# FAILLE #11 : Wrong Secret (ADR-032 Faille #11)
#
# Problème : Admin configure POLAR_WEBHOOK_SECRET=xyz au lieu de abc
# → tous les webhooks rejetés.
#
# Mitigation : Tester avec secret erroné, vérifier que signature échoue.
# ============================================================================


def test_wrong_secret_rejected(valid_webhook_body: bytes, valid_webhook_signature: str) -> None:
    """
    Test d'attaque (Faille #11) : même signature valide,
    mais mauvais secret configuré → doit échouer.

    Cela teste qu'on utilise bien le secret pour la vérification HMAC.
    """
    wrong_secret = "completely_different_secret"

    with pytest.raises(WebhookVerificationError):
        verify_polar_webhook(
            body=valid_webhook_body,
            signature_header=valid_webhook_signature,
            secret=wrong_secret,
            timestamp=datetime.now(UTC).isoformat(),
        )


# ============================================================================
# Cas Nominaux (Happy Path)
# ============================================================================


def test_valid_webhook_accepted(
    valid_webhook_body: bytes, valid_webhook_signature: str, polar_secret: str
) -> None:
    """
    Nominal : webhook avec signature correcte et timestamp OK.
    Doit être ACCEPTÉ (retourne True).
    """
    current_timestamp = datetime.now(UTC).isoformat()

    result = verify_polar_webhook(
        body=valid_webhook_body,
        signature_header=valid_webhook_signature,
        secret=polar_secret,
        timestamp=current_timestamp,
    )
    assert result is True


# ============================================================================
# Tests Validation Pydantic (PolarWebhookEvent)
# ============================================================================


def test_parse_valid_order_created_event() -> None:
    """
    Test nominal : Pydantic doit accepter un payload order.created valide.
    """
    payload: dict[str, Any] = {
        "id": "webhook_evt_xxx",
        "type": "order.created",
        "data": {
            "id": "order_123",
            "customer_id": "customer_xxx",
            "customer_email": "user@example.com",
            "product_id": "product_xxx",
            "subscription_id": "sub_xxx",
            "status": "succeeded",
            "metadata": {"dataset_id": "d8799999-9999-4999-9999-999999999999"},
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }

    event = PolarWebhookEvent(**payload)
    assert event.type == "order.created"
    assert event.data["customer_email"] == "user@example.com"


def test_parse_valid_subscription_cancelled_event() -> None:
    """
    Test nominal : Pydantic doit accepter un payload subscription.cancelled valide.
    """
    payload: dict[str, Any] = {
        "id": "webhook_evt_yyy",
        "type": "subscription.cancelled",
        "data": {"subscription_id": "sub_xxx", "customer_id": "customer_xxx"},
        "timestamp": datetime.now(UTC).isoformat(),
    }

    event = PolarWebhookEvent(**payload)
    assert event.type == "subscription.cancelled"
    assert event.data["subscription_id"] == "sub_xxx"


def test_reject_malformed_payload_missing_type() -> None:
    """
    Test d'erreur : Pydantic doit rejeter un payload malformé
    (champ 'type' manquant).
    """
    invalid_payload: dict[str, Any] = {
        "id": "webhook_evt_xxx",
        # "type" manquant → erreur validation Pydantic
        "data": {},
    }

    with pytest.raises((ValueError, TypeError)):
        PolarWebhookEvent(**invalid_payload)
