"""Page 2 — Analyse d'une société cotée à la BVC."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from calculations import get_kpi_societe
from visualizations import plot_evolution_line, plot_yoy_bars
from ui_utils import (
    filtrer_periode,
    get_data,
    options_periode,
    render_refresh_button,
)


render_refresh_button()
df = get_data()

st.title(" Analyse Société")

# Sélecteurs dans la sidebar
with st.sidebar:
    st.markdown("### Filtres")
    societes = sorted(df["Société"].unique())
    societe = st.selectbox("Société", societes)

    indic_dispo = sorted(df.loc[df["Société"] == societe, "TypeValeur"].unique())
    if not indic_dispo:
        st.error("Aucun indicateur disponible pour cette société.")
        st.stop()

    indicator = st.selectbox("Indicateur", indic_dispo)

# Bloc identité société
secteur = df.loc[df["Société"] == societe, "Secteur"].iloc[0]
ticker = df.loc[df["Société"] == societe, "Ticker"].iloc[0]

st.markdown(f"""
**{societe}** &nbsp;·&nbsp; `{ticker}` &nbsp;·&nbsp; *{secteur}*

Indicateurs disponibles : {" &nbsp;·&nbsp; ".join([f"`{i}`" for i in indic_dispo])}
""")

st.markdown("---")

# KPI 2x2 (toujours calculés sur l'ensemble des données de la société)
kpi = get_kpi_societe(df, societe, indicator)
annee_label = f" ({kpi['derniere_annee']})" if kpi["derniere_annee"] else ""

r1c1, r1c2 = st.columns(2)
r2c1, r2c2 = st.columns(2)

with r1c1:
    st.metric(f"Dernière valeur{annee_label}", kpi["derniere_valeur_fmt"])

with r1c2:
    yoy = kpi["yoy_annuel"]
    st.metric(
        "Variation YoY (annuelle)",
        kpi["yoy_annuel_fmt"],
        delta=round(float(yoy), 1) if isinstance(yoy, float) else None,
        delta_color="normal",
    )

with r2c1:
    cagr = kpi["cagr"]
    st.metric(
        "CAGR 2022 → 2025",
        kpi["cagr_fmt"],
        delta=round(float(cagr), 1) if isinstance(cagr, float) else None,
        delta_color="normal",
    )

with r2c2:
    cum = kpi["croissance_cumulee"]
    st.metric(
        "Croissance cumulée 2022 → 2025",
        kpi["croissance_cumulee_fmt"],
        delta=round(float(cum), 1) if isinstance(cum, float) else None,
        delta_color="normal",
    )

st.markdown("---")

# =====================================================================
# Évolution & comparaison — contrôles communs aux deux graphes
# Granularité + filtre Année + filtre Période (s'adapte à la granularité)
# =====================================================================
st.subheader("Évolution temporelle")

cg1, cg2, cg3 = st.columns([1, 1, 1])
with cg1:
    granularity = st.radio(
        "Granularité",
        ["Annuel", "Semestriel", "Trimestriel"],
        horizontal=True,
        key="gran_societe",
    )
with cg2:
    annees_dispo = sorted([int(a) for a in df["Année"].unique()], reverse=True)
    annees_sel = st.multiselect(
        "Année(s)", annees_dispo, default=annees_dispo, key="annees_soc"
    )
with cg3:
    # "Toutes" retiré : la multi-sélection gère déjà "tout coché".
    periodes_dispo = [p for p in options_periode(granularity) if p != "Toutes"]
    if periodes_dispo:
        periodes_sel = st.multiselect(
            "Période(s)", periodes_dispo, default=periodes_dispo, key="periodes_soc"
        )
    else:
        periodes_sel = []
        st.caption("Période : Annuel")

# --- Graphe 1 : évolution temporelle ---
show_pct = st.checkbox("Axe variation %", value=False, key="show_pct_soc")
if not annees_sel or (periodes_dispo and not periodes_sel):
    st.info("Sélectionnez au moins une année et une période.")
else:
    df_g = df[df["Année"].isin(annees_sel)]
    if periodes_dispo:
        df_g = df_g[df_g["Période"].isin(periodes_sel)]
    fig_line = plot_evolution_line(
        df_g, societe, indicator, granularity, show_pct_axis=show_pct
    )
    st.plotly_chart(fig_line, use_container_width=True)

st.markdown("---")

# =====================================================================
# GRAPHE 2 — Comparaison YoY par période (filtres propres et indépendants)
# =====================================================================
st.subheader("Comparaison YoY par période")

cy1, cy2, cy3 = st.columns([1, 1, 1])
with cy1:
    granularity_yoy = st.radio(
        "Granularité",
        ["Annuel", "Semestriel", "Trimestriel"],
        horizontal=True,
        key="gran_yoy",
    )
with cy2:
    annees_dispo_yoy = sorted([int(a) for a in df["Année"].unique()], reverse=True)
    annees_sel_yoy = st.multiselect(
        "Année(s)", annees_dispo_yoy, default=annees_dispo_yoy, key="annees_yoy"
    )
with cy3:
    periodes_dispo_yoy = [p for p in options_periode(granularity_yoy) if p != "Toutes"]
    if periodes_dispo_yoy:
        periodes_sel_yoy = st.multiselect(
            "Période(s)", periodes_dispo_yoy, default=periodes_dispo_yoy, key="periodes_yoy"
        )
    else:
        periodes_sel_yoy = []
        st.caption("Période : Annuel")

if not annees_sel_yoy or (periodes_dispo_yoy and not periodes_sel_yoy):
    st.info("Sélectionnez au moins une année et une période.")
else:
    df_yoy = df[df["Année"].isin(annees_sel_yoy)]
    if periodes_dispo_yoy:
        df_yoy = df_yoy[df_yoy["Période"].isin(periodes_sel_yoy)]
    fig_yoy = plot_yoy_bars(df_yoy, societe, indicator, granularity_yoy)
    st.plotly_chart(fig_yoy, use_container_width=True)
