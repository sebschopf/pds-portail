#!/usr/bin/env bash
# PDS-38 — Vérifie les headers de sécurité HTTP sur les environnements cibles.
#
# Usage :
#   ./scripts/check-security-headers.sh <url>            # vérifie une URL
#   ./scripts/check-security-headers.sh --all             # vérifie prod frontend + backend
#   ./scripts/check-security-headers.sh --frontend        # prod frontend uniquement
#   ./scripts/check-security-headers.sh --backend         # prod backend uniquement
#
# Codes de sortie : 0 = tous les headers présents, 1 = au moins un header manquant.
#
# Headers vérifiés (ADR-021) :
#   - Strict-Transport-Security (HSTS)
#   - X-Content-Type-Options
#   - X-Frame-Options (fallback legacy, CSP frame-ancestors couvre sinon)
#   - Cross-Origin-Opener-Policy (COOP)
#   - Referrer-Policy
#   - Content-Security-Policy (CSP)
#   - Permissions-Policy
#
# Note : X-Frame-Options peut être absent si frame-ancestors 'none' est dans la CSP.
#        Ce script le signale comme warning, pas comme erreur.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PROD_FRONTEND="https://pds-portail.vercel.app"
PROD_BACKEND="https://pds-portail-backend.fly.dev/api/v1/health"

REQUIRED_HEADERS=(
    "strict-transport-security"
    "x-content-type-options"
    "cross-origin-opener-policy"
    "referrer-policy"
    "content-security-policy"
    "permissions-policy"
)

LEGACY_HEADERS=(
    "x-frame-options"
)

failures=0
warnings=0

check_url() {
    local url="$1"
    local label="$2"

    echo -e "${CYAN}=== $label ===${NC}"
    echo "URL : $url"
    echo ""

    # Récupérer les headers HTTP (suivre les redirections)
    local response_headers
    response_headers=$(curl -sIL --max-time 15 "$url" 2>/dev/null || true)

    if [ -z "$response_headers" ]; then
        echo -e "${RED}❌ Impossible de joindre $url${NC}"
        echo ""
        failures=$((failures + 1))
        return
    fi

    # Normaliser les headers en minuscules pour la comparaison
    local headers_lower
    headers_lower=$(echo "$response_headers" | tr '[:upper:]' '[:lower:]')

    # Vérifier les headers requis
    for header in "${REQUIRED_HEADERS[@]}"; do
        if echo "$headers_lower" | grep -q "^${header}:"; then
            local value
            value=$(echo "$headers_lower" | grep "^${header}:" | head -1 | sed 's/^[^:]*: //')
            echo -e "  ${GREEN}✓${NC} ${header}: ${value:0:80}"
        else
            echo -e "  ${RED}✗${NC} ${header}: MANQUANT"
            failures=$((failures + 1))
        fi
    done

    # Vérifier les headers legacy (warning si absent)
    for header in "${LEGACY_HEADERS[@]}"; do
        if echo "$headers_lower" | grep -q "^${header}:"; then
            local value
            value=$(echo "$headers_lower" | grep "^${header}:" | head -1 | sed 's/^[^:]*: //')
            echo -e "  ${GREEN}✓${NC} ${header}: ${value:0:80}"
        else
            echo -e "  ${YELLOW}⚠${NC}  ${header}: absent (CSP frame-ancestors couvre si présent)"
            warnings=$((warnings + 1))
        fi
    done

    echo ""
}

main() {
    echo "PDS-38 — Vérification des headers de sécurité HTTP"
    echo "===================================================="
    echo ""

    local target="${1:-}"

    if [ "$target" = "--all" ] || [ -z "$target" ]; then
        check_url "$PROD_FRONTEND" "Frontend (Vercel)"
        check_url "$PROD_BACKEND" "Backend (Fly.io)"
    elif [ "$target" = "--frontend" ]; then
        check_url "$PROD_FRONTEND" "Frontend (Vercel)"
    elif [ "$target" = "--backend" ]; then
        check_url "$PROD_BACKEND" "Backend (Fly.io)"
    else
        check_url "$target" "URL personnalisée"
    fi

    echo "===================================================="
    echo -e "Erreurs   : ${RED}$failures${NC}"
    echo -e "Warnings  : ${YELLOW}$warnings${NC}"
    echo ""

    if [ "$failures" -gt 0 ]; then
        echo -e "${RED}❌ Des headers requis sont manquants.${NC}"
        exit 1
    else
        echo -e "${GREEN}✅ Tous les headers requis sont présents.${NC}"
        exit 0
    fi
}

main "$@"