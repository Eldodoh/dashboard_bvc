"""
ui_utils.py — Fonctions utilitaires partagées par les pages Streamlit.

Centralise :
- le chargement des données (depuis Google Sheets ou Excel, via data_loader),
  avec mise en cache et rafraîchissement (bouton + TTL) ;
- le style global de l'application (densité, typographie, charte Wafa) ;
- le bouton « Actualiser » de la barre latérale ;
- le filtrage des données par année et période pour les graphes.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from data_loader import load_data

# Valeurs spéciales des filtres (= aucune restriction)
TOUTES_ANNEES = "Toutes"
TOUTES_PERIODES = "Toutes"

# --- Couleurs UI (miroir de la charte Wafa Gestion définie dans config.py) ---
WAFA_ORANGE = "#F39200"
WAFA_NOIR = "#1A1A1A"
WAFA_GRIS_TEXTE = "#6B7280"
WAFA_GRIS_CLAIR = "#F5F5F5"

# --- Réglages de densité / typographie (à ajuster ici en un seul endroit) ---
TOP_PADDING = "3.75rem"       # dégage la barre supérieure fixe de Streamlit
BLOCK_GAP = "0.55rem"         # écart vertical entre les éléments
H1_SIZE = "1.7rem"            # st.title
H2_SIZE = "1.3rem"            # st.header
H3_SIZE = "1.08rem"           # st.subheader
BODY_SIZE = "0.94rem"         # texte / markdown
METRIC_VALUE_SIZE = "1.55rem"  # valeur des st.metric
METRIC_LABEL_SIZE = "0.78rem"  # libellé des st.metric

# Durée de vie du cache (secondes) : au-delà, les données sont relues
# automatiquement. Le bouton « Actualiser » force une relecture immédiate.
CACHE_TTL_SECONDES = 300


@st.cache_data(ttl=CACHE_TTL_SECONDES)
def _charger_donnees():
    """Charge les données BVC (mis en cache, relu après le TTL).

    Returns:
        DataFrame des données BVC au format long.
    """
    return load_data()


def get_data():
    """Retourne les données BVC (cache partagé par tous les visiteurs).

    Returns:
        DataFrame des données BVC au format long.
    """
    return _charger_donnees()


def apply_compact_style() -> None:
    """Injecte le style global : densité, typographie et couleurs charte.

    À appeler une fois en haut de chaque page (les pages qui utilisent
    ``render_refresh_button`` l'obtiennent automatiquement). Les valeurs clés
    sont pilotées par les constantes en tête de module.
    """
    variables = f"""
    <style>
    :root {{
        --wafa-orange: {WAFA_ORANGE};
        --wafa-noir: {WAFA_NOIR};
        --wafa-gris-texte: {WAFA_GRIS_TEXTE};
        --wafa-gris-clair: {WAFA_GRIS_CLAIR};
        --pad-top: {TOP_PADDING};
        --block-gap: {BLOCK_GAP};
        --h1: {H1_SIZE};
        --h2: {H2_SIZE};
        --h3: {H3_SIZE};
        --body: {BODY_SIZE};
        --metric-value: {METRIC_VALUE_SIZE};
        --metric-label: {METRIC_LABEL_SIZE};
    }}
    </style>
    """

    regles = """
    <style>
    /* Police professionnelle (charte : sans-serif) */
    html, body, [data-testid="stAppViewContainer"], [class*="css"] {
        font-family: "Segoe UI", system-ui, -apple-system,
                     "Helvetica Neue", Arial, sans-serif;
    }

    /* Conteneur principal : moins de vide en haut, marges latérales mesurées */
    .block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] {
        padding-top: var(--pad-top) !important;
        padding-bottom: 2rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
    }

    /* Espacement vertical resserré entre les éléments */
    [data-testid="stVerticalBlock"] { gap: var(--block-gap) !important; }

    /* Titres : tailles logiques (appliquées à toutes les balises) */
    h1, [data-testid="stHeading"] h1 {
        font-size: var(--h1) !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        letter-spacing: -0.01em;
        margin: 0 0 0.4rem 0 !important;
    }
    h2 {
        font-size: var(--h2) !important;
        font-weight: 700 !important;
        margin: 0.5rem 0 0.3rem 0 !important;
    }
    h3 {
        font-size: var(--h3) !important;
        font-weight: 600 !important;
        margin: 0.4rem 0 0.3rem 0 !important;
        border-left: 3px solid var(--wafa-orange);
        padding-left: 0.55rem;
    }

    /* Couleur charte UNIQUEMENT pour les titres natifs Streamlit
       (st.title / st.header / st.subheader). Les bannières HTML
       personnalisées (ex. app.py) conservent ainsi leur propre couleur. */
    [data-testid="stHeading"] h1,
    [data-testid="stHeading"] h2,
    [data-testid="stHeading"] h3 {
        color: var(--wafa-noir) !important;
    }

    /* Corps de texte / markdown */
    [data-testid="stMarkdownContainer"] p,
    .stMarkdown p { font-size: var(--body) !important; }

    /* Indicateurs (st.metric) en petites cartes sobres */
    [data-testid="stMetric"] {
        background: var(--wafa-gris-clair);
        border: 1px solid #ECECEC;
        border-left: 3px solid var(--wafa-orange);
        border-radius: 8px;
        padding: 0.6rem 0.9rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: var(--metric-label) !important;
        color: var(--wafa-gris-texte) !important;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    [data-testid="stMetricValue"] {
        font-size: var(--metric-value) !important;
        font-weight: 700 !important;
        color: var(--wafa-noir) !important;
    }

    /* Séparateurs discrets */
    hr { margin: 0.7rem 0 !important; border-color: #ECECEC !important; }

    /* Barre latérale resserrée */
    [data-testid="stSidebar"] { background: #FAFAFA; }
    [data-testid="stSidebarUserContent"] { padding-top: 1rem !important; }

    /* Libellés de widgets plus compacts */
    [data-testid="stWidgetLabel"] p {
        font-size: 0.85rem !important;
        color: var(--wafa-gris-texte) !important;
    }

    /* Bouton « Actualiser » au look charte (contour orange, plein au survol) */
    [data-testid="stSidebar"] button {
        border: 1px solid var(--wafa-orange) !important;
        color: var(--wafa-noir) !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] button:hover {
        background: var(--wafa-orange) !important;
        color: #FFFFFF !important;
        border-color: var(--wafa-orange) !important;
    }
    </style>
    """
    st.markdown(variables + regles, unsafe_allow_html=True)


def render_refresh_button() -> None:
    """Applique le style global puis affiche le bouton « Actualiser ».

    - Applique ``apply_compact_style`` (densité + charte) sur toute la page.
    - Au clic sur le bouton, vide le cache et relance la page.
    """
    apply_compact_style()
    if st.sidebar.button("🔄 Actualiser les données"):
        st.cache_data.clear()
        st.rerun()


def filtrer_periode(
    df: pd.DataFrame, annee_sel, periode_sel
) -> pd.DataFrame:
    """Filtre les données par année et/ou période pour l'affichage des graphes.

    Args:
        df: DataFrame complet.
        annee_sel: Année à isoler, ou "Toutes" pour ne pas filtrer.
        periode_sel: Période à isoler (T1..T4, S1, S2), ou "Toutes".

    Returns:
        Sous-ensemble du DataFrame correspondant aux filtres.
    """
    data = df
    if annee_sel != TOUTES_ANNEES:
        data = data[data["Année"] == int(annee_sel)]
    if periode_sel != TOUTES_PERIODES:
        data = data[data["Période"] == periode_sel]
    return data


def options_periode(granularity: str) -> list[str]:
    """Retourne les options du filtre Période selon la granularité choisie.

    Args:
        granularity: "Annuel", "Semestriel" ou "Trimestriel".

    Returns:
        Liste d'options pour le sélecteur de période (commence par "Toutes").
    """
    if granularity == "Trimestriel":
        return [TOUTES_PERIODES, "T1", "T2", "T3", "T4"]
    if granularity == "Semestriel":
        return [TOUTES_PERIODES, "S1", "S2"]
    return [TOUTES_PERIODES]