"""
data_loader.py — Chargement des données BVC.

Sources de vérité (Google Sheets en ligne, Excel en local hors ligne) :
    - « Trims »      : CA / Capex / Endettement, format large TRIMESTRIEL.
                       S1/S2/Annuel y sont RECALCULÉS selon la nature comptable :
                           FLUX  (CA, Capex)   : S1=T1+T2, S2=T3+T4, Annuel=ΣT
                           STOCK (Endettement) : S1=T2,   S2=T4,   Annuel=T4
    - « Semestriel » : seules les lignes RN sont lues (colonnes S1_AAAA / S2_AAAA).
    - « Annuel »     : seules les lignes RN sont lues (colonnes d'années pures AAAA ;
                       les colonnes « Var %_… » sont ignorées).

Le Résultat Net (RN) n'existe qu'en semestriel et annuel : il n'a jamais de
valeur trimestrielle. Une période n'est jamais fabriquée à partir d'une donnée
manquante : une case vide reste absente (affichée « N/A » côté interface), jamais 0.
"""
from __future__ import annotations

import math
import re
from urllib.parse import quote

import pandas as pd

from config import (
    EXCEL_PATH,
    GSHEET_ANNUEL_TAB,
    GSHEET_ID,
    GSHEET_SEMESTRIEL_TAB,
    GSHEET_TRIMS_TAB,
    INDICATEUR_RN,
    SHEET_ANNUEL,
    SHEET_SEMESTRIEL,
    SHEET_TRIMS,
)

# --- Nature comptable des indicateurs lus depuis « Trims » ---
INDICATEURS_FLUX = {"CA", "Capex"}        # additifs sur la période
INDICATEURS_STOCK = {"Endettement"}        # valeur de fin de période

TRIMESTRES = ["T1", "T2", "T3", "T4"]

# Reconnaissance des colonnes de période dans Semestriel / Annuel
RE_COL_SEMESTRE = re.compile(r"S[12]_\d{4}")   # ex. "S1_2022"
RE_COL_ANNEE = re.compile(r"\d{4}")            # ex. "2022" (exclut "Var %_22-23")

# En dessous de ce nombre de lignes, une société est jugée « peu couverte »
SEUIL_COUVERTURE_FAIBLE = 20


def _read_tab_raw(
    gsheet_tab: str, excel_sheet: str, excel_path: str | None = None
) -> pd.DataFrame:
    """Lit un onglet brut (format large), depuis Google Sheets ou Excel.

    - Si ``config.GSHEET_ID`` est renseigné : lecture du Google Sheet en ligne
      (onglet ``gsheet_tab``) via son export CSV public. ``headers=1`` force la
      1re ligne comme en-tête (sinon Google ne la détecte pas quand la 1re
      colonne est du texte).
    - Sinon : lecture de l'onglet ``excel_sheet`` du fichier Excel local.

    Args:
        gsheet_tab: Nom de l'onglet côté Google Sheets.
        excel_sheet: Nom de l'onglet côté Excel.
        excel_path: Chemin Excel (utilisé uniquement si GSHEET_ID est vide).

    Returns:
        DataFrame brut de l'onglet (en-têtes en première ligne).
    """
    if GSHEET_ID:
        url = (
            f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}"
            f"/gviz/tq?tqx=out:csv&headers=1&sheet={quote(gsheet_tab)}"
        )
        return pd.read_csv(url)
    chemin = excel_path if excel_path is not None else EXCEL_PATH
    return pd.read_excel(chemin, sheet_name=excel_sheet, header=0)


def _read_trims_raw(excel_path: str | None = None) -> pd.DataFrame:
    """Lit l'onglet Trims brut (format large). Voir :func:`_read_tab_raw`."""
    return _read_tab_raw(GSHEET_TRIMS_TAB, SHEET_TRIMS, excel_path)


def _to_float(value) -> float | None:
    """Convertit une valeur de cellule en float, ou None si vide/illisible.

    Gère les nombres déjà numériques (lecture Excel) et les chaînes formatées
    à la française venant de Google Sheets : séparateur de milliers = espace
    fine insécable (U+202F), espace insécable (U+00A0) ou espace normale ;
    signe moins éventuellement suivi d'un espace ; décimale en virgule.

    Args:
        value: Contenu brut d'une cellule (nombre, chaîne, None ou NaN).

    Returns:
        La valeur en float, ou None si la cellule est vide / non convertible.
        On ne remplace jamais une donnée manquante par 0.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if (isinstance(value, float) and math.isnan(value)) else float(value)
    texte = str(value).strip()
    if texte == "" or texte.lower() == "nan":
        return None
    for espace in (" ", "\u00a0", "\u202f"):
        texte = texte.replace(espace, "")
    texte = texte.replace(",", ".")  # décimale française éventuelle
    try:
        return float(texte)
    except ValueError:
        return None


def build_sector_mapping(df_trims: pd.DataFrame) -> dict[str, str]:
    """Construit la correspondance {société: secteur} depuis la feuille Trims.

    Une ligne sans Ticker est un en-tête de secteur ; toutes les sociétés
    qui la suivent héritent de ce secteur jusqu'au prochain en-tête.

    Args:
        df_trims: DataFrame brut de la feuille Trims.

    Returns:
        Dictionnaire associant chaque nom de société à son secteur.
    """
    mapping: dict[str, str] = {}
    secteur_courant: str | None = None
    for _, row in df_trims.iterrows():
        nom = str(row["Mmad"]).strip()
        ticker = row["Ticker"]
        est_entete = pd.isna(ticker) or str(ticker).strip() == ""
        if est_entete:
            if nom and nom.lower() != "nan":
                secteur_courant = nom
        elif nom and nom.lower() != "nan":
            mapping[nom] = secteur_courant
    return mapping


def _periodes_depuis_trimestres(
    vals: dict[str, float | None], est_flux: bool
) -> list[tuple[str, float, str]]:
    """Calcule S1/S2/Annuel à partir des 4 trimestres d'une année.

    Args:
        vals: Valeurs trimestrielles {"T1": .., "T2": .., "T3": .., "T4": ..}
            (None si le trimestre est absent).
        est_flux: True pour un indicateur additif (CA, Capex), False pour
            un indicateur de stock (Endettement).

    Returns:
        Liste de tuples (période, valeur, type_période). Une période n'est
        incluse que si les trimestres nécessaires sont présents.
    """
    res: list[tuple[str, float, str]] = []
    if est_flux:
        if vals["T1"] is not None and vals["T2"] is not None:
            res.append(("S1", vals["T1"] + vals["T2"], "Semestriel"))
        if vals["T3"] is not None and vals["T4"] is not None:
            res.append(("S2", vals["T3"] + vals["T4"], "Semestriel"))
        if all(vals[t] is not None for t in TRIMESTRES):
            res.append(("Annuel", sum(vals[t] for t in TRIMESTRES), "Annuel"))
    else:
        if vals["T2"] is not None:
            res.append(("S1", vals["T2"], "Semestriel"))
        if vals["T4"] is not None:
            res.append(("S2", vals["T4"], "Semestriel"))
            res.append(("Annuel", vals["T4"], "Annuel"))
    return res


def _lire_lignes_rn(excel_path: str | None = None) -> list[list]:
    """Lit le Résultat Net (RN) depuis les feuilles Semestriel et Annuel.

    Ne garde QUE les lignes dont ``TypeValeur`` vaut ``RN`` (les CA/Capex/
    Endettement éventuellement présents dans ces feuilles sont ignorés : ils
    restent gérés par « Trims »). Le RN n'a pas de valeur trimestrielle.

    - Semestriel : colonnes ``S1_AAAA`` / ``S2_AAAA`` -> périodes S1 / S2.
    - Annuel     : colonnes d'années pures ``AAAA``   -> période Annuel
                   (les colonnes « Var %_… » sont ignorées).

    Le nom de la société est pris dans la 1re colonne, dont l'intitulé diffère
    selon la feuille (« Mmad » / « Colonne1 ») : on lit donc ``df.columns[0]``.

    Args:
        excel_path: Chemin Excel (utilisé uniquement si GSHEET_ID est vide).

    Returns:
        Liste de lignes [Société, Ticker, TypeValeur, Année, Période, Valeur,
        TypePériode] prêtes à être ajoutées au tableau long.
    """
    lignes: list[list] = []

    def _lignes_depuis(
        df: pd.DataFrame, cols_periode: list[str], periode_fixe: str | None,
        type_periode: str,
    ) -> None:
        df.columns = [str(c).strip() for c in df.columns]
        col_nom = df.columns[0]  # « Mmad » (Semestriel) ou « Colonne1 » (Annuel)
        for _, row in df[df["Ticker"].notna()].iterrows():
            if str(row["TypeValeur"]).strip() != INDICATEUR_RN:
                continue
            soc = str(row[col_nom]).strip()
            if not soc or soc.lower() == "nan":
                continue
            ticker = str(row["Ticker"]).strip()
            for col in cols_periode:
                val = _to_float(row.get(col))
                if val is None:
                    continue  # case vide -> on n'invente jamais de 0
                if periode_fixe is None:          # Semestriel : "S1_2022"
                    periode, annee = col.split("_")
                else:                              # Annuel : "2022"
                    periode, annee = periode_fixe, col
                lignes.append(
                    [soc, ticker, INDICATEUR_RN, int(annee), periode, val, type_periode]
                )

    # --- Semestriel (S1 / S2) ---
    df_sem = _read_tab_raw(GSHEET_SEMESTRIEL_TAB, SHEET_SEMESTRIEL, excel_path)
    df_sem.columns = [str(c).strip() for c in df_sem.columns]
    cols_sem = [c for c in df_sem.columns if RE_COL_SEMESTRE.fullmatch(c)]
    _lignes_depuis(df_sem, cols_sem, periode_fixe=None, type_periode="Semestriel")

    # --- Annuel ---
    df_ann = _read_tab_raw(GSHEET_ANNUEL_TAB, SHEET_ANNUEL, excel_path)
    df_ann.columns = [str(c).strip() for c in df_ann.columns]
    cols_ann = [c for c in df_ann.columns if RE_COL_ANNEE.fullmatch(c)]
    _lignes_depuis(df_ann, cols_ann, periode_fixe="Annuel", type_periode="Annuel")

    return lignes


def load_data(excel_path: str | None = None) -> pd.DataFrame:
    """Charge Trims (CA/Capex/Endettement) + RN (Semestriel/Annuel).

    Args:
        excel_path: Chemin Excel (utilisé uniquement si GSHEET_ID est vide).

    Returns:
        DataFrame avec les colonnes : Société, Ticker, TypeValeur, Année,
        Période, Valeur, TypePériode, Secteur.
    """
    df = _read_trims_raw(excel_path)
    df.columns = [str(c).strip() for c in df.columns]
    df["Mmad"] = df["Mmad"].astype(str).str.strip()
    df["TypeValeur"] = df["TypeValeur"].astype(str).str.strip()

    secteurs = build_sector_mapping(df)
    annees = sorted({int(c.split("_")[0]) for c in df.columns if "_T" in c})

    lignes: list[list] = []
    societes = df[df["Ticker"].notna()]
    for _, row in societes.iterrows():
        soc = row["Mmad"]
        if not soc or soc.lower() == "nan":
            continue
        ticker = str(row["Ticker"]).strip()
        indic = row["TypeValeur"]
        est_flux = indic in INDICATEURS_FLUX

        for annee in annees:
            vals = {t: _to_float(row.get(f"{annee}_{t}")) for t in TRIMESTRES}
            for t in TRIMESTRES:
                if vals[t] is not None:
                    lignes.append([soc, ticker, indic, annee, t, vals[t], "Trimestriel"])
            for per, val, type_per in _periodes_depuis_trimestres(vals, est_flux):
                lignes.append([soc, ticker, indic, annee, per, val, type_per])

    # --- Ajout du Résultat Net (RN) lu depuis Semestriel + Annuel ---
    lignes.extend(_lire_lignes_rn(excel_path))

    out = pd.DataFrame(
        lignes,
        columns=["Société", "Ticker", "TypeValeur", "Année", "Période", "Valeur", "TypePériode"],
    )
    out["Secteur"] = out["Société"].map(secteurs)
    return out


def get_data_quality_report(df: pd.DataFrame) -> dict:
    """Produit un rapport de qualité des données pour la sidebar.

    Args:
        df: DataFrame retourné par :func:`load_data`.

    Returns:
        Dictionnaire récapitulant le périmètre et les anomalies détectées.
    """
    nb_lignes_par_soc = df.groupby("Société").size()
    couverture_faible = sorted(
        [
            (soc, int(n))
            for soc, n in nb_lignes_par_soc.items()
            if n < SEUIL_COUVERTURE_FAIBLE
        ],
        key=lambda x: x[1],
    )
    sans_secteur = sorted(df[df["Secteur"].isna()]["Société"].unique().tolist())
    indicateurs_par_societe = {
        soc: sorted(sous_df["TypeValeur"].unique().tolist())
        for soc, sous_df in df.groupby("Société")
    }
    return {
        "nb_societes": int(df["Société"].nunique()),
        "nb_secteurs": int(df["Secteur"].nunique()),
        "nb_lignes": int(len(df)),
        "annees": sorted(df["Année"].unique().tolist()),
        "societes_sans_secteur": sans_secteur,
        "societes_couverture_faible": couverture_faible,
        "indicateurs_par_societe": indicateurs_par_societe,
    }