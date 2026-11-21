"""Profile page: view and edit your details, change your password."""
from tests.helpers import SIGNUP, signup


def test_signup_profile_fields_are_saved_and_editable(client):
    body = client.post("/auth/signup", json={
        **SIGNUP, "date_of_birth": "2000-05-17", "home_town": "  New   Delhi ",
        "phone": "+91 98765 43210", "gender": "male", "travel_interests": ["food", "food", "nature"],
    }).json()
    user = body["user"]
    assert user["home_town"] == "New Delhi"
    assert user["phone"] == "+919876543210"
    assert user["travel_interests"] == ["food", "nature"]

    headers = {"Authorization": f"Bearer {body['access_token']}"}
    r = client.put("/auth/me", json={"home_town": "Jaipur", "travel_interests": ["culture"]}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["home_town"] == "Jaipur"
    assert r.json()["travel_interests"] == ["culture"]
    assert r.json()["date_of_birth"] == "2000-05-17"  # untouched fields stay


def test_profile_rejects_bad_values(client):
    headers = signup(client)["headers"]
    assert client.put("/auth/me", json={"date_of_birth": "2099-01-01"}, headers=headers).status_code == 422
    assert client.put("/auth/me", json={"phone": "12"}, headers=headers).status_code == 422
    assert client.put("/auth/me", json={"name": ""}, headers=headers).status_code == 422


def test_change_password_needs_the_current_one(client):
    headers = signup(client)["headers"]
    wrong = client.post("/auth/change-password",
                        json={"current_password": "nope", "new_password": "fresh-pass-42"}, headers=headers)
    assert wrong.status_code == 400
    ok = client.post("/auth/change-password",
                     json={"current_password": SIGNUP["password"], "new_password": "fresh-pass-42"}, headers=headers)
    assert ok.status_code == 200, ok.text
    assert client.post("/auth/login", json={"email": SIGNUP["email"], "password": "fresh-pass-42"}).status_code == 200
