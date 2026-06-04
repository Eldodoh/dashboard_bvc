"""Fonctions de calcul financier pures pour le dashboard BVC.

Toutes les fonctions sont pures (sans Streamlit, sans I/O).

Règles cas limites :
  - Dénominateur nul ou valeur manquante  -> None  (affiché N/A)
  - Changement de signe (négatif->positif) -> LABEL_NM (affiché N/M)
  - Jamais remplacer une valeur manquante par 0
"""
from __future__ import annotations

from typing import Union

import numpy as np
import pandas as pd

from config import (
    ANNEE_DEBUT,
    LABEL_NA,
    LABEL_NM,
    PERIODE_ANNUELLE,
    PERIODES_SEMESTRIELLES,
    PERIODES_TRIMESTRIELLES,
    INDICATEUR_CA,
)

CalcResult = Union[float, str, None]


def compute_yoy(value_n, value_n_minus_1):
    if value_n is None or value_n_minus_1 is None:
        return None
    try:
        vn, vn1 = float(value_n), float(value_n_minus_1)
    except (TypeError, ValueError):
        return None
    if np.isnan(vn) or np.isnan(vn1):
        return None
    if vn1 == 0:
        return None
    if (vn1 < 0 < vn) or (vn < 0 < vn1):
        return LABEL_NM
    return (vn - vn1) / abs(vn1) * 100


def compute_cagr(initial, final, years):
    if initial is None or final is None or years <= 0:
        return None
    try:
        vi, vf = float(initial), float(final)
    except (TypeError, ValueError):
        return None
    if np.isnan(vi) or np.isnan(vf):
        return None
    if vi == 0:
        return None
    if (vi < 0 < vf) or (vf < 0 < vi) or (vi < 0 and vf < 0):
        return LABEL_NM
    return ((vf / vi) ** (1 / years) - 1) * 100


def format_mmad(value):
    if value is None:
        return LABEL_NA
    try:
        v = float(value)
    except (TypeError, ValueError):
        return LABEL_NA
    if np.isnan(v):
        return LABEL_NA
    if abs(v) >= 1000:
        mmdh = v / 1000
        s = f"{mmdh:,.2f}"
        s = s.replace(",", "XXXX").replace(".", ",").replace("XXXX", " ")
        return f"{s} MMDH"
    return f"{v:,.0f}".replace(",", " ") + " MMAD"


def format_pct(value):
    if value is None:
        return LABEL_NA
    if isinstance(value, str):
        return value
    try:
        v = float(value)
    except (TypeError, ValueError):
        return LABEL_NA
    sign = "+" if v >= 0 else "-"
    return f"{sign}{abs(v):.1f} %".replace(".", ",")


def get_company_series(df, societe, indicator, granularity):
    mask = (
        (df["Société"] == societe)
        & (df["TypeValeur"] == indicator)
        & (df["TypePériode"] == granularity)
    )
    result = df.loc[mask, ["Année", "Période", "Valeur"]].copy()
    if granularity == "Trimestriel":
        ordre = PERIODES_TRIMESTRIELLES
    elif granularity == "Semestriel":
        ordre = PERIODES_SEMESTRIELLES
    else:
        ordre = [PERIODE_ANNUELLE]
    result["Période"] = pd.Categorical(result["Période"], categories=ordre, ordered=True)
    return result.sort_values(["Année", "Période"]).reset_index(drop=True)


def get_last_annual_value(df, societe, indicator):
    mask = (
        (df["Société"] == societe)
        & (df["TypeValeur"] == indicator)
        & (df["TypePériode"] == "Annuel")
    )
    data = df.loc[mask].dropna(subset=["Valeur"])
    if data.empty:
        return None, None
    row = data.loc[data["Année"].idxmax()]
    return int(row["Année"]), float(row["Valeur"])


