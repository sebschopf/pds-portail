"""Validation et parsing des payloads CKAN bruts.

Transforme un ``object`` (JSON deserialise) en instances des ``TypedDict``
definis dans ``ckan_types.py``. Chaque parseur verifie les types a l'entree
et leve ``TypeError`` si la structure CKAN est invalide.

Separe du module de types (``ckan_types``) pour respecter le principe SRP :
- ``ckan_types`` : declarations pures de forme des donnees
- ``ckan_payloads`` : validation et transformation
"""

import logging
from typing import cast

from app.application.ports.ckan_types import (
    CkanOrganizationPayload,
    CkanPackagePayload,
    CkanPackageSearchResponse,
    CkanPackageSearchResult,
    CkanResourcePayload,
    CkanTagPayload,
)

logger = logging.getLogger(__name__)


def parse_package_search_response(payload: object) -> CkanPackageSearchResponse:
    """Valide la structure racine renvoyee par ``package_search``.

    On ne parse ici que les champs exploites par le MVP afin de limiter le
    couplage aux details CKAN inutiles au domaine.
    """

    if not isinstance(payload, dict):
        raise TypeError("CKAN package_search response must be a JSON object")
    source = cast(dict[str, object], payload)

    result_payload = source.get("result")
    if result_payload is None:
        return {}
    if not isinstance(result_payload, dict):
        raise TypeError("CKAN package_search result must be a JSON object")
    result_source = cast(dict[str, object], result_payload)

    parsed_result: dict[str, object] = {}
    results_payload = result_source.get("results")
    if results_payload is None:
        return cast(
            CkanPackageSearchResponse, {"result": cast(CkanPackageSearchResult, parsed_result)}
        )
    if not isinstance(results_payload, list):
        raise TypeError("CKAN package_search results must be a JSON array")

    results_items = cast(list[object], results_payload)

    parsed_packages: list[CkanPackagePayload] = []
    for index, item in enumerate(results_items):
        try:
            parsed_packages.append(parse_package_payload(item))
        except TypeError as exc:
            logger.warning("Record CKAN invalide ignore a l'index %s: %s", index, exc)

    parsed_result["results"] = parsed_packages
    return cast(CkanPackageSearchResponse, {"result": cast(CkanPackageSearchResult, parsed_result)})


def parse_package_payload(payload: object) -> CkanPackagePayload:
    """Normalise la partie dataset d'un resultat CKAN."""

    if not isinstance(payload, dict):
        raise TypeError("CKAN package payload must be a JSON object")
    source = cast(dict[str, object], payload)

    parsed_payload: dict[str, object] = {}
    _copy_optional_str(source, parsed_payload, "id")
    _copy_optional_text(source, parsed_payload, "title")
    _copy_optional_text(source, parsed_payload, "notes")
    _copy_optional_str(source, parsed_payload, "metadata_created")
    _copy_optional_str(source, parsed_payload, "metadata_modified")
    _copy_optional_str(source, parsed_payload, "url")

    organization_payload = source.get("organization")
    if organization_payload is not None:
        parsed_payload["organization"] = parse_organization_payload(organization_payload)

    tags_payload = source.get("tags")
    if tags_payload is not None:
        if not isinstance(tags_payload, list):
            raise TypeError("CKAN tags payload must be a JSON array")

        tag_items = cast(list[object], tags_payload)
        parsed_payload["tags"] = [parse_tag_payload(item) for item in tag_items]

    resources_payload = source.get("resources")
    if resources_payload is not None:
        if not isinstance(resources_payload, list):
            raise TypeError("CKAN resources payload must be a JSON array")

        resource_items = cast(list[object], resources_payload)
        parsed_payload["resources"] = [parse_resource_payload(item) for item in resource_items]

    return cast(CkanPackagePayload, parsed_payload)


def parse_organization_payload(payload: object) -> CkanOrganizationPayload:
    """Extrait une organisation CKAN sans laisser entrer de types ambigus."""

    if not isinstance(payload, dict):
        raise TypeError("CKAN organization payload must be a JSON object")
    source = cast(dict[str, object], payload)

    parsed_payload: dict[str, object] = {}
    _copy_optional_str(source, parsed_payload, "id")
    _copy_optional_str(source, parsed_payload, "name")
    _copy_optional_text(source, parsed_payload, "title")
    _copy_optional_text(source, parsed_payload, "description")
    _copy_optional_str(source, parsed_payload, "image_url")
    _copy_optional_str(source, parsed_payload, "url")
    return cast(CkanOrganizationPayload, parsed_payload)


def parse_tag_payload(payload: object) -> CkanTagPayload:
    """Extrait un tag CKAN utile a l'indexation locale."""

    if not isinstance(payload, dict):
        raise TypeError("CKAN tag payload must be a JSON object")
    source = cast(dict[str, object], payload)

    parsed_payload: dict[str, object] = {}
    _copy_optional_text(source, parsed_payload, "name")
    _copy_optional_text(source, parsed_payload, "display_name")
    return cast(CkanTagPayload, parsed_payload)


def parse_resource_payload(payload: object) -> CkanResourcePayload:
    """Valide la partie ressource d'un dataset CKAN."""

    if not isinstance(payload, dict):
        raise TypeError("CKAN resource payload must be a JSON object")
    source = cast(dict[str, object], payload)

    parsed_payload: dict[str, object] = {}
    _copy_optional_str(source, parsed_payload, "id")
    _copy_optional_str(source, parsed_payload, "package_id")
    _copy_optional_text(source, parsed_payload, "name")
    _copy_optional_text(source, parsed_payload, "description")
    _copy_optional_str(source, parsed_payload, "format")
    _copy_optional_str(source, parsed_payload, "download_url")
    _copy_optional_str(source, parsed_payload, "url")
    _copy_optional_str(source, parsed_payload, "created")
    _copy_optional_str(source, parsed_payload, "last_modified")

    media_type_value = source.get("media-type")
    if media_type_value is not None:
        if not isinstance(media_type_value, str):
            raise TypeError("CKAN field 'media-type' must be a string")
        if "format" not in parsed_payload:
            parsed_payload["format"] = media_type_value

    if "url" not in parsed_payload and "download_url" in parsed_payload:
        parsed_payload["url"] = parsed_payload["download_url"]

    size_value = source.get("size")
    if size_value is not None:
        if not isinstance(size_value, int):
            raise TypeError("CKAN resource size must be an integer")
        parsed_payload["size"] = size_value

    return cast(CkanResourcePayload, parsed_payload)


def _copy_optional_str(source: dict[str, object], target: dict[str, object], key: str) -> None:
    """Copie un champ texte optionnel apres verification stricte de son type."""

    value = source.get(key)
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError(f"CKAN field '{key}' must be a string")
    target[key] = value


def _copy_optional_text(source: dict[str, object], target: dict[str, object], key: str) -> None:
    """Copie un champ texte CKAN qui peut etre string ou objet multilingue."""

    value = source.get(key)
    if value is None:
        return
    if isinstance(value, str):
        target[key] = value
        return
    if isinstance(value, dict):
        normalized = _extract_multilingual_text(cast(dict[str, object], value))
        if normalized is None:
            return
        target[key] = normalized
        return
    raise TypeError(f"CKAN field '{key}' must be a string")


def _extract_multilingual_text(values: dict[str, object]) -> str | None:
    """Extrait un libelle humain depuis un objet de traductions CKAN."""

    for locale in ("fr", "de", "it", "en", "rm"):
        candidate = values.get(locale)
        if isinstance(candidate, str) and candidate.strip():
            return candidate

    for candidate in values.values():
        if isinstance(candidate, str) and candidate.strip():
            return candidate

    return None
