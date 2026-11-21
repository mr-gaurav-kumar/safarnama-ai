"""Package photos: upload rules and the seed data."""
from tests.helpers import OTHER, SIGNUP, signup

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _admin(client, session_factory):
    from app.models.user import User
    me = signup(client)
    with session_factory() as db:
        u = db.query(User).filter_by(email=SIGNUP["email"]).one()
        u.role = "admin"
        u.is_verified = True  # the real admin is always verified
        db.commit()
    return me["headers"]


def test_admin_uploads_a_photo_and_attaches_it(client, session_factory, tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "MEDIA_DIR", tmp_path)
    admin = _admin(client, session_factory)
    r = client.post("/uploads/package-image", files={"file": ("x.png", PNG, "image/png")}, headers=admin)
    assert r.status_code == 201, r.text
    url = r.json()["url"]
    assert url.startswith("/media/packages/") and url.endswith(".png")
    assert (tmp_path / "packages" / url.rsplit("/", 1)[1]).exists()

    pkg = client.post("/admin/packages", json={
        "title": "Photo test", "destination": "Goa", "duration_days": 3, "price_per_person": 9999,
        "images": [url, "https://example.com/beach.jpg"],
    }, headers=admin)
    assert pkg.status_code == 201, pkg.text
    assert pkg.json()["images"][0] == url


def test_uploads_are_checked(client, session_factory, tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "MEDIA_DIR", tmp_path)
    admin = _admin(client, session_factory)
    fake = client.post("/uploads/package-image", files={"file": ("x.png", b"<script>", "image/png")}, headers=admin)
    assert fake.status_code == 415
    user = signup(client, OTHER)["headers"]
    denied = client.post("/uploads/package-image", files={"file": ("x.png", PNG, "image/png")}, headers=user)
    assert denied.status_code == 403
    bad = client.post("/admin/packages", json={
        "title": "Bad", "destination": "Goa", "duration_days": 3, "price_per_person": 1, "images": ["javascript:alert(1)"],
    }, headers=admin)
    assert bad.status_code == 422


def test_seed_packages_are_valid():
    from app.data.seed_packages import PACKAGES
    from app.schemas.package import PackageIn
    titles = [PackageIn(**p).title for p in PACKAGES]
    assert len(titles) == len(set(titles)) == 6