def get_kpi_societe(df, societe, indicator):
    ann = df.loc[
        (df["Société"] == societe)
        & (df["TypeValeur"] == indicator)
        & (df["TypePériode"] == "Annuel")
    ].dropna(subset=["Valeur"]).sort_values("Année")

    if ann.empty:
        return _empty_kpi()

    derniere_annee, derniere_valeur = get_last_annual_value(df, societe, indicator)
    annees_dispo = sorted(ann["Année"].unique())
    idx = annees_dispo.index(derniere_annee)
    valeur_n1 = (
        float(ann.loc[ann["Année"] == annees_dispo[idx - 1], "Valeur"].iloc[0])
        if idx > 0 else None
    )
    row_2022 = ann.loc[ann["Année"] == ANNEE_DEBUT, "Valeur"]
    valeur_2022 = float(row_2022.iloc[0]) if not row_2022.empty else None

    yoy = compute_yoy(derniere_valeur, valeur_n1)
    n_years = (derniere_annee - ANNEE_DEBUT) if derniere_annee else 0
    cagr = compute_cagr(valeur_2022, derniere_valeur, n_years) if n_years > 0 else None
    croissance_cumulee = compute_yoy(derniere_valeur, valeur_2022)

    return {
        "derniere_annee": derniere_annee,
        "derniere_valeur": derniere_valeur,
        "derniere_valeur_fmt": format_mmad(derniere_valeur),
        "yoy_annuel": yoy,
        "yoy_annuel_fmt": format_pct(yoy),
        "cagr": cagr,
        "cagr_fmt": format_pct(cagr),
        "croissance_cumulee": croissance_cumulee,
        "croissance_cumulee_fmt": format_pct(croissance_cumulee),
    }


def _empty_kpi():
    na = LABEL_NA
    return {
        "derniere_annee": None, "derniere_valeur": None,
        "derniere_valeur_fmt": na, "yoy_annuel": None,
        "yoy_annuel_fmt": na, "cagr": None, "cagr_fmt": na,
        "croissance_cumulee": None, "croissance_cumulee_fmt": na,
    }


def get_yoy_by_company(df, indicator, year):
    ann = df.loc[
        (df["TypeValeur"] == indicator)
        & (df["TypePériode"] == "Annuel")
        & (df["Année"].isin([year - 1, year]))
    ].copy()

    pivot = ann.pivot_table(
        index=["Société", "Secteur"],
        columns="Année",
        values="Valeur",
        aggfunc="first",
    ).reset_index()
    pivot.columns.name = None

    if year not in pivot.columns:
        pivot[year] = None
    if year - 1 not in pivot.columns:
        pivot[year - 1] = None

    pivot["YoY"] = pivot.apply(
        lambda r: compute_yoy(r[year], r[year - 1]), axis=1
    )
    pivot["YoY_fmt"] = pivot["YoY"].apply(format_pct)
    pivot["Valeur_N"] = pivot[year]
    pivot["Valeur_N_fmt"] = pivot[year].apply(format_mmad)

    return pivot[
        ["Société", "Secteur", "Valeur_N", "Valeur_N_fmt", "YoY", "YoY_fmt"]
    ].copy()


def get_kpi_overview(df, year, indicator=INDICATEUR_CA):
    ann = df.loc[(df["TypeValeur"] == indicator) & (df["TypePériode"] == "Annuel")]
    ca_year = ann.loc[ann["Année"] == year, "Valeur"].dropna()
    total_ca = float(ca_year.sum()) if not ca_year.empty else None
    nb_societes = int(ann.loc[ann["Année"] == year, "Société"].nunique())
    nb_secteurs = int(df["Secteur"].nunique(dropna=True))

    yoy_df = get_yoy_by_company(df, indicator, year)
    yoy_valides = [
        float(v) for v in yoy_df["YoY"]
        if isinstance(v, (int, float)) and not np.isnan(float(v))
    ]
    croissance_moyenne = float(np.mean(yoy_valides)) if yoy_valides else None

    return {
        "total_ca": total_ca,
        "total_ca_fmt": format_mmad(total_ca),
        "nb_societes": nb_societes,
        "croissance_moyenne_yoy": croissance_moyenne,
        "croissance_moyenne_yoy_fmt": format_pct(croissance_moyenne),
        "nb_secteurs": nb_secteurs,
    }


def get_kpi_secteur(df, sector, year, indicator=INDICATEUR_CA):
    data = df.loc[
        (df["Secteur"] == sector)
        & (df["TypeValeur"] == indicator)
        & (df["TypePériode"] == "Annuel")
    ]
    nb_societes = int(data["Société"].nunique())
    total_n = _safe_sum(data, year)
    total_n1 = _safe_sum(data, year - 1)
    yoy = compute_yoy(total_n, total_n1)
    by_soc = data.loc[data["Année"] == year].groupby("Société")["Valeur"].sum()
    leader = str(by_soc.idxmax()) if not by_soc.empty else None

    return {
        "nb_societes": nb_societes,
        "total": total_n,
        "total_fmt": format_mmad(total_n),
        "yoy": yoy,
        "yoy_fmt": format_pct(yoy),
        "leader": leader,
    }


