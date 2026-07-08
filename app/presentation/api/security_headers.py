"""Middleware de securite web : injecte les headers definis par ADR-021.

Politique : tous les headers sont actifs en production et en staging.
En dev, les headers sont injectes pour validation mais la redirection
HTTPS est desactivee (environnement local HTTP).

Headers couverts :
  - Strict-Transport-Security (HSTS)
  - X-Content-Type-Options
  - X-Frame-Options
  - Referrer-Policy
  - Cross-Origin-Opener-Policy (COOP)
  - Permissions-Policy

Permissions-Policy : contient uniquement les features standard
(supportees sans flag par Chromium >=120, Firefox >=120, Safari >=17).
Source : https://github.com/w3c/webappsec-permissions-policy/blob/main/features.md
"""

from collections.abc import Awaitable, Callable

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injecte les headers de securite definis par ADR-021."""

    def __init__(
        self,
        app: Starlette,
        settings: Settings,
        *,
        enable_hsts: bool = True,
        enable_coop: bool = True,
        enable_xfo: bool = True,
        enable_cto: bool = True,
        enable_referrer_policy: bool = True,
        enable_permissions_policy: bool = True,
    ):
        super().__init__(app)
        self._settings: Settings = settings
        self._enable_hsts = enable_hsts
        self._enable_coop = enable_coop
        self._enable_xfo = enable_xfo
        self._enable_cto = enable_cto
        self._enable_referrer_policy = enable_referrer_policy
        self._enable_permissions_policy = enable_permissions_policy

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)

        headers_to_set: dict[str, str] = {}

        # HSTS : 1 an, inclure sous-domaines (Fly.io force deja HTTPS)
        if self._enable_hsts:
            headers_to_set["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # X-Content-Type-Options : empeche MIME sniffing
        if self._enable_cto:
            headers_to_set["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options : fallback pour navigateurs sans CSP
        if self._enable_xfo:
            headers_to_set["X-Frame-Options"] = "DENY"

        # Referrer-Policy : ne leak que l'origine en cross-origin
        if self._enable_referrer_policy:
            headers_to_set["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # COOP : isole le contexte de navigation
        if self._enable_coop:
            headers_to_set["Cross-Origin-Opener-Policy"] = "same-origin"

        # Permissions-Policy : desactiver les features non utilisees
        # Uniquement les features reconnues par defaut (pas de flag experimental)
        if self._enable_permissions_policy:
            headers_to_set["Permissions-Policy"] = (
                "accelerometer=(), autoplay=(), "
                "camera=(), cross-origin-isolated=(), "
                "display-capture=(), encrypted-media=(), "
                "fullscreen=(), geolocation=(), gyroscope=(), "
                "keyboard-map=(), magnetometer=(), microphone=(), "
                "midi=(), payment=(), picture-in-picture=(), "
                "publickey-credentials-get=(), screen-wake-lock=(), "
                "sync-xhr=(), usb=(), xr-spatial-tracking=()"
            )

        for header_name, header_value in headers_to_set.items():
            response.headers[header_name] = header_value

        return response
