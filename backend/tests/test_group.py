"""Group trips: who can do what, invitations, merged preferences, matches, room."""
from datetime import date, timedelta

import pytest
from starlette.websockets import WebSocketDisconnect

from app.notify.email import OUTBOX
from tests.helpers import OTHER, SIGNUP, THIRD, create_trip, invite_token, signup, verified

FUTURE = date.today() + timedelta(days=40)
TRIP = {
    "destination": "Goa", "start_date": FUTURE.isoformat(),
    "end_date": (FUTURE + timedelta(days=3)).isoformat(),
    "budget": "40000", "travelers": 3, "style_tags": ["relax"], "use_memory": False,
}


@pytest.fixture
def group(client):
    """Garv owns a Goa trip; Riya is invited and joins; Aman is a stranger."""
    garv = verified(client, SIGNUP)
    riya = verified(client, OTHER)
    aman = verified(client, THIRD)
    trip = create_trip(client, TRIP, garv["headers"])
    r = client.post(f"/trips/{trip['id']}/invite", json={"email": OTHER["email"]}, headers=garv["headers"])
    assert r.status_code == 202, r.text
    token = invite_token(OTHER["email"])
    r = client.post(f"/trips/{trip['id']}/join", json={"token": token}, headers=riya["headers"])
    assert r.status_code == 200, r.text
    return {"garv": garv, "riya": riya, "aman": aman, "trip": trip, "id": trip["id"]}


def H(p):
    return p["headers"]


# --- access -------------------------------------------------------------------

def test_a_member_can_see_the_trip_and_it_appears_in_their_list(client, group):
    r = client.get(f"/trips/{group['id']}", headers=H(group["riya"]))
    assert r.status_code == 200 and r.json()["role"] == "member"
    listed = client.get("/trips", headers=H(group["riya"])).json()
    assert [(t["destination"], t["role"]) for t in listed] == [("Goa", "member")]
    owner_view = client.get("/trips", headers=H(group["garv"])).json()[0]
    assert owner_view["role"] == "owner" and owner_view["member_count"] == 1


def test_a_stranger_sees_nothing(client, group):
    for path in ("", "/members", "/pdf", "/feedback"):
        assert client.get(f"/trips/{group['id']}{path}", headers=H(group["aman"])).status_code == 404


@pytest.mark.parametrize("method, path, body", [
    ("delete", "", None),
    ("post", "/replan", None),
    ("post", "/invite", {"email": "x@example.com"}),
    ("put", "/discoverable", {"discoverable": True}),
])
def test_members_cannot_do_owner_things(client, group, method, path, body):
    r = getattr(client, method)(f"/trips/{group['id']}{path}", headers=H(group["riya"]),
                                **({"json": body} if body else {}))
    assert r.status_code == 403


def test_member_can_download_the_pdf_and_email_it_to_themselves(client, group):
    assert client.get(f"/trips/{group['id']}/pdf", headers=H(group["riya"])).status_code == 200
    OUTBOX.clear()
    assert client.post(f"/trips/{group['id']}/email", headers=H(group["riya"])).status_code == 202
    assert [e.to for e in OUTBOX] == [OTHER["email"]], "a member's copy goes to the member"


# --- invitations ---------------------------------------------------------------

def test_the_invitation_email_carries_a_join_link(client):
    garv = verified(client)
    trip = create_trip(client, TRIP, H(garv))
    OUTBOX.clear()
    client.post(f"/trips/{trip['id']}/invite", json={"email": "Riya@Example.com"}, headers=H(garv))
    [mail] = list(OUTBOX)
    assert mail.to == "riya@example.com"
    assert f"/join?trip={trip['id']}&token=" in mail.text


def test_the_link_only_works_for_the_invited_address(client, group):
    """A forwarded link is useless to anyone else."""
    garv = group["garv"]
    client.post(f"/trips/{group['id']}/invite", json={"email": "someone@example.com"}, headers=H(garv))
    token = invite_token("someone@example.com")
    r = client.post(f"/trips/{group['id']}/join", json={"token": token}, headers=H(group["aman"]))
    assert r.status_code == 404


def test_an_unverified_account_cannot_take_an_invitation(client):
    """Otherwise anyone could sign up with the invitee's address and join."""
    garv = verified(client)
    trip = create_trip(client, TRIP, H(garv))
    client.post(f"/trips/{trip['id']}/invite", json={"email": OTHER["email"]}, headers=H(garv))
    token = invite_token(OTHER["email"])

    impostor = signup(client, OTHER)  # same address, never verified
    r = client.post(f"/trips/{trip['id']}/join", json={"token": token}, headers=H(impostor))
    assert r.status_code == 403
    assert client.get("/invitations", headers=H(impostor)).json() == []


def test_join_from_the_dashboard_without_the_link(client):
    garv = verified(client)
    riya = verified(client, OTHER)
    trip = create_trip(client, TRIP, H(garv))
    client.post(f"/trips/{trip['id']}/invite", json={"email": OTHER["email"]}, headers=H(garv))

    [inv] = client.get("/invitations", headers=H(riya)).json()
    assert inv["destination"] == "Goa" and inv["invited_by"] == "Garv"
    assert client.post(f"/trips/{trip['id']}/join", json={}, headers=H(riya)).status_code == 200
    assert client.get("/invitations", headers=H(riya)).json() == []


def test_reinviting_invalidates_the_old_link(client):
    garv = verified(client)
    riya = verified(client, OTHER)
    trip = create_trip(client, TRIP, H(garv))
    client.post(f"/trips/{trip['id']}/invite", json={"email": OTHER["email"]}, headers=H(garv))
    old = invite_token(OTHER["email"])
    client.post(f"/trips/{trip['id']}/invite", json={"email": OTHER["email"]}, headers=H(garv))
    assert client.post(f"/trips/{trip['id']}/join", json={"token": old}, headers=H(riya)).status_code == 404


def test_cannot_invite_yourself_or_someone_already_in(client, group):
    g = H(group["garv"])
    assert client.post(f"/trips/{group['id']}/invite", json={"email": SIGNUP["email"]}, headers=g).status_code == 409
    assert client.post(f"/trips/{group['id']}/invite", json={"email": OTHER["email"]}, headers=g).status_code == 409


def test_decline_hides_the_invitation_from_other_members(client, group):
    garv, aman = group["garv"], group["aman"]
    client.post(f"/trips/{group['id']}/invite", json={"email": THIRD["email"]}, headers=H(garv))
    assert client.post(f"/trips/{group['id']}/decline", json={}, headers=H(aman)).status_code == 204

    owner_sees = {m["email"]: m["role"] for m in client.get(f"/trips/{group['id']}/members", headers=H(garv)).json()}
    member_sees = {m["email"] for m in client.get(f"/trips/{group['id']}/members", headers=H(group["riya"])).json()}
    assert owner_sees[THIRD["email"]] == "declined"
    assert THIRD["email"] not in member_sees


def test_leave_and_remove(client, group):
    riya = group["riya"]
    assert client.post(f"/trips/{group['id']}/leave", headers=H(riya)).status_code == 204
    assert client.get(f"/trips/{group['id']}", headers=H(riya)).status_code == 404
    # the owner can't "leave"
    assert client.post(f"/trips/{group['id']}/leave", headers=H(group["garv"])).status_code == 409


def test_owner_removes_a_member(client, group):
    members = client.get(f"/trips/{group['id']}/members", headers=H(group["garv"])).json()
    riya_row = next(m for m in members if m["email"] == OTHER["email"])
    r = client.delete(f"/trips/{group['id']}/members/{riya_row['id']}", headers=H(group["garv"]))
    assert r.status_code == 204
    assert client.get(f"/trips/{group['id']}", headers=H(group["riya"])).status_code == 404


# --- planning for the group ----------------------------------------------------

def test_replan_merges_everyones_preferences(client, group, monkeypatch):
    from app.services import trip_service

    seen = {}
    real = trip_service.generate_itinerary

    def spy(**kw):
        seen.update(kw)
        return real(**kw)

    monkeypatch.setattr(trip_service, "generate_itinerary", spy)
    client.put(f"/trips/{group['id']}/my-preferences", json={"style_tags": ["food", "relax"]},
               headers=H(group["riya"]))
    r = client.post(f"/trips/{group['id']}/replan", headers=H(group["garv"]))
    assert r.status_code == 202

    assert seen["style_tags"][0] == "relax", "wanted by both, so it comes first"
    assert set(seen["style_tags"]) == {"relax", "food"}
    assert "group of 2" in seen["group_context"]
    assert "Riya wants food, relax" in seen["group_context"]


def test_a_solo_trip_has_no_group_context(client, monkeypatch):
    from app.services import trip_service

    seen = {}
    real = trip_service.generate_itinerary
    monkeypatch.setattr(trip_service, "generate_itinerary", lambda **kw: (seen.update(kw), real(**kw))[1])
    create_trip(client, TRIP, H(verified(client)))
    assert seen["group_context"] is None


# --- matches (opt-in) -------------------------------------------------------------

def _two_goa_trips(client):
    garv = verified(client)
    riya = verified(client, OTHER)
    mine = create_trip(client, TRIP, H(garv))
    theirs = create_trip(client, {**TRIP, "start_date": (FUTURE + timedelta(days=2)).isoformat(),
                                  "end_date": (FUTURE + timedelta(days=6)).isoformat(),
                                  "destination": " goa "}, H(riya))
    return garv, riya, mine, theirs


def test_nobody_is_discoverable_by_default(client):
    garv, riya, mine, theirs = _two_goa_trips(client)
    client.put(f"/trips/{mine['id']}/discoverable", json={"discoverable": True}, headers=H(garv))
    assert client.get(f"/trips/{mine['id']}/matches", headers=H(garv)).json() == []


def test_matches_are_reciprocal(client):
    """You only see others if they can see you."""
    garv, riya, mine, theirs = _two_goa_trips(client)
    client.put(f"/trips/{theirs['id']}/discoverable", json={"discoverable": True}, headers=H(riya))
    assert client.get(f"/trips/{mine['id']}/matches", headers=H(garv)).json() == []

    client.put(f"/trips/{mine['id']}/discoverable", json={"discoverable": True}, headers=H(garv))
    [m] = client.get(f"/trips/{mine['id']}/matches", headers=H(garv)).json()
    assert m["first_name"] == "Riya" and m["overlap_days"] == 2
    assert "email" not in m, "only a first name is shown"


def test_suggesting_teaming_up_emails_them_once(client):
    garv, riya, mine, theirs = _two_goa_trips(client)
    for who, t in ((garv, mine), (riya, theirs)):
        client.put(f"/trips/{t['id']}/discoverable", json={"discoverable": True}, headers=H(who))
    OUTBOX.clear()
    url = f"/trips/{mine['id']}/matches/{theirs['id']}/request"
    assert client.post(url, headers=H(garv)).status_code == 202
    [mail] = list(OUTBOX)
    assert mail.to == OTHER["email"] and SIGNUP["email"] in mail.text
    assert client.post(url, headers=H(garv)).status_code == 409


# --- the room ------------------------------------------------------------------

def _room(client, trip_id, token):
    ws = client.websocket_connect(f"/ws/trips/{trip_id}/room")
    conn = ws.__enter__()
    conn.send_json({"type": "auth", "token": token})
    return ws, conn


def test_room_messages_reach_other_members_and_are_kept(client, group):
    ws1, garv = _room(client, group["id"], group["garv"]["token"])
    assert garv.receive_json() == {"type": "history", "messages": []}
    ws2, riya = _room(client, group["id"], group["riya"]["token"])
    riya.receive_json()

    garv.send_json({"type": "message", "text": "Beach on day 1?"})
    got = riya.receive_json()
    assert got["type"] == "message" and got["message"]["text"] == "Beach on day 1?"
    assert got["message"]["name"] == "Garv"
    assert garv.receive_json()["message"]["text"] == "Beach on day 1?"
    ws1.__exit__(None, None, None)
    ws2.__exit__(None, None, None)

    ws3, again = _room(client, group["id"], group["riya"]["token"])
    [kept] = again.receive_json()["messages"]
    assert kept["text"] == "Beach on day 1?"
    ws3.__exit__(None, None, None)


def test_a_stranger_cannot_enter_the_room(client, group):
    with client.websocket_connect(f"/ws/trips/{group['id']}/room") as ws:
        ws.send_json({"type": "auth", "token": group["aman"]["token"]})
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_json()
        assert info.value.code == 4404