def _safe_sum(data, year):
    vals = data.loc[data["Année"] == year, "Valeur"].dropna()
    return float(vals.sum()) if not vals.empty else None


def get_market_share(df, sector, year, indicator=INDICATEUR_CA):
    data = df.loc[
        (df["Secteur"] == sector)
        & (df["TypeValeur"] == indicator)
        & (df["TypePériode"] == "Annuel")
        & (df["Année"] == year)
    ].dropna(subset=["Valeur"])

    if data.empty:
        return pd.DataFrame(columns=["Société", "Valeur", "Part_pct"])

    by_soc = data.groupby("Société")["Valeur"].sum().reset_index()
    total = by_soc["Valeur"].sum()
    by_soc["Part_pct"] = by_soc["Valeur"] / total * 100 if total != 0 else None
    return by_soc.sort_values("Part_pct", ascending=False).reset_index(drop=True)


def get_sector_aggregate(df, sector, indicator, granularity="Annuel"):
    data = df.loc[
        (df["Secteur"] == sector)
        & (df["TypeValeur"] == indicator)
        & (df["TypePériode"] == granularity)
    ].dropna(subset=["Valeur"])

    agg = (
        data.groupby(["Année", "Période"])["Valeur"]
        .sum()
        .reset_index()
        .rename(columns={"Valeur": "Total"})
    )

    if granularity == "Trimestriel":
        ordre = PERIODES_TRIMESTRIELLES
    elif granularity == "Semestriel":
        ordre = PERIODES_SEMESTRIELLES
    else:
        ordre = [PERIODE_ANNUELLE]

    agg["Période"] = pd.Categorical(agg["Période"], categories=ordre, ordered=True)
    return agg.sort_values(["Année", "Période"]).reset_index(drop=True)
# =============================================================================
# CA AGRÉGÉ TRIMESTRIEL (hors sociétés exclues) — Vue d'Ensemble
# =============================================================================

def get_ca_agrege_trimestriel(df, trimestre, annee, exclusions=None, indicator=INDICATEUR_CA):
    """Somme le CA agrégé d'un trimestre/année, hors sociétés exclues.

    Returns:
        Total agrégé (float) ou None si aucune donnée.
    """
    exclusions = exclusions or []
    data = df.loc[
        (df["TypeValeur"] == indicator)
        & (df["TypePériode"] == "Trimestriel")
        & (df["Période"] == trimestre)
        & (df["Année"] == annee)
        & (~df["Société"].isin(exclusions))
    ].dropna(subset=["Valeur"])
    return float(data["Valeur"].sum()) if not data.empty else None


def get_kpi_ca_trimestriel(df, trimestre, annee, exclusions=None, indicator=INDICATEUR_CA):
    """KPI du CA agrégé d'un trimestre + YoY vs même trimestre N-1."""
    total_n = get_ca_agrege_trimestriel(df, trimestre, annee, exclusions, indicator)
    total_n1 = get_ca_agrege_trimestriel(df, trimestre, annee - 1, exclusions, indicator)
    yoy = compute_yoy(total_n, total_n1)
    return {
        "total": total_n,
        "total_fmt": format_mmad(total_n),
        "yoy": yoy,
        "yoy_fmt": format_pct(yoy),
    }


def get_ca_trimestriel_table(df, trimestres, annees, exclusions=None, indicator=INDICATEUR_CA):
    """Table des totaux CA agrégés pour chaque (année, trimestre) + YoY."""
    rows = []
    for annee in sorted(annees):
        for trim in sorted(trimestres):
            total = get_ca_agrege_trimestriel(df, trim, annee, exclusions, indicator)
            total_n1 = get_ca_agrege_trimestriel(df, trim, annee - 1, exclusions, indicator)
            yoy = compute_yoy(total, total_n1)
            rows.append({
                "Année": annee, "Trimestre": trim, "Label": f"{trim} {annee}",
                "Total": total, "Total_fmt": format_mmad(total),
                "YoY": yoy, "YoY_fmt": format_pct(yoy),
            })
    return pd.DataFrame(rows)