"""GraphGen - generateur de graphiques interactifs a partir de CSV / Excel."""
import logging
import os
import shutil
from pathlib import Path

from flask import Flask, Response, abort, flash, redirect, render_template, request, url_for

import helpers as h

BASE_DIR = Path(__file__).parent


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        UPLOAD_FOLDER=BASE_DIR / "uploads",
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10 Mo
        UPLOAD_TTL_HOURS=float(os.environ.get("UPLOAD_TTL_HOURS", 24)),
    )
    if test_config:
        app.config.update(test_config)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    folder = Path(app.config["UPLOAD_FOLDER"])
    folder.mkdir(parents=True, exist_ok=True)
    if app.config["SECRET_KEY"] == "dev-only-change-me" and not app.testing:
        app.logger.warning("SECRET_KEY par défaut: définissez-la en production.")
    purged = h.purge_old(folder, app.config["UPLOAD_TTL_HOURS"])
    app.logger.info("Fichiers purgés au démarrage: %d", purged)

    def load(file_id, args):
        """Valide l'identifiant puis charge le fichier correspondant."""
        if not h.is_valid_file_id(file_id):
            abort(404)
        path = folder / file_id
        if not path.exists():
            abort(404)
        sheets, sheet = [], None
        if path.suffix == ".xlsx":
            sheets = h.sheet_names(path)
            sheet = args.get("sheet") if args.get("sheet") in sheets else sheets[0]
        df, header = h.load_df(path, sheet, args.get("header", type=int))
        return df, sheets, sheet, header

    @app.after_request
    def security_headers(resp):
        resp.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "same-origin",
        })
        return resp

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/")
    def index():
        return render_template("index.html", step=1)

    @app.get("/demo")
    def demo():
        file_id = h.new_file_id("demo.csv")
        shutil.copy(BASE_DIR / "sample_data" / "ventes_demo.csv", folder / file_id)
        return redirect(url_for("preview", file_id=file_id))

    @app.post("/upload")
    def upload():
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Aucun fichier sélectionné.", "error")
            return redirect(url_for("index"))
        if not h.is_allowed(file.filename):
            flash("Format non supporté. Utilisez un fichier .csv ou .xlsx.", "error")
            return redirect(url_for("index"))
        file_id = h.new_file_id(file.filename)
        path = folder / file_id
        file.save(path)
        try:
            h.load_df(path, sheet=h.sheet_names(path)[0] if path.suffix == ".xlsx" else None)
        except Exception as exc:
            path.unlink(missing_ok=True)
            app.logger.warning("Import refusé: %s", exc)
            flash(f"Fichier illisible: {exc}", "error")
            return redirect(url_for("index"))
        app.logger.info("Import réussi: %s", file_id)
        return redirect(url_for("preview", file_id=file_id))

    @app.get("/preview/<file_id>")
    def preview(file_id):
        try:
            df, sheets, sheet, header = load(file_id, request.args)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))
        numeric = list(df.select_dtypes("number").columns)
        corr = h.correlation_fig(df)
        total = df.size
        kpis = {
            "rows": len(df), "cols": df.shape[1], "numeric": len(numeric),
            "missing_pct": round(100 * df.isna().sum().sum() / total, 1) if total else 0,
            "duplicates": int(df.duplicated().sum()),
        }
        return render_template(
            "preview.html", step=2, file_id=file_id, sheets=sheets, sheet=sheet, header=header,
            table=df.head(10).to_html(classes="data", border=0, index=False),
            cols=list(df.columns), numeric=numeric or list(df.columns), kpis=kpis,
            profile=h.profile(df), corr=h.fig_to_html(corr) if corr else None,
            chart_types=h.CHART_TYPES, aggregations=h.AGGREGATIONS, palettes=list(h.PALETTES),
        )

    @app.get("/chart")
    def chart():
        file_id = request.args.get("file_id", "")
        df, _, sheet, header = load(file_id, request.args)
        params = {k: v for k, v in request.args.items() if k != "download"}
        try:
            fig = h.build_chart(
                df, request.args.get("kind", "line"), request.args.get("x"),
                request.args.get("y"), request.args.get("color"),
                request.args.get("agg", "none"), request.args.get("title"),
                request.args.get("palette", "Indigo"),
            )
        except Exception as exc:
            flash(f"Impossible de créer ce graphique: {exc}", "error")
            return redirect(url_for("preview", file_id=file_id, sheet=sheet, header=header))
        if request.args.get("download"):
            return Response(h.fig_to_html(fig, full=True), mimetype="text/html",
                            headers={"Content-Disposition": "attachment; filename=graphique.html"})
        return render_template(
            "chart.html", step=3, chart=h.fig_to_html(fig),
            back_url=url_for("preview", file_id=file_id, sheet=sheet, header=header),
            download_url=url_for("chart", **params, download=1),
        )

    @app.errorhandler(413)
    def too_large(_):
        flash("Fichier trop volumineux (maximum 10 Mo).", "error")
        return redirect(url_for("index"))

    @app.errorhandler(404)
    def not_found(_):
        return render_template("index.html", step=1, not_found=True), 404

    return app


if __name__ == "__main__":
    create_app().run(debug=os.environ.get("FLASK_DEBUG") == "1")
