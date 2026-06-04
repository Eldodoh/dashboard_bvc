"""Page 3 — Analyse sectorielle de la BVC."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from calculations import get_kpi_secteur
from data_loader import load_data
from visualizations import (
    plot_companies_overlay,
    plot_market_share,
    plot_sector_aggregate,
)

from ui_utils import get_data, render_refresh_button, options_periode

render_refresh_button()
df = get_data()

st.title(" Analyse Sectorielle")

# Sélecteurs dans la sidebar
with st.sidebar:
    st.markdown("### Filtres")
    secteurs = sorted(df["Secteur"].dropna().unique())
    secteur = st.selectbox("Secteur", secteurs)

    annees = sorted(df["Année"].unique(), reverse=True)
    # Année par défaut = dernière année ayant des données annuelles complètes
    annees_completes = sorted(df[df["Période"] == "Annuel"]["Année"].unique(), reverse=True)
    annee_defaut = annees_completes[0] if annees_completes else annees[0]
    annee = st.selectbox("Année", annees, index=annees.index(annee_defaut))

    indic_dispo = sorted(df.loc[df["Secteur"] == secteur, "TypeValeur"].unique())
    indicator = st.selectbox("Indicateur", indic_dispo)

# KPI sectoriels 2x2
kpi = get_kpi_secteur(df, secteur, annee, indicator)

r1c1, r1c2 = st.columns(2)
r2c1, r2c2 = st.columns(2)

with r1c1:
    st.metric("Sociétés du secteur", kpi["nb_societes"])

with r1c2:
    yoy = kpi["yoy"]
    st.metric(
        f"Total {indicator} {annee}",
        kpi["total_fmt"],
        delta=round(float(yoy), 1) if isinstance(yoy, float) else None,
        delta_color="normal",
    )

with r2c1:
    st.metric("Variation YoY sectorielle", kpi["yoy_fmt"])

with r2c2:
    st.metric("Société leader", kpi["leader"] or "N/A")

st.markdown("---")

# --- Graphe 1 : Évolution agrégée du secteur (pleine largeur) ---
# Reste sur le df complet : le filtre Période ne le concerne pas.
st.subheader("Évolution agrégée du secteur")
fig_agg = plot_sector_aggregate(df, secteur, indicator)
st.plotly_chart(fig_agg, use_container_width=True)

st.markdown("---")

# --- Graphe 2 : Sociétés du secteur (pleine largeur, sous le précédent) ---
st.subheader("Sociétés du secteur")

granularity = st.radio(
    "Granularité",
    ["Annuel", "Semestriel", "Trimestriel"],
    horizontal=True,
    key="gran_sect",
)

# Filtre Période (dépend de la granularité) :
# options_periode renvoie ["Annuel"] / ["S1", "S2"] / ["T1", "T2", "T3", "T4"].
periodes_dispo = options_periode(granularity)
if len(periodes_dispo) <= 1:
    # Annuel : une seule période possible -> pas de filtre utile.
    periodes_sel = list(periodes_dispo)
    if periodes_dispo:
        st.caption(f"Période : {periodes_dispo[0]}")
else:
    periodes_sel = st.multiselect(
        "Période(s)",
        periodes_dispo,
        default=periodes_dispo,
        help="Filtre les périodes affichées dans ce graphe",
        key="per_sect",
    )

if not periodes_sel:
    st.warning("Sélectionnez au moins une période.")
    st.stop()

societes_sect = sorted(
    df.loc[df["Secteur"] == secteur, "Société"].unique().tolist()
)

# Garde-fou non-régression : df inchangé si toutes les périodes sont cochées,
# sinon pré-filtre des lignes par Période avant de tracer.
periodes_completes = set(periodes_sel) == set(periodes_dispo)
if periodes_completes:
    df_overlay = df
else:
    df_overlay = df[df["Période"].isin(periodes_sel)].copy()

fig_overlay = plot_companies_overlay(df_overlay, societes_sect, indicator, granularity)
st.plotly_chart(fig_overlay, use_container_width=True)

st.markdown("---")

# Parts de marché
st.subheader("Parts de marché")
mode = st.radio(
    "Mode d'affichage",
    ["Camembert", "Barres horizontales"],
    horizontal=True,
    key="mode_pdm",
)
mode_code = "pie" if mode == "Camembert" else "bar"
fig_pdm = plot_market_share(df, secteur, annee, indicator, mode=mode_code)
st.plotly_chart(fig_pdm, use_container_width=True)