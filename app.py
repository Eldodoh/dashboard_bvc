"""Point d'entrée du dashboard BVC — Wafa Gestion.

Lancement : streamlit run app.py
"""
import sys
from pathlib import Path

import streamlit as st

from ui_utils import apply_compact_style

apply_compact_style()

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import COLOR_BLACK, COLOR_ORANGE, COLOR_WHITE
from data_loader import get_data_quality_report, load_data

st.set_page_config(
    page_title="Dashboard BVC — Wafa Gestion",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Injection CSS charte Wafa Gestion
# Chargement de la police Inter (Google Fonts)
st.markdown(
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap">',
    unsafe_allow_html=True,
)

# CSS charte Wafa Gestion
st.markdown("""
<style>
html, body, [class*="css"], .stMarkdown, h1, h2, h3, p, div, span, label, button {
    font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif !important;
}
[data-testid="stSidebar"] { background-color: #F5F5F5 !important; }
div[data-testid="metric-container"] {
    background: #FFFFFF;
    border-left: 4px solid #F39200;
    padding: 1rem;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def get_df():
    """Chargement mis en cache pour toute la session."""
    return load_data()


@st.cache_data
def get_report():
    return get_data_quality_report(get_df())


df = get_df()
report = get_report()

# Affichage dans le terminal au premier chargement
import logging
logging.getLogger(__name__).info(
    f"Dashboard BVC | {report['nb_societes']} sociétés "
    f"| {report['nb_secteurs']} secteurs "
    f"| {min(report['annees'])}–{max(report['annees'])}"
)

# En-tête principal
st.markdown(f"""
<div style="background:{COLOR_BLACK};padding:1rem 1.5rem;
            margin-bottom:1.2rem;border-radius:6px;">
  <h1 style="color:{COLOR_WHITE};margin:0;font-family:Arial,sans-serif;font-size:1.6rem;">
    <span style="color:{COLOR_ORANGE};">●</span>&nbsp; Dashboard BVC
  </h1>
  <p style="color:#9CA3AF;margin:0.25rem 0 0;font-size:0.82rem;">
    Wafa Gestion &nbsp;·&nbsp; {report['nb_societes']} sociétés
    &nbsp;·&nbsp; {report['nb_secteurs']} secteurs
    &nbsp;·&nbsp; {min(report['annees'])}–{max(report['annees'])}
  </p>
</div>
""", unsafe_allow_html=True)

st.info("👈 Sélectionnez une page dans le menu latéral pour commencer l'analyse.", icon="📊")

# Sidebar
with st.sidebar:
    st.markdown(
        f"<h2 style='color:{COLOR_ORANGE};font-family:Arial;margin-top:0'>📊 BVC</h2>",
        unsafe_allow_html=True,
    )
    st.caption(f"Données : {min(report['annees'])} – {max(report['annees'])}")

    if report["societes_couverture_faible"]:
        st.markdown("---")
        st.warning("Couverture incomplète :")
        for soc, n in sorted(report["societes_couverture_faible"], key=lambda x: x[1]):
            st.caption(f"• {soc} ({n} obs.)")