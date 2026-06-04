"""
data_loader.py — Chargement des données BVC depuis la feuille « Trims ».

La feuille « Trims » (format large, données trimestrielles) est l'UNIQUE
source de vérité. En ligne, elle est lue depuis Google Sheets ; en local
(hors ligne), depuis le fichier Excel. Les périodes semestrielles et
annuelles sont calculées selon la nature comptable de chaque indicateur :

    - FLUX  (CA, Capex)      : additif      -> S1=T1+T2, S2=T3+T4, Annuel=ΣT
    - STOCK (Endettement)    : non additif  -> S1=T2,   S2=T4,   Annuel=T4

Une période n'est calculée que si TOUS les trimestres nécessaires sont
présents. Sinon elle est omise (affichée « N/A » côté interface) : on ne
remplace jamais une donnée manquante par 0.
"""
from __future__ import annotations

import math
from urllib.parse import quote

import pandas as pd

from config import EXCEL_PATH, GSHEET_ID, GSHEET_TRIMS_TAB, SHEET_TRIMS

# --- Nature comptable des indicateurs ---
INDICATEURS_FLUX = {"CA", "Capex"}        # additifs sur la période
INDICATEURS_STOCK = {"Endettement"}        # valeur de fin de période

TRIMESTRES = ["T1", "T2", "T3", "T4"]

# En dessous de ce nombre de lignes, une société est jugée « peu couverte »
SEUIL_COUVERTURE_FAIBLE = 20


def _read_trims_raw(excel_path: str | None = None) -> pd.DataFrame:
    """Lit l'onglet Trims brut (format large), depuis Google Sheets ou Excel.

    - Si ``config.GSHEET_ID`` est renseigné : lecture du Google Sheet en ligne
      (onglet ``config.GSHEET_TRIMS_TAB``) via son export CSV public. Le Sheet
      doit être partagé « Tout utilisateur disposant du lien : Lecteur ».
      ``headers=1`` force la 1re ligne comme en-tête (sinon Google ne détecte
      pas l'en-tête quand la 1re colonne est du texte).
    - Sinon : lecture du fichier Excel local (développement hors ligne).

    Args:
        excel_path: Chemin Excel (utilisé uniquement si GSHEET_ID est vide).

    Returns:
        DataFrame brut de l'onglet Trims (en-têtes en première ligne).
    """
    if GSHEET_ID:
        url = (
            f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}"
            f"/gviz/tq?tqx=out:csv&headers=1&sheet={quote(GSHEET_TRIMS_TAB)}"
        )
        return pd.read_csv(url)
    chemin = excel_path if excel_path is not None else EXCEL_PATH
    return pd.read_excel(chemin, sheet_name=SHEET_TRIMS, header=0)


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


def load_data(excel_path: str | None = None) -> pd.DataFrame:
    """Charge la feuille Trims et reconstruit un tableau long exploitable.

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