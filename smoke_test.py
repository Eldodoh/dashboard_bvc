"""Smoke test de la Vague 1.

Lance le chargement et imprime un rapport de validation à l'écran.
À exécuter une seule fois pour vérifier que tout marche :

    python smoke_test.py

Critères de succès attendus :
- 41 sociétés
- 18 secteurs
- Période 2022 → 2025
- 0 société sans secteur
- Cash Plus signalée comme à couverture faible
"""
from __future__ import annotations

import sys

from config import EXCEL_PATH
from data_loader import get_data_quality_report, load_data


def main() -> int:
    print("=" * 64)
    print("  SMOKE TEST — Dashboard BVC, Vague 1")
    print("=" * 64)
    print(f"Fichier Excel attendu : {EXCEL_PATH}")
    print()

    if not EXCEL_PATH.exists():
        print(f"[ECHEC] Fichier Excel introuvable.")
        print(f"        Place le fichier ici : {EXCEL_PATH}")
        return 1

    try:
        df = load_data()
    except Exception as e:  # noqa: BLE001 — on veut tout attraper ici
        print(f"[ECHEC] Erreur de chargement : {type(e).__name__}: {e}")
        return 1

    print(f"[OK] Chargement reussi : {len(df)} lignes")
    print()

    report = get_data_quality_report(df)

    print("-" * 64)
    print("  CHIFFRES CLES")
    print("-" * 64)
    print(f"  Nombre de societes  : {report['nb_societes']}")
    print(f"  Nombre de secteurs  : {report['nb_secteurs']}")
    print(f"  Periode couverte    : {min(report['annees'])} -> {max(report['annees'])}")
    print(f"  Total lignes        : {report['nb_lignes']}")
    print()

    # Validation des attendus.
    print("-" * 64)
    print("  VALIDATION")
    print("-" * 64)
    attendus = {
        "41 societes": report["nb_societes"] == 41,
        "18 secteurs": report["nb_secteurs"] == 18,
        "Periode 2022-2025": report["annees"] == [2022, 2023, 2024, 2025],
        "Aucune societe sans secteur": len(report["societes_sans_secteur"]) == 0,
    }
    for libelle, ok in attendus.items():
        statut = "[OK]" if ok else "[ECHEC]"
        print(f"  {statut} {libelle}")
    print()

    # Sociétés à couverture faible (signalement attendu : Cash Plus).
    if report["societes_couverture_faible"]:
        print("-" * 64)
        print("  SOCIETES A COUVERTURE INCOMPLETE (a signaler dans le dashboard)")
        print("-" * 64)
        for soc, n in sorted(
            report["societes_couverture_faible"], key=lambda x: x[1]
        ):
            print(f"  - {soc:35s} ({n} lignes)")
        print()

    # Cas Cash Plus : vérifier que S1 2025 = NA après nettoyage.
    print("-" * 64)
    print("  VERIFICATION ANOMALIE CASH PLUS")
    print("-" * 64)
    cp = df[df["Société"] == "Cash Plus"][
        ["Société", "Ticker", "TypeValeur", "Année", "Période", "Valeur", "Secteur"]
    ]
    print(cp.to_string(index=False))
    print()

    # Échantillon : indicateurs disponibles par société.
    print("-" * 64)
    print("  INDICATEURS DISPONIBLES (echantillon de 5 societes)")
    print("-" * 64)
    indicateurs = report["indicateurs_par_societe"]
    for soc in sorted(indicateurs)[:5]:
        print(f"  {soc:35s} -> {indicateurs[soc]}")
    print(f"  ... ({len(indicateurs) - 5} autres societes)")
    print()

    print("=" * 64)
    tous_ok = all(attendus.values())
    if tous_ok:
        print("  RESULTAT : SMOKE TEST OK. Vague 1 prete.")
    else:
        print("  RESULTAT : Au moins une verification a echoue. Voir ci-dessus.")
    print("=" * 64)

    return 0 if tous_ok else 1


if __name__ == "__main__":
    sys.exit(main())
    