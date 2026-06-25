"""Dictionnaires de synonymes metier et equivalents multilingues.

Donnees statiques versionnees et auditables en CI. Separees de la logique
d'expansion pour respecter le SRP (ADR-003).

Chaque entree est un groupe de termes equivalents. Les variantes sont en
minuscules, sans accents pour la normalisation. L'ordre est arbitraire ;
le premier terme sert de representant canonique.

Origine : termes observes sur opendata.swiss et catalogues nationaux.
Maintenance : ce dictionnaire est versionne dans le depot, auditable en CI.
Limites initiales : couverture partielle, a enrichir avec les retours utilisateurs.

Convention de nommage : les cles sont des concepts metier en francais.
Les listes contiennent des synonymes tous en minuscules sans accents.

References:
    PRD-F01, PRD-F10 (recherche multilingue)
    ADR-023 (trajectoire M6)
    PDS-41 (tache de reference)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Dictionnaire de synonymes metier orientes usages publics (FR uniquement)
# ---------------------------------------------------------------------------

SYNONYM_DICTIONARY: dict[str, list[str]] = {
    "transport": [
        "transport",
        "transports",
        "mobilite",
        "deplacement",
        "trafic",
        "circulation",
        "navette",
    ],
    "sante": [
        "sante",
        "medical",
        "hopital",
        "hopitaux",
        "clinique",
        "medecin",
        "patient",
        "soins",
        "maladie",
        "pathologie",
        "epidemie",
    ],
    "education": [
        "education",
        "ecole",
        "ecoles",
        "enseignement",
        "formation",
        "etudiant",
        "etudiants",
        "eleve",
        "eleves",
        "universite",
        "college",
        "lycee",
    ],
    "environnement": [
        "environnement",
        "ecologie",
        "climat",
        "pollution",
        "dechets",
        "recyclage",
        "biodiversite",
        "nature",
        "developpement durable",
    ],
    "population": [
        "population",
        "demographie",
        "habitant",
        "habitants",
        "resident",
        "residents",
        "recensement",
        "menage",
        "menages",
    ],
    "economie": [
        "economie",
        "emploi",
        "chomage",
        "entreprise",
        "entreprises",
        "commerce",
        "industrie",
        "agriculture",
        "tourisme",
    ],
    "finance": [
        "finance",
        "budget",
        "depense",
        "depenses",
        "recette",
        "recettes",
        "fiscalite",
        "impot",
        "impots",
        "subvention",
        "subventions",
    ],
    "territoire": [
        "territoire",
        "commune",
        "communes",
        "canton",
        "cantons",
        "region",
        "regions",
        "district",
        "municipalite",
    ],
    "energie": [
        "energie",
        "electricite",
        "gaz",
        "petrole",
        "renouvelable",
        "solaire",
        "eolien",
        "hydraulique",
        "consommation",
    ],
    "eau": [
        "eau",
        "potable",
        "assainissement",
        "hydrologie",
        "riviere",
        "lac",
        "nappe",
        "phreatique",
        "qualite eau",
    ],
    "logement": [
        "logement",
        "immobilier",
        "construction",
        "batiment",
        "batiments",
        "appartement",
        "maison",
        "loyer",
        "loyers",
    ],
    "social": [
        "social",
        "aide sociale",
        "prestation",
        "prestations",
        "protection sociale",
        "assurance",
        "retraite",
        "pauvrete",
    ],
    "justice": [
        "justice",
        "tribunal",
        "delinquance",
        "criminalite",
        "police",
        "prison",
        "condamnation",
        "infraction",
    ],
    "culture": [
        "culture",
        "patrimoine",
        "musee",
        "bibliotheque",
        "archive",
        "monument",
        "evenement",
        "spectacle",
    ],
    "meteo": [
        "meteo",
        "meteorologie",
        "temperature",
        "precipitation",
        "pluie",
        "neige",
        "vent",
        "climatologie",
    ],
}

# ---------------------------------------------------------------------------
# Dictionnaire multilingue FR ↔ DE ↔ IT ↔ EN (termes metier de base)
# ---------------------------------------------------------------------------

MULTILINGUAL_DICTIONARY: dict[str, dict[str, list[str]]] = {
    "transport": {
        "de": ["verkehr", "transport", "mobilität", "verkehrsmittel"],
        "it": ["trasporto", "trasporti", "mobilità"],
        "en": ["transport", "transportation", "mobility", "traffic", "transit"],
    },
    "sante": {
        "de": ["gesundheit", "medizin", "krankenhaus", "klinik"],
        "it": ["salute", "medico", "ospedale", "sanità"],
        "en": ["health", "medical", "hospital", "healthcare"],
    },
    "education": {
        "de": ["bildung", "schule", "ausbildung", "universität"],
        "it": ["educazione", "scuola", "formazione", "università"],
        "en": ["education", "school", "training", "university"],
    },
    "environnement": {
        "de": ["umwelt", "ökologie", "klima", "naturschutz"],
        "it": ["ambiente", "ecologia", "clima", "natura"],
        "en": ["environment", "ecology", "climate", "nature"],
    },
    "population": {
        "de": ["bevölkerung", "einwohner", "demografie", "zensus"],
        "it": ["popolazione", "demografia", "censimento", "abitanti"],
        "en": ["population", "demographics", "census", "inhabitants"],
    },
    "economie": {
        "de": ["wirtschaft", "arbeit", "arbeitslosigkeit", "industrie"],
        "it": ["economia", "lavoro", "disoccupazione", "industria"],
        "en": ["economy", "employment", "unemployment", "industry"],
    },
    "finance": {
        "de": ["finanzen", "budget", "ausgaben", "steuern"],
        "it": ["finanza", "budget", "spesa", "tasse", "imposte"],
        "en": ["finance", "budget", "expenditure", "tax", "taxation"],
    },
    "territoire": {
        "de": ["gebiet", "gemeinde", "kanton", "region", "bezirk"],
        "it": ["territorio", "comune", "cantone", "regione", "distretto"],
        "en": ["territory", "municipality", "canton", "region", "district"],
    },
    "energie": {
        "de": ["energie", "strom", "gas", "erneuerbar"],
        "it": ["energia", "elettricità", "gas", "rinnovabile"],
        "en": ["energy", "electricity", "gas", "renewable"],
    },
    "eau": {
        "de": ["wasser", "trinkwasser", "abwasser", "hydrologie"],
        "it": ["acqua", "potabile", "idrologia", "fognatura"],
        "en": ["water", "drinking water", "hydrology", "wastewater"],
    },
    "logement": {
        "de": ["wohnen", "immobilien", "bau", "miete", "wohnung"],
        "it": ["alloggio", "immobiliare", "costruzione", "affitto"],
        "en": ["housing", "real estate", "construction", "building", "rent"],
    },
    "social": {
        "de": ["soziales", "sozialhilfe", "versicherung", "rente"],
        "it": ["sociale", "assistenza", "assicurazione", "pensione"],
        "en": ["social", "welfare", "insurance", "pension"],
    },
    "justice": {
        "de": ["justiz", "gericht", "kriminalität", "polizei"],
        "it": ["giustizia", "tribunale", "criminalità", "polizia"],
        "en": ["justice", "court", "crime", "police"],
    },
    "culture": {
        "de": ["kultur", "erbe", "museum", "bibliothek", "archiv"],
        "it": ["cultura", "patrimonio", "museo", "biblioteca", "archivio"],
        "en": ["culture", "heritage", "museum", "library", "archive"],
    },
    "meteo": {
        "de": ["wetter", "meteorologie", "temperatur", "niederschlag"],
        "it": ["meteo", "meteorologia", "temperatura", "precipitazione"],
        "en": ["weather", "meteorology", "temperature", "precipitation"],
    },
    "agriculture": {
        "de": ["landwirtschaft", "agrar", "bauer", "ernte"],
        "it": ["agricoltura", "agrario", "raccolto", "coltivazione"],
        "en": ["agriculture", "farming", "crop", "harvest"],
    },
    "foret": {
        "de": ["wald", "forst", "forstwirtschaft", "waldfläche"],
        "it": ["foresta", "bosco", "selvicoltura", "silvicoltura"],
        "en": ["forest", "forestry", "woodland", "timber"],
    },
    "statistique": {
        "de": ["statistik", "daten", "erhebung", "auswertung"],
        "it": ["statistica", "dati", "rilevazione", "analisi"],
        "en": ["statistics", "data", "survey", "analysis"],
    },
    "geographie": {
        "de": ["geografie", "karte", "kartografie", "geodaten"],
        "it": ["geografia", "mappa", "cartografia", "geodati"],
        "en": ["geography", "map", "cartography", "geodata"],
    },
    "open data": {
        "de": ["offene daten", "open data", "opendata"],
        "it": ["dati aperti", "open data", "opendata"],
        "en": ["open data", "opendata", "public data"],
    },
}
