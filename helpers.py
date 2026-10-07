"""Chargement des donnees, analyse et construction des graphiques (independant de Flask)."""
import re
import time
import uuid
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio

ALLOWED_EXTENSIONS = {"csv", "xlsx"}
FILE_ID_RE = re.compile(r"^[0-9a-f]{32}\.(csv|xlsx)$")

CHART_TYPES = {
    "line": "Ligne", "bar": "Barres", "scatter": "Nuage de points",
    "histogram": "Histogramme", "box": "Boîte à moustaches", "pie": "Camembert",
}
AGGREGATIONS = {
    "none": "Aucune", "sum": "Somme", "mean": "Moyenne",
    "count": "Nombre de lignes", "max": "Maximum", "min": "Minimum",
}
PALETTES = {
    "Indigo": px.colors.qualitative.Plotly, "Pastel": px.colors.qualitative.Pastel,
    "Vif": px.colors.qualitative.Bold, "Doux": px.colors.qualitative.Set2,
    "Sobre": px.colors.qualitative.D3,
}


def is_allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def new_file_id(filename: str) -> str:
    """Identifiant aleatoire: le nom d'origine n'est jamais utilise sur le disque."""
    return f"{uuid.uuid4().hex}.{filename.rsplit('.', 1)[1].lower()}"


def is_valid_file_id(file_id: str) -> bool:
    return bool(FILE_ID_RE.match(file_id or ""))


def purge_old(folder: Path, hours: float) -> int:
    """Supprime les fichiers importes plus anciens que `hours` (confidentialite)."""
    limit, removed = time.time() - hours * 3600, 0
    for f in Path(folder).iterdir():
        if is_valid_file_id(f.name) and f.stat().st_mtime < limit:
            f.unlink(missing_ok=True)
            removed += 1
    return removed


def sheet_names(path) -> list:
    return pd.ExcelFile(path).sheet_names


def guess_header_row(raw: pd.DataFrame) -> int:
    """Premiere ligne dont le nombre de cellules remplies est proche du maximum."""
    counts = raw.notna().sum(axis=1)
    if counts.empty or counts.max() == 0:
        return 0
    return int((counts >= 0.8 * counts.max()).idxmax())


def load_df(path, sheet=None, header=None):
    """Retourne (DataFrame nettoye, ligne d'en-tete utilisee)."""
    path = Path(path)
    if path.suffix == ".csv":
        try:
            df = pd.read_csv(path, sep=None, engine="python")
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=None, engine="python", encoding="latin-1")
        header = 0
    else:
        sheet = sheet if sheet is not None else 0
        if header is None:
            raw = pd.read_excel(path, sheet_name=sheet, header=None, nrows=30)
            header = guess_header_row(raw)
        df = pd.read_excel(path, sheet_name=sheet, header=header)
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c) for c in df.columns]
    if df.empty:
        raise ValueError("Aucune donnée exploitable dans ce fichier.")
    return df, header


def profile(df: pd.DataFrame) -> list:
    """Resume par colonne: type, valeurs manquantes, valeurs uniques, statistiques."""
    out = []
    for col in df.columns:
        s = df[col]
        numeric = pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
        if numeric and s.notna().any():
            summary = f"{s.min():.4g} → {s.max():.4g} · moy. {s.mean():.4g}"
        else:
            mode = s.mode()
            summary = f"fréquent: {mode.iloc[0]}" if not mode.empty else "—"
        out.append({
            "name": col, "numeric": numeric, "unique": int(s.nunique()),
            "missing": int(s.isna().sum()), "missing_pct": round(100 * s.isna().mean(), 1),
            "summary": summary,
        })
    return out


def correlation_fig(df: pd.DataFrame):
    """Heatmap des correlations (None s'il y a moins de 2 colonnes numeriques)."""
    num = df.select_dtypes("number").iloc[:, :15]
    if num.shape[1] < 2:
        return None
    fig = px.imshow(num.corr(), text_auto=".2f", zmin=-1, zmax=1,
                    color_continuous_scale="RdBu_r", aspect="auto")
    fig.update_layout(template="plotly_white", height=460, margin=dict(l=10, r=10, t=20, b=10))
    return fig


def build_chart(df, kind, x, y=None, color=None, agg="none", title=None, palette="Indigo"):
    if kind not in CHART_TYPES:
        raise ValueError("Type de graphique inconnu.")
    x, y, color = x or None, y or None, color or None
    for col in (x, y, color):
        if col and col not in df.columns:
            raise ValueError(f"Colonne introuvable: {col}")
    if not x:
        raise ValueError("Choisissez une colonne X.")
    seq = PALETTES.get(palette, PALETTES["Indigo"])
    style = {"color_discrete_sequence": seq}

    if kind == "histogram":
        fig = px.histogram(df, x=x, color=color, **style)
        auto_title = f"Distribution de {x}"
    elif kind == "box":
        fig = px.box(df, x=x if y else None, y=y or x, color=color, **style)
        auto_title = f"Dispersion de {y or x}"
    else:
        if agg != "none":
            keys = [x] + ([color] if color and color != x else [])
            if agg == "count":
                df = df.groupby(keys, dropna=False).size().reset_index(name="nombre")
                y = "nombre"
            else:
                if not y:
                    raise ValueError("Choisissez une colonne Y pour cette agrégation.")
                df = df.groupby(keys, dropna=False)[y].agg(agg).reset_index()
        if not y:
            raise ValueError("Choisissez une colonne Y.")
        auto_title = f"{y} par {x}"
        if kind == "pie":
            fig = px.pie(df, names=x, values=y, **style)
        else:
            df = df.sort_values(x)
            plot = {"line": px.line, "bar": px.bar, "scatter": px.scatter}[kind]
            fig = plot(df, x=x, y=y, color=color, **style)
    fig.update_layout(template="plotly_white", title=(title or auto_title),
                      margin=dict(l=20, r=20, t=60, b=20), font=dict(family="system-ui"))
    return fig


def fig_to_html(fig, full=False) -> str:
    return pio.to_html(fig, full_html=full, include_plotlyjs="cdn")
