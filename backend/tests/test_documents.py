"""My documents: encrypted ID storage that only the owner can open."""
from datetime import date, timedelta

from app.core.config import settings
from app.services import document_vault as vault
from tests.helpers import OTHER, signup
from tests.test_business import _admin

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
PDF = b"%PDF-1.4\n" + b"x" * 300


def aadhaar(prefix: str = "23456789012") -> str:
    """A number with a valid Verhoeff check digit."""
    for d in "0123456789":
        if vault.verhoeff_ok(prefix + d):
            return prefix + d
    raise AssertionError


def test_add_aadhaar_masked_encrypted_and_revealed_only_to_owner(client):
    h = signup(client)["headers"]
    num = aadhaar()
    r = client.post("/me/documents", data={"kind": "aadhaar", "number": f"{num[:4]} {num[4:8]} {num[8:]}"},
                    files={"file": ("my aadhaar.png", PNG, "image/png")}, headers=h)
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["number_masked"] == f"XXXX XXXX {num[-4:]}" and doc["has_file"] and doc["file_type"] == "image/png"
    assert num not in r.text  # never the full number in a listing

    # On disk: encrypted, random name, not the PNG.
    files = list(settings.PRIVATE_DOCS_DIR.glob("*.bin"))
    assert files and all(not f.read_bytes().startswith(b"\x89PNG") for f in files)
    assert all("aadhaar" not in f.name for f in files)

    assert client.get(f"/me/documents/{doc['id']}/number", headers=h).json() == {"number": num}
    f = client.get(f"/me/documents/{doc['id']}/file", headers=h)
    assert f.status_code == 200 and f.content == PNG and f.headers["cache-control"] == "no-store"

    # Another traveller -- and the admin -- get nothing.
    riya = signup(client, OTHER)["headers"]
    for url in (f"/me/documents/{doc['id']}/number", f"/me/documents/{doc['id']}/file"):
        assert client.get(url, headers=riya).status_code == 404
    assert client.get("/me/documents", headers=riya).json()["items"] == []
    assert client.delete(f"/me/documents/{doc['id']}", headers=riya).status_code == 404


def test_numbers_are_checked():
    import pytest
    ok = {"pan": "abcde1234f", "passport": "k1234567", "driving_licence": "DL-04 2019 1234567", "voter_id": "ABC1234567"}
    for kind, n in ok.items():
        assert vault.clean_number(kind, n)
    for kind, n in {"aadhaar": "123456789012", "pan": "ABCD1234F", "passport": "12345678"}.items():
        with pytest.raises(vault.VaultError):
            vault.clean_number(kind, n)
    good = aadhaar()
    bad = good[:-1] + str((int(good[-1]) + 1) % 10)
    with pytest.raises(vault.VaultError, match="doesn't add up"):
        vault.clean_number("aadhaar", bad)


def test_bad_files_and_duplicates_are_refused(client):
    h = signup(client)["headers"]
    r = client.post("/me/documents", data={"kind": "pan"}, files={"file": ("x.exe", b"MZ\x90\x00evil", "image/png")}, headers=h)
    assert r.status_code == 422 and "photo" in r.json()["detail"]
    assert client.post("/me/documents", data={"kind": "pan"}, headers=h).status_code == 422  # nothing given
    assert client.post("/me/documents", data={"kind": "pan", "number": "ABCDE1234F"}, headers=h).status_code == 201
    dup = client.post("/me/documents", data={"kind": "pan", "number": "ABCDE1234G"}, headers=h)
    assert dup.status_code == 422 and "already" in dup.json()["detail"]


def test_passport_expiry_update_replaces_file_and_delete_removes_it(client):
    h = signup(client)["headers"]
    soon = (date.today() + timedelta(days=60)).isoformat()
    doc = client.post("/me/documents", data={"kind": "passport", "number": "K1234567", "expires_on": soon},
                      files={"file": ("p.pdf", PDF, "application/pdf")}, headers=h).json()
    assert doc["days_left"] == 60 and doc["number_masked"] == "•••• 4567"
    before = set(settings.PRIVATE_DOCS_DIR.glob("*.bin"))

    r = client.put(f"/me/documents/{doc['id']}", files={"file": ("p.png", PNG, "image/png")}, headers=h)
    assert r.json()["file_type"] == "image/png" and r.json()["number_masked"] == "•••• 4567"
    after = set(settings.PRIVATE_DOCS_DIR.glob("*.bin"))
    assert len(after - before) == 1 and len(before - after) == 1  # old file gone, new one written

    assert client.delete(f"/me/documents/{doc['id']}", headers=h).status_code == 204
    assert set(settings.PRIVATE_DOCS_DIR.glob("*.bin")) == after - (after - before)
    assert client.get("/me/documents", headers=h).json()["items"] == []


def test_admin_deleting_a_user_removes_their_files(client, session_factory):
    admin = _admin(client, session_factory)
    riya = signup(client, OTHER)
    client.post("/me/documents", data={"kind": "pan", "number": "ABCDE1234F"},
                files={"file": ("pan.png", PNG, "image/png")}, headers=riya["headers"])
    count = len(list(settings.PRIVATE_DOCS_DIR.glob("*.bin")))
    assert client.delete(f"/admin/users/{riya['user']['id']}", headers=admin).status_code == 204
    assert len(list(settings.PRIVATE_DOCS_DIR.glob("*.bin"))) == count - 1


def test_vault_off_without_a_key(client, monkeypatch):
    h = signup(client)["headers"]
    monkeypatch.setattr(settings, "DOCUMENT_ENCRYPTION_KEY", "")
    assert client.get("/me/documents", headers=h).json()["enabled"] is False
    assert client.post("/me/documents", data={"kind": "pan", "number": "ABCDE1234F"}, headers=h).status_code == 503
