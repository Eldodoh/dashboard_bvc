"""Fonctions de visualisation Plotly pour le dashboard BVC.

Chaque fonction prend un DataFrame et retourne une go.Figure avec
la charte graphique Wafa Gestion appliquée.

Conventions :
- Orange #F39200 -> élément mis en avant uniquement
- Hovers en français avec unités (MMAD, %)
- Exports PNG via la modebar native Plotly (sans kaleido)
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from calculations import (
    compute_yoy,
    format_mmad,
    format_pct,
    get_company_series,
    get_market_share,
    get_sector_aggregate,
    get_yoy_by_company,
)
from config import (
    COLOR_GRAY_LIGHT,
    COLOR_GRAY_MEDIUM,
    COLOR_NEGATIVE,
    COLOR_ORANGE,
    COLOR_POSITIVE,
    COLOR_WHITE,
    COLOR_BLACK,
    FONT_FAMILY,
    PALETTE_NEUTRAL,
    PALETTE_SECTORS,
    PERIODES_TRIMESTRIELLES,
    PERIODES_SEMESTRIELLES,
    PERIODE_ANNUELLE,
    INDICATEUR_CA,
    PALETTE_ANNEES,
)


# =============================================================================
# LAYOUT COMMUN
# =============================================================================

def _wafa_layout(fig, title="", height=450):
    """Applique le thème Wafa Gestion à une figure Plotly."""
    fig.update_layout(
        title={"text": title, "font": {"color": COLOR_BLACK, "size": 14}, "x": 0.01},
        font={"family": FONT_FAMILY, "color": COLOR_BLACK},
        paper_bgcolor=COLOR_WHITE,
        plot_bgcolor=COLOR_GRAY_LIGHT,
        height=height,
        legend={"orientation": "h", "y": -0.2, "x": 0},
        margin={"t": 55, "b": 10, "l": 10, "r": 10},
        hoverlabel={"bgcolor": COLOR_WHITE, "font_family": FONT_FAMILY},
    )
    fig.update_xaxes(gridcolor="#E5E7EB", zeroline=False)
    fig.update_yaxes(gridcolor="#E5E7EB", zeroline=False)
    return fig


def _empty_figure(message):
    """Retourne une figure vide avec un message d'information."""
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font={"size": 13, "color": COLOR_GRAY_MEDIUM},
    )
    return _wafa_layout(fig)


# =============================================================================
# PAGE 1 — VUE D ENSEMBLE
# =============================================================================

def plot_treemap_companies(df, year):
    """Treemap des sociétés pondéré par CA, coloré par secteur."""
    data = df.loc[
        (df["TypeValeur"] == INDICATEUR_CA)
        & (df["TypePériode"] == "Annuel")
        & (df["Année"] == year)
    ].dropna(subset=["Valeur"])
    data = data[data["Valeur"] > 0].copy()

    if data.empty:
        return _empty_figure(f"Aucune donnée CA disponible pour {year}")

    data["Valeur_fmt"] = data["Valeur"].apply(format_mmad)
    secteurs = sorted(data["Secteur"].dropna().unique())
    color_map = {s: PALETTE_SECTORS[i % len(PALETTE_SECTORS)] for i, s in enumerate(secteurs)}

    fig = px.treemap(
        data,
        path=["Secteur", "Société"],
        values="Valeur",
        color="Secteur",
        color_discrete_map=color_map,
        custom_data=["Valeur_fmt"],
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>CA : %{customdata[0]}<br><extra></extra>",
        textinfo="label+percent root",
    )
    return _wafa_layout(fig, title=f"Répartition du CA par société — {year}", height=500)


def plot_top_flop_yoy(df, year, indicator=INDICATEUR_CA, top=True, n=10):
    """Barres horizontales Top/Flop N sociétés par variation YoY."""
    yoy_df = get_yoy_by_company(df, indicator, year)
    numeriques = yoy_df[
        yoy_df["YoY"].apply(lambda x: isinstance(x, (int, float)))
    ].copy()

    if numeriques.empty:
        rang = "Top" if top else "Flop"
        return _empty_figure(f"Données insuffisantes pour {rang} {n} ({year})")

    numeriques = numeriques.sort_values("YoY", ascending=not top).head(n)
    numeriques = numeriques.sort_values("YoY", ascending=top)
    color = "#22C55E" if top else "#EF4444"
    rang = "Top" if top else "Flop"
    label = "hausse" if top else "baisse"

    fig = go.Figure(go.Bar(
        x=numeriques["YoY"],
        y=numeriques["Société"],
        orientation="h",
        marker_color=color,
        customdata=numeriques[["Valeur_N_fmt", "YoY_fmt", "Secteur"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>Secteur : %{customdata[2]}<br>"
            f"{indicator} {year} : %{{customdata[0]}}<br>"
            "Variation YoY : %{customdata[1]}<br><extra></extra>"
        ),
        text=numeriques["YoY_fmt"],
        textposition="outside",
    ))
    titre = f"{rang} {n} — Plus fortes {label}s ({indicator} {year} vs {year-1})"
    _wafa_layout(fig, title=titre, height=max(300, n * 42))
    _wafa_layout(fig, title=titre, height=max(300, n * 42))
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode="hide")
    max_abs = numeriques["YoY"].abs().max()
    if top:
        fig.update_xaxes(range=[0, max_abs * 1.5], title_text="Variation YoY (%)")
    else:
        fig.update_xaxes(range=[max_abs * -1.5, 0], title_text="Variation YoY (%)")
    return fig


# =============================================================================
# PAGE 2 — ANALYSE SOCIÉTÉ
# =============================================================================

def plot_evolution_line(df, societe, indicator, granularity, show_pct_axis=False):
    """Courbe d'évolution temporelle d'une société."""
    series = get_company_series(df, societe, indicator, granularity).dropna(subset=["Valeur"])
    if series.empty:
        return _empty_figure(f"Aucune donnée {indicator} ({granularity}) pour {societe}")

    series["Label"] = series["Période"].astype(str) + " " + series["Année"].astype(str)
    vals = series["Valeur"].tolist()
    pop = [None] + [compute_yoy(vals[i], vals[i-1]) for i in range(1, len(vals))]
    series["PoPfmt"] = [format_pct(p) for p in pop]
    series["Valeur_fmt"] = series["Valeur"].apply(format_mmad)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=series["Label"], y=series["Valeur"],
        name=indicator,
        marker_color=COLOR_ORANGE,
        customdata=series[["Valeur_fmt", "PoPfmt"]].values,
        hovertemplate=(
            "<b>%{x}</b><br>"
            f"{indicator} : %{{customdata[0]}}<br>"
            "Var. p/p : %{customdata[1]}<br><extra></extra>"
        ),
    ))

    if show_pct_axis:
        pop_num = [p if isinstance(p, (int, float)) else None for p in pop]
        fig.add_trace(go.Scatter(
            x=series["Label"], y=pop_num,
            mode="lines+markers", name="Var. % (éch. droite)",
            line={"color": PALETTE_NEUTRAL[0], "width": 1.5, "dash": "dot"},
            marker={"color": PALETTE_NEUTRAL[0], "size": 5},
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Var. : %{y:.1f} %<extra></extra>",
        ))
        fig.update_layout(yaxis2={
            "title": "Variation % (p/p)", "overlaying": "y",
            "side": "right", "showgrid": False,
        })

    _wafa_layout(fig, title=f"{societe} — Évolution {indicator} ({granularity})")
    fig.update_xaxes(title_text="Période")
    fig.update_yaxes(title_text=f"{indicator} (MMAD)")
    return fig


def plot_yoy_bars(df, societe, indicator, period_type):
    """Barres comparatives YoY : groupes = périodes, barres = années."""
    mask = (
        (df["Société"] == societe)
        & (df["TypeValeur"] == indicator)
        & (df["TypePériode"] == period_type)
    )
    data = df.loc[mask].dropna(subset=["Valeur"])
    if data.empty:
        return _empty_figure(f"Aucune donnée {indicator} ({period_type}) pour {societe}")

    if period_type == "Trimestriel":
        periodes = PERIODES_TRIMESTRIELLES
    elif period_type == "Semestriel":
        periodes = PERIODES_SEMESTRIELLES
    else:
        periodes = [PERIODE_ANNUELLE]

    annees = sorted(data["Année"].unique())
    couleurs = [PALETTE_ANNEES[i % len(PALETTE_ANNEES)] for i in range(len(annees))]

    fig = go.Figure()
    for i, annee in enumerate(annees):
        d = data.loc[data["Année"] == annee].copy()
        d["Période"] = pd.Categorical(d["Période"], categories=periodes, ordered=True)
        d = d.sort_values("Période")

        if i > 0:
            d_prev = data.loc[data["Année"] == annees[i-1]]
            yoy_map = {}
            for _, row in d.iterrows():
                prev = d_prev.loc[d_prev["Période"] == row["Période"], "Valeur"]
                yoy_map[str(row["Période"])] = compute_yoy(
                    row["Valeur"], float(prev.iloc[0]) if not prev.empty else None
                )
            d["YoY_fmt"] = d["Période"].astype(str).map(yoy_map).apply(format_pct)
        else:
            d["YoY_fmt"] = "—"

        d["Valeur_fmt"] = d["Valeur"].apply(format_mmad)
        is_last = (i == len(annees) - 1)

        fig.add_trace(go.Bar(
            x=d["Période"].astype(str), y=d["Valeur"],
            name=str(annee), marker_color=couleurs[i],
            customdata=d[["Valeur_fmt", "YoY_fmt"]].values,
            hovertemplate=(
                f"<b>{annee} — %{{x}}</b><br>"
                f"{indicator} : %{{customdata[0]}}<br>"
                "YoY : %{customdata[1]}<br><extra></extra>"
            ),
            text=d["YoY_fmt"] if is_last else None,
            textposition="outside" if is_last else "none",
        ))

    fig.update_layout(barmode="group")
    _wafa_layout(fig, title=f"{societe} — {indicator} par période ({period_type})")
    fig.update_xaxes(title_text="Période")
    fig.update_yaxes(title_text=f"{indicator} (MMAD)")
    return fig


# =============================================================================
# PAGE 3 — ANALYSE SECTORIELLE
# =============================================================================

def plot_sector_aggregate(df, sector, indicator):
    """Courbe d'évolution du total agrégé d'un secteur (annuel)."""
    agg = get_sector_aggregate(df, sector, indicator, granularity="Annuel")
    if agg.empty:
        return _empty_figure(f"Aucune donnée {indicator} pour {sector}")

    agg["Valeur_fmt"] = agg["Total"].apply(format_mmad)
    fig = go.Figure(go.Scatter(
        x=agg["Année"].astype(str), y=agg["Total"],
        mode="lines+markers",
        line={"color": COLOR_ORANGE, "width": 2.5},
        marker={"color": COLOR_ORANGE, "size": 8},
        customdata=[[v] for v in agg["Valeur_fmt"]],
        hovertemplate=(
            "<b>%{x}</b><br>"
            f"Total {indicator} : %{{customdata[0]}}<br><extra></extra>"
        ),
    ))
    _wafa_layout(fig, title=f"{sector} — Évolution {indicator} agrégé")
    fig.update_xaxes(title_text="Année")
    fig.update_yaxes(title_text=f"{indicator} (MMAD)")
    return fig


def plot_companies_overlay(df, societes, indicator, granularity):
    """Courbes superposées pour une liste de sociétés."""
    if not societes:
        return _empty_figure("Aucune société sélectionnée")

    couleurs = [COLOR_ORANGE] + PALETTE_NEUTRAL * 4
    fig = go.Figure()
    for i, soc in enumerate(societes):
        series = get_company_series(df, soc, indicator, granularity).dropna(subset=["Valeur"])
        if series.empty:
            continue
        series["Label"] = series["Période"].astype(str) + " " + series["Année"].astype(str)
        series["Valeur_fmt"] = series["Valeur"].apply(format_mmad)
        fig.add_trace(go.Scatter(
            x=series["Label"], y=series["Valeur"],
            mode="lines+markers", name=soc,
            line={"color": couleurs[i % len(couleurs)], "width": 2},
            marker={"size": 6},
            customdata=[[v] for v in series["Valeur_fmt"]],
            hovertemplate=(
                f"<b>{soc} — %{{x}}</b><br>"
                f"{indicator} : %{{customdata[0]}}<br><extra></extra>"
            ),
        ))

    _wafa_layout(fig, title=f"Comparaison {indicator} ({granularity})", height=500)
    fig.update_xaxes(title_text="Période")
    fig.update_yaxes(title_text=f"{indicator} (MMAD)")
    return fig


def plot_market_share(df, sector, year, indicator=INDICATEUR_CA, mode="pie"):
    """Parts de marché relatives dans un secteur (pie ou barres)."""
    parts = get_market_share(df, sector, year, indicator)
    if parts.empty:
        return _empty_figure(f"Pas de données {indicator} pour {sector} en {year}")

    parts["Part_fmt"] = parts["Part_pct"].apply(lambda x: f"{x:.1f} %" if x else "N/A")
    parts["Valeur_fmt"] = parts["Valeur"].apply(format_mmad)
    couleurs = [PALETTE_SECTORS[i % len(PALETTE_SECTORS)] for i in range(len(parts))]
    titre = f"Parts de marché {indicator} — {sector} ({year})"

    if mode == "pie":
        fig = go.Figure(go.Pie(
            labels=parts["Société"], values=parts["Part_pct"],
            marker={"colors": couleurs},
            customdata=[[v] for v in parts["Valeur_fmt"]],

            hovertemplate=(
                "<b>%{label}</b><br>Part : %{percent}<br>"
                f"{indicator} : %{{customdata[0]}}<br><extra></extra>"
            ),
            textinfo="label+percent",
        ))
        return _wafa_layout(fig, title=titre)
    else:
        ps = parts.sort_values("Part_pct", ascending=True)
        bar_colors = [
            COLOR_ORANGE if i == len(ps) - 1 else PALETTE_NEUTRAL[0]
            for i in range(len(ps))
        ]
        fig = go.Figure(go.Bar(
            x=ps["Part_pct"], y=ps["Société"], orientation="h",
            marker_color=bar_colors,
            customdata=ps[["Valeur_fmt", "Part_fmt"]].values,
            hovertemplate=(
                "<b>%{y}</b><br>Part : %{customdata[1]}<br>"
                f"{indicator} : %{{customdata[0]}}<br><extra></extra>"
            ),
            text=ps["Part_fmt"], textposition="outside",
        ))
        _wafa_layout(fig, title=titre, height=max(300, len(parts) * 45))
        fig.update_xaxes(title_text="Part de marché (%)")
        return fig
# =============================================================================
# CA agrégé trimestriel — graphique de comparaison (Vue d'Ensemble)
# =============================================================================
from config import ANNEE_DEBUT, COLOR_GRAY_LIGHT, COLOR_GRAY_MEDIUM, FONT_FAMILY, PALETTE_ANNEES


def plot_ca_trimestriel_compare(table, indicator="CA"):
    """Barres groupées du CA agrégé trimestriel par année (YoY au survol)."""
    fig = go.Figure()
    if table.empty or table["Total"].isna().all():
        fig.add_annotation(text="Données insuffisantes pour la sélection",
                           showarrow=False, font={"size": 15, "color": COLOR_GRAY_MEDIUM})
        fig.update_layout(plot_bgcolor=COLOR_GRAY_LIGHT, paper_bgcolor="white",
                          font={"family": FONT_FAMILY}, height=420)
        return fig

    for annee in sorted(table["Année"].unique()):
        sub = table[table["Année"] == annee].dropna(subset=["Total"])
        if sub.empty:
            continue
        couleur = PALETTE_ANNEES[(int(annee) - ANNEE_DEBUT) % len(PALETTE_ANNEES)]
        fig.add_trace(go.Bar(
            x=sub["Trimestre"], y=sub["Total"], name=str(int(annee)),
            marker_color=couleur,
            customdata=[[t, y] for t, y in zip(sub["Total_fmt"], sub["YoY_fmt"])],
            hovertemplate=("<b>%{x} " + str(int(annee)) + "</b><br>"
                           + f"Total {indicator} : " + "%{customdata[0]}<br>"
                           + "YoY vs N-1 : %{customdata[1]}<extra></extra>"),
        ))

    fig.update_layout(
        barmode="group", plot_bgcolor=COLOR_GRAY_LIGHT, paper_bgcolor="white",
        font={"family": FONT_FAMILY, "color": "#1A1A1A"},
        height=420, legend_title_text="Année",
        margin={"t": 30, "b": 40, "l": 60, "r": 20},
    )
    fig.update_xaxes(title_text="Trimestre")
    fig.update_yaxes(title_text=f"{indicator} agrégé (MMAD)")
    return fig