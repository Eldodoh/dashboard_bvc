"""Page 4 — Comparaison multi-sociétés."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from calculations import format_mmad, get_company_series
from data_loader import load_data
from config import ANNEE_DEBUT, ANNEE_FIN, INDICATEURS
from visualizations import plot_companies_overlay

from ui_utils import get_data, render_refresh_button, options_periode

render_refresh_button()
df = get_data()

st.title(" Comparaison Multi-Sociétés")

# Sélecteurs dans la sidebar
with st.sidebar:
    st.markdown("### Filtres")
    societes_dispo = sorted(df["Société"].unique())

    societes_sel = st.multiselect(
        "Sociétés à comparer",
        societes_dispo,
        default=societes_dispo[:3],
        help="Sélectionnez 2 à 10 sociétés",
    )

    indicator = st.selectbox("Indicateur", INDICATEURS)
    granularity = st.radio("Granularité", ["Annuel", "Semestriel", "Trimestriel"])

    # --- Filtre Période (dépend de la granularité) ---
    # options_periode renvoie les libellés de période pour la granularité :
    # ["Annuel"] / ["S1", "S2"] / ["T1", "T2", "T3", "T4"].
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
            help="Filtre les périodes affichées (graphe + tableau)",
        )

    annee_min, annee_max = st.slider(
        "Plage d'années",
        min_value=ANNEE_DEBUT,
        max_value=ANNEE_FIN,
        value=(ANNEE_DEBUT, ANNEE_FIN),
    )

if not societes_sel:
    st.warning("👈 Sélectionnez au moins une société dans le menu latéral.")
    st.stop()

if not periodes_sel:
    st.warning("👈 Sélectionnez au moins une période dans le menu latéral.")
    st.stop()

# Filtrer les sociétés ayant l'indicateur sélectionné
societes_valides = [
    s for s in societes_sel
    if indicator in df.loc[df["Société"] == s, "TypeValeur"].values
]
societes_ignorees = set(societes_sel) - set(societes_valides)

if societes_ignorees:
    st.info(
        f"Sociétés ignorées (pas de données '{indicator}') : "
        f"{', '.join(sorted(societes_ignorees))}"
    )

if not societes_valides:
    st.warning(f"Aucune société sélectionnée n'a de données pour '{indicator}'.")
    st.stop()

st.markdown("---")

# Courbes superposées
st.subheader("Évolution comparative")

# Garde-fou non-régression : si toutes les périodes sont sélectionnées,
# on passe le df INCHANGÉ (comportement identique à avant le filtre).
# Sinon, on pré-filtre les lignes par Période avant de tracer.
periodes_completes = set(periodes_sel) == set(periodes_dispo)
if periodes_completes:
    df_chart = df
else:
    df_chart = df[df["Période"].isin(periodes_sel)].copy()

fig = plot_companies_overlay(df_chart, societes_valides, indicator, granularity)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Tableau comparatif
st.subheader("Tableau des valeurs")

annees_sel = list(range(annee_min, annee_max + 1))
rows = []
for soc in societes_valides:
    series = get_company_series(df, soc, indicator, granularity)
    series = series.loc[series["Année"].isin(annees_sel)]
    # Filtre Période appliqué sur la sortie déjà résolue par granularité.
    series = series.loc[series["Période"].isin(periodes_sel)]
    series = series.dropna(subset=["Valeur"])
    for _, row in series.iterrows():
        label = f"{row['Période']} {int(row['Année'])}"
        rows.append({
            "Société": soc,
            "Période": label,
            "Valeur (MMAD)": row["Valeur"],
            "Année": int(row["Année"]),
        })

if not rows:
    st.info("Aucune donnée disponible pour la sélection actuelle.")
else:
    result = pd.DataFrame(rows)

    # Pivot : lignes = société, colonnes = période
    pivot = result.pivot_table(
        index="Société",
        columns="Période",
        values="Valeur (MMAD)",
        aggfunc="first",
    )
    pivot = pivot.map(lambda x: format_mmad(x) if pd.notna(x) else "—")

    st.dataframe(pivot, use_container_width=True)

    # Suffixe périodes pour le nom de fichier (si sélection restreinte)
    suffixe_periodes = "" if periodes_completes else "_" + "-".join(periodes_sel)

    # Export CSV
    csv_data = result[["Société", "Période", "Valeur (MMAD)"]].to_csv(
        index=False, sep=";", decimal=","
    )
    st.download_button(
        label="⬇️ Télécharger le CSV",
        data=csv_data,
        file_name=f"comparaison_{indicator}_{granularity}{suffixe_periodes}.csv",
        mime="text/csv",
    )