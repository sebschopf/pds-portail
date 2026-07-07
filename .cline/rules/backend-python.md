# Règles Backend Python — PDS-Portail

> Appliquées à `app/**/*.py` et `tests/**/*.py`

---

## Typage & Contrats

- Typage strict partout (`strict=True` dans mypy), 0 erreur tolérée.
- Contrats publics explicites (interfaces, signatures, pas de `**kwargs` génériques).
- Pas de `Any` sans justification documentée.

## Architecture Hexagonale (Critique)

| Couche | Règles |
|--------|--------|
| **Domain** | Logique métier pure. **Aucun import** de `infrastructure` ni `persistence`. |
| **Application** | Use cases + Ports (Protocol interfaces uniquement, pas d'implémentations concrètes). |
| **Infrastructure** | Repositories, clients externes, adaptateurs base de données. |
| **Presentation** | API routers, schemas Pydantic (BaseModel), contrats HTTP. |

### Pattern Ports & Repositories

1. Définir le Port comme Protocol dans `app/application/ports/`
2. Implémenter dans `app/infrastructure/persistence/`
3. Injecter via `dependencies.py` ou instanciation directe dans les routers
4. Toujours valider avec des fakes dans les tests

## Tests : Règles strictes

### Déterminisme temporel (OBLIGATOIRE)

```python
# ❌ INTERDIT — flaky, dépendant de l'horloge système
now = datetime.now(UTC)
magic_link_repo.create(expires_at=(now + timedelta(minutes=15)).isoformat())

# ✅ OBLIGATOIRE — injectable, déterministe
now = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)
magic_link_repo.create(expires_at=(now + timedelta(minutes=15)).isoformat())
```

- Ne jamais utiliser `datetime.now()` ou `time.time()` directement dans les tests.
- Toujours accepter les timestamps en paramètre (injection de dépendance temporelle).
- Utiliser `tests/utils/time.py` pour les helpers de temps si existants.

### Pattern AAA (Arrange / Act / Assert)

```python
def test_quelque_chose():
    # Arrange — préparation des données et dépendances
    repo = FakeRepo()
    use_case = MonUseCase(repo)

    # Act — exécution de l'action testée
    result = use_case.execute(param)

    # Assert — vérifications
    assert result.status == "ok"
```

### Autres règles de test

- Tests orientés comportement, pas assertions sur les détails d'implémentation.
- Pas d'état partagé caché entre les tests (pas de variables globales mutables).
- Données de test déterministes et assertions stables (pas de `random`, pas d'UUID non fixés).
- Fixtures à usage unique, clairement nommées.
- CI run: `uv run pytest --cov=app --cov-fail-under=80 --cov-report=term-missing`

## Patterns spécifiques

### Email & SMTP (ADR-029, SPEC-009)

- Configuration via env: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
- Utiliser `smtplib.SMTP()` + `server.starttls()` pour compatibilité Brevo
- Templates dans `app/infrastructure/email/` (versions `.html` + `.txt`)
- Échecs silencieux : logger l'erreur mais ne jamais bloquer la réponse HTTP

### Magic Link (ADR-030, SPEC-012)

- Stockage token : hash SHA-256 uniquement (le token brut n'est jamais persisté)
- Validité : 15 minutes depuis la création
- Usage unique : marquer `used_at` à la consommation
- Anti-énumération : réponse HTTP identique que l'email existe ou non

## Validations obligatoires

```bash
uv run black --check app/ tests/       # 0 violation
uv run ruff check app/ tests/          # 0 violation
uv run mypy app/ tests/                # 0 erreur (strict)
uv run pytest --cov=app --cov-fail-under=80
```

## Références

- ADR-029: Email sending (SMTP, templates, Brevo)
- ADR-030: Magic link tokens (SHA-256, single-use, 15min)
- SPEC-009: Surveillance service (change detection, alerts)
- SPEC-011: Fiabilisation suite tests (déterminisme, anti-flaky)
- SPEC-012: Polar payment integration (checkout, webhooks)