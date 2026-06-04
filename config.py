"""Configuration centrale du dashboard BVC.

Ce module contient toutes les constantes utilisées dans l'application :
chemins, charte graphique Wafa Gestion, noms de feuilles, ordres des
périodes et indicateurs. Aucune logique métier ici.
"""
from __future__ import annotations

import os
from pathlib import Path

# =============================================================================
# CHEMINS
# =============================================================================
# Racine du projet (dossier contenant ce fichier).
PROJECT_ROOT: Path = Path(__file__).resolve().parent

# Chemin du fichier Excel source.
# Modifiable via la variable d'environnement BVC_EXCEL_PATH si besoin.
EXCEL_PATH: Path = Path(
    os.environ.get(
        "BVC_EXCEL_PATH",
        str(PROJECT_ROOT / "data" / "Copie_de_Données_trims__Annuelles.xlsx"),
    )
)

# =============================================================================
# FEUILLES EXCEL
# =============================================================================
SHEET_BASE: str = "Base_Finale"   # source principale (format long/tidy)
SHEET_TRIMS: str = "Trims"        # source du mapping société → secteur

# =============================================================================
# SOURCE GOOGLE SHEETS (déploiement en ligne)
# =============================================================================
# ID du Google Sheet servant de source de vérité une fois l'app en ligne.
#   - Laisser vide ("") -> lecture du fichier Excel local (développement).
#   - Renseigner l'ID    -> lecture du Google Sheet (déploiement public).
# L'ID se trouve dans l'URL du Sheet :
#   https://docs.google.com/spreadsheets/d/<ICI_L_ID>/edit
# Le Sheet doit être partagé « Tout utilisateur disposant du lien : Lecteur ».
GSHEET_ID: str = os.environ.get("BVC_GSHEET_ID", "1tnjSxIjyXAbSBqPoQ50k6kfCNuPM6cJNXdtDlLf-cXQ")  # <-- colle ton ID entre les guillemets
# Nom de l'onglet contenant les données trimestrielles (format large).
GSHEET_TRIMS_TAB: str = os.environ.get("BVC_GSHEET_TRIMS_TAB", SHEET_TRIMS)

# =============================================================================
# CHARTE GRAPHIQUE WAFA GESTION
# =============================================================================
# UI / Chrome
COLOR_ORANGE: str = "#F39200"        # couleur principale Wafa Gestion
COLOR_BLACK: str = "#1A1A1A"
COLOR_WHITE: str = "#FFFFFF"
COLOR_GRAY_LIGHT: str = "#F5F5F5"    # fonds secondaires
COLOR_GRAY_MEDIUM: str = "#6B7280"   # texte secondaire

# Variations
COLOR_POSITIVE: str = "#16A34A"      # vert sobre
COLOR_NEGATIVE: str = "#DC2626"      # rouge sobre

# Palette neutre coordonnée pour les comparaisons (5 teintes).
# L'orange #F39200 reste réservé à l'élément mis en avant.
PALETTE_NEUTRAL: list[str] = [
    "#0072B2", "#009E73", "#CC79A7", "#56B4E9", "#999999",
]

# Palette catégorielle pour les 18 secteurs (Plotly "Antique").
# Définie en dur pour éviter d'importer plotly dans config.
# Palette chronologique pour les graphes comparatifs par année
# Palette catégorielle pour les 18 secteurs (Plotly "Antique")
PALETTE_SECTORS: list[str] = [
    "#0072B2", "#F39200", "#009E73", "#CC79A7",
    "#56B4E9", "#D55E00", "#F0E442", "#999999",
]
PALETTE_ANNEES: list[str] = [
    "#0072B2",  # 2022 — bleu foncé
    "#56B4E9",  # 2023 — bleu ciel
    "#009E73",  # 2024 — vert
    "#F39200",  # 2025 — orange Wafa (mise en avant)
    "#D55E00",  # 2026 — vermillon
    "#CC79A7",  # 2027 — rose
    "#F0E442",  # 2028+ — jaune
]

# Police par défaut des graphiques Plotly et de l'UI.
FONT_FAMILY: str = "Inter, -apple-system, BlinkMacSystemFont, Arial, sans-serif"

# =============================================================================
# ORDRE CANONIQUE DES PÉRIODES
# =============================================================================
PERIODES_TRIMESTRIELLES: list[str] = ["T1", "T2", "T3", "T4"]
PERIODES_SEMESTRIELLES: list[str] = ["S1", "S2"]
PERIODE_ANNUELLE: str = "Annuel"

GRANULARITES: list[str] = ["Trimestriel", "Semestriel", "Annuel"]

# =============================================================================
# INDICATEURS
# =============================================================================
INDICATEUR_CA: str = "CA"
INDICATEUR_CAPEX: str = "Capex"            # version strippée (sans espace)
INDICATEUR_ENDETTEMENT: str = "Endettement"

INDICATEURS: list[str] = [
    INDICATEUR_CA,
    INDICATEUR_CAPEX,
    INDICATEUR_ENDETTEMENT,
]

# =============================================================================
# ANNÉES
# =============================================================================
ANNEE_DEBUT: int = 2022
ANNEE_FIN: int = 2026   
ANNEE_DEFAUT: int = 2025   # année sélectionnée par défaut

# =============================================================================
# AFFICHAGE — SENTINELLES POUR CAS LIMITES
# =============================================================================
LABEL_NA: str = "N/A"   # dénominateur nul ou donnée manquante
LABEL_NM: str = "N/M"   # changement de signe (non significatif)
# Sociétés du secteur énergie exclues du CA agrégé (Vue d'Ensemble)
SOCIETES_EXCLUES_CA: list[str] = ["AFRIQUIA GAZ", "TAQA MOROCCO", "TOTALENERGIES"]