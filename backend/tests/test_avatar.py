"""Profile pictures: cropped, resized, re-encoded, metadata stripped."""
import io

import pytest
from PIL import Image

from app.core.config import settings
from tests.helpers import OTHER, signup
from tests.test_business import _admin


@pytest.fixture(autouse=True)
def media(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MEDIA_DIR", tmp_path)
    return tmp_path


def jpeg_with_gps(w=800, h=500) -> bytes:
    img = Image.new("RGB", (w, h), (200, 80, 40))
    exif = Image.Exif()
    exif[0x8825] = {2: (28.0, 40.0, 0.0), 4: (77.0, 26.0, 0.0)}  # GPSInfo: somewhere near Ghaziabad
    exif[0x010F] = "PhoneMaker"
    out = io.BytesIO()
    img.save(out, "JPEG", exif=exif)
    return out.getvalue()


def test_upload_is_square_webp_without_location(client, media):
    me = signup(client)
    raw = jpeg_with_gps()
    assert Image.open(io.BytesIO(raw)).getexif().get(0x8825)  # the original does carry GPS

    r = client.post("/auth/me/avatar", files={"file": ("me.jpg", raw, "image/jpeg")}, headers=me["headers"])
    assert r.status_code == 200, r.text
    url = r.json()["avatar_url"]
    assert url.startswith("/media/avatars/") and url.endswith(".webp") and "me.jpg" not in url

    saved = media / "avatars" / url.rsplit("/", 1)[-1]
    img = Image.open(saved)
    assert img.format == "WEBP" and img.size == (320, 320)
    assert not img.getexif()  # no GPS, no camera, nothing
    assert client.get("/auth/me", headers=me["headers"]).json()["avatar_url"] == url


def test_replace_deletes_old_file_and_remove_clears_it(client, media):
    me = signup(client)
    first = client.post("/auth/me/avatar", files={"file": ("a.jpg", jpeg_with_gps(), "image/jpeg")}, headers=me["headers"]).json()
    second = client.post("/auth/me/avatar", files={"file": ("b.jpg", jpeg_with_gps(300, 900), "image/jpeg")}, headers=me["headers"]).json()
    files = list((media / "avatars").iterdir())
    assert len(files) == 1 and files[0].name == second["avatar_url"].rsplit("/", 1)[-1]
    assert first["avatar_url"] != second["avatar_url"]

    r = client.delete("/auth/me/avatar", headers=me["headers"])
    assert r.json()["avatar_url"] is None and list((media / "avatars").iterdir()) == []


def test_not_a_photo_is_refused(client):
    me = signup(client)
    for name, data in (("x.png", b"MZ\x90\x00not an image"), ("y.gif", b"GIF89a" + b"\x00" * 50)):
        r = client.post("/auth/me/avatar", files={"file": (name, data, "image/png")}, headers=me["headers"])
        assert r.status_code == 422


def test_admin_sees_the_picture_and_deleting_the_user_removes_it(client, session_factory, media):
    admin = _admin(client, session_factory)
    riya = signup(client, OTHER)
    url = client.post("/auth/me/avatar", files={"file": ("r.jpg", jpeg_with_gps(), "image/jpeg")},
                      headers=riya["headers"]).json()["avatar_url"]
    users = client.get("/admin/users", headers=admin).json()["items"]
    assert next(u for u in users if u["email"] == OTHER["email"])["avatar_url"] == url
    client.delete(f"/admin/users/{riya['user']['id']}", headers=admin)
    assert list((media / "avatars").iterdir()) == []


def test_needs_login(client):
    assert client.post("/auth/me/avatar", files={"file": ("a.jpg", b"x", "image/jpeg")}).status_code in (401, 403)
