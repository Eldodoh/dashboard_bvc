"""Page 1 — Vue d'Ensemble du marché BVC."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from config import SOCIETES_EXCLUES_CA
from calculations import (
    get_ca_trimestriel_table,
    get_kpi_ca_trimestriel,
    get_kpi_overview,
)
from visualizations import plot_ca_trimestriel_compare, plot_top_flop_yoy
from ui_utils import get_data, render_refresh_button

render_refresh_button()
df = get_data()

st.title("Vue d'Ensemble")

# Filtre année
annees = sorted(df["Année"].unique(), reverse=True)
# Année par défaut = dernière année ayant des données annuelles complètes
annees_completes = sorted(df[df["Période"] == "Annuel"]["Année"].unique(), reverse=True)
annee_defaut = annees_completes[0] if annees_completes else annees[0]
annee = st.selectbox("Année d'analyse", annees, index=annees.index(annee_defaut))

st.markdown("---")

# =====================================================================
# INDICATEURS ANNUELS — filtre Avec / Hors énergie
# =====================================================================
st.markdown("### Indicateurs annuels du marché")

perimetre_annuel = st.radio(
    "Périmètre du calcul",
    ["Hors énergie", "Avec énergie"],
    horizontal=True,
    key="perimetre_annuel",
)
hors_energie_annuel = perimetre_annuel == "Hors énergie"
suffixe_a = "hors énergie" if hors_energie_annuel else "énergie incluse"

st.caption(
    f"Total CA agrégé et croissance moyenne — **{suffixe_a}** "
    "(AFRIQUIA GAZ, TAQA MOROCCO, TOTALENERGIES). "
    
)

# Total CA + croissance : selon le périmètre choisi ; nb sociétés/secteurs : marché complet
df_hors_energie = df[~df["Société"].isin(SOCIETES_EXCLUES_CA)]
kpi_complet = get_kpi_overview(df, annee)
kpi_choisi = get_kpi_overview(df_hors_energie if hors_energie_annuel else df, annee)

r1c1, r1c2 = st.columns(2)
r2c1, r2c2 = st.columns(2)

with r1c1:
    st.metric(
        f"Total CA agrégé ({suffixe_a})",
        kpi_choisi["total_ca_fmt"],
        help=f"Somme des CA annuels {annee} — {suffixe_a}",
    )

with r1c2:
    yoy = kpi_choisi["croissance_moyenne_yoy"]
    st.metric(
        f"Croissance moyenne YoY ({suffixe_a})",
        kpi_choisi["croissance_moyenne_yoy_fmt"],
        delta=round(float(yoy), 1) if isinstance(yoy, float) else None,
        delta_color="normal",
        help="Moyenne simple des variations YoY — exclut les N/M et N/A",
    )

with r2c1:
    st.metric("Sociétés couvertes", kpi_complet["nb_societes"])

with r2c2:
    st.metric("Secteurs représentés", kpi_complet["nb_secteurs"])

st.markdown("---")

# =====================================================================
# CA AGRÉGÉ TRIMESTRIEL — filtre Avec / Hors énergie + 2 modes
# =====================================================================
st.markdown("### CA agrégé trimestriel")

perimetre_trim = st.radio(
    "Périmètre du calcul",
    ["Hors énergie", "Avec énergie"],
    horizontal=True,
    key="perimetre_trim",
)
exclusions_trim = SOCIETES_EXCLUES_CA if perimetre_trim == "Hors énergie" else []
suffixe_t = "hors énergie" if perimetre_trim == "Hors énergie" else "énergie incluse"

st.caption(
    f"Chiffre d'affaires agrégé par trimestre — **{suffixe_t}** "
    "(AFRIQUIA GAZ, TAQA MOROCCO, TOTALENERGIES). "
    
)

trimestres_dispo = ["T1", "T2", "T3", "T4"]
annees_dispo = sorted(df["Année"].unique(), reverse=True)

mode = st.radio(
    "Mode d'affichage",
    ["Trimestre unique", "Comparaison multi-trimestres"],
    horizontal=True,
    key="mode_ca_trim",
)

if mode == "Trimestre unique":
    c1, c2 = st.columns(2)
    with c1:
        trim_sel = st.selectbox("Trimestre", trimestres_dispo, key="trim_unique")
    with c2:
        annee_sel = st.selectbox("Année", annees_dispo, index=0, key="annee_unique")

    kpi_trim = get_kpi_ca_trimestriel(df, trim_sel, annee_sel, exclusions_trim)
    yoy_t = kpi_trim["yoy"]
    k1, k2 = st.columns(2)
    with k1:
        st.metric(
            f"CA agrégé {trim_sel} {annee_sel} ({suffixe_t})",
            kpi_trim["total_fmt"],
        )
    with k2:
        st.metric(
            f"YoY vs {trim_sel} {annee_sel - 1}",
            kpi_trim["yoy_fmt"],
            delta=round(float(yoy_t), 1) if isinstance(yoy_t, float) else None,
            delta_color="normal",
        )
else:
    c1, c2 = st.columns(2)
    with c1:
        trims_sel = st.multiselect(
            "Trimestres", trimestres_dispo, default=trimestres_dispo, key="trims_multi"
        )
    with c2:
        annees_par_defaut = [a for a in annees_dispo if a in annees_completes][:2]
        annees_sel = st.multiselect(
            "Années", annees_dispo,
            default=annees_par_defaut or annees_dispo[:2], key="annees_multi"
        )

    if trims_sel and annees_sel:
        table = get_ca_trimestriel_table(df, trims_sel, annees_sel, exclusions_trim)
        fig_trim = plot_ca_trimestriel_compare(table)
        st.plotly_chart(fig_trim, use_container_width=True)
    else:
        st.info("Sélectionnez au moins un trimestre et une année.")

st.markdown("---")

# =====================================================================
# Top 10 / Flop 10
# =====================================================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Top 10 — Fortes hausses")
    fig_top = plot_top_flop_yoy(df, annee, top=True, n=10)
    st.plotly_chart(fig_top, use_container_width=True)

with col2:
    st.subheader("Flop 10 — Fortes baisses")
    fig_flop = plot_top_flop_yoy(df, annee, top=False, n=10)
    st.plotly_chart(fig_flop, use_container_width=True)
