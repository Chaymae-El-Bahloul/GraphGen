import io

import pandas as pd
import pytest

import helpers as h
from app import create_app

CSV = b"mois,ventes,region\njan,10,N\nfev,20,S\nmar,30,N\n"


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "UPLOAD_FOLDER": tmp_path})
    return app.test_client()


def upload(client, name, data):
    return client.post("/upload", data={"file": (io.BytesIO(data), name)},
                       content_type="multipart/form-data")


def test_index(client):
    assert client.get("/").status_code == 200


def test_rejects_bad_extension(client):
    r = upload(client, "virus.exe", b"x")
    assert r.status_code == 302 and "/preview/" not in r.headers["Location"]


def test_upload_preview_and_chart(client):
    r = upload(client, "data.csv", CSV)
    assert "/preview/" in r.headers["Location"]
    page = client.get(r.headers["Location"])
    assert b"ventes" in page.data
    file_id = r.headers["Location"].split("/preview/")[1].split("?")[0]
    q = f"/chart?file_id={file_id}&kind=bar&x=region&y=ventes&agg=sum"
    assert b"plotly" in client.get(q).data
    assert client.get(q + "&download=1").headers["Content-Disposition"].startswith("attachment")


def test_invalid_file_id_is_404(client):
    assert client.get("/preview/../../etc/passwd").status_code == 404
    assert client.get("/chart?file_id=nope").status_code == 404


def test_chart_error_redirects(client):
    r = upload(client, "data.csv", CSV)
    file_id = r.headers["Location"].split("/preview/")[1].split("?")[0]
    r = client.get(f"/chart?file_id={file_id}&kind=line&x=mois")  # Y manquant
    assert r.status_code == 302


def test_excel_header_detection(tmp_path):
    path = tmp_path / "t.xlsx"
    rows = [["TITRE", None, None], [None, None, None], ["a", "b", "c"], [1, 2, 3], [4, 5, 6]]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)
    df, header = h.load_df(path)
    assert header == 2 and list(df.columns) == ["a", "b", "c"] and len(df) == 2


def test_all_chart_types():
    df = pd.read_csv(io.BytesIO(CSV))
    for kind in h.CHART_TYPES:
        assert h.build_chart(df, kind, "region", "ventes", None, "sum") is not None


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_security_headers(client):
    assert client.get("/").headers["X-Frame-Options"] == "DENY"


def test_demo_flow(client):
    r = client.get("/demo")
    assert "/preview/" in r.headers["Location"]
    page = client.get(r.headers["Location"])
    assert b"Profil des colonnes" in page.data and b"Corr" in page.data


def test_profile_and_palette():
    df = pd.read_csv(io.BytesIO(CSV))
    prof = {p["name"]: p for p in h.profile(df)}
    assert prof["ventes"]["numeric"] and not prof["region"]["numeric"]
    fig = h.build_chart(df, "bar", "region", "ventes", None, "sum", "Mon titre", "Pastel")
    assert fig.layout.title.text == "Mon titre"


def test_purge_old(tmp_path):
    import os
    f = tmp_path / ("a" * 32 + ".csv")
    f.write_text("x")
    os.utime(f, (0, 0))
    assert h.purge_old(tmp_path, 1) == 1 and not f.exists()
