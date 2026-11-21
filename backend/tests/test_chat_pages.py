"""The Help chat answers about the page it is opened on."""
from app.chat import pages
from app.chat.classify import classify
from app.chat.context import ChatContext
from app.chat.reply import draft_reply, page_reply


def ctx() -> ChatContext:
    return ChatContext(user_name="Raja Kumar", email="raja@example.com", email_verified=True)


def reply(page, message, intent="other", sentiment="neutral"):
    return page_reply(message, intent, sentiment, ctx(), page)


def test_every_page_answers_its_own_starter_questions():
    """No starter question may get the "could you tell me more?" reply."""
    for key, p in pages.PAGES.items():
        assert p.starters and p.clarify and p.intro, key
        for q in p.starters:
            intent, sentiment = classify(q)
            r = page_reply(q, intent, sentiment, ctx(), key)
            assert r != p.clarify and "That's on the" not in r, (key, q, r)


def test_same_question_different_page_different_answer():
    on_profile = reply("profile", "how do I delete it?")
    on_trip = reply("trip", "how do I delete it?")
    assert on_profile != on_trip and "dashboard" in on_trip


def test_page_specific_answers():
    assert "My documents" in reply("profile", "aadhar kaise add karu?")
    assert "come home" in reply("packing", "lautte waqt kya karna hai")
    assert "250 km" in reply("recommend", "what does To do?")
    assert "partner site" in reply("book", "can I pay here?")


def test_vague_question_gets_this_pages_follow_up():
    assert reply("profile", "help me") == pages.PAGES["profile"].clarify
    assert reply("packing", "kuch samajh nahi aaya") == pages.PAGES["packing"].clarify


def test_each_page_keeps_to_its_own_issues():
    """A question about another part of the app gets this page's follow-up
    question -- never an answer from somewhere else."""
    assert reply("packing", "how do I upload my aadhaar document?") == pages.PAGES["packing"].clarify
    assert pages.public_reply("login", "how do I add my aadhaar?") == pages.PAGES["login"].clarify
    # Trip answers that use their own data still work on trip pages, not on Profile.
    assert "Delete" in reply("dashboard", "how do I delete my trip?", intent="cancel_trip")
    assert "dashboard" in reply("trip", "where is my trip plan?", intent="cancel_trip")
    assert reply("profile", "how do I delete my trip?", intent="cancel_trip") == pages.PAGES["profile"].clarify


def test_public_help_before_login(client):
    r = client.post("/chat/public", json={"message": "I forgot my password", "page": "login"})
    assert r.status_code == 200 and "Forgot password?" in r.json()["reply"]
    r = client.post("/chat/public", json={"message": "mail nahi aaya", "page": "signup"})
    assert "24 hours" in r.json()["reply"]
    r = client.post("/chat/public", json={"message": "gst chahiye?", "page": "business_signup"})
    assert "GSTIN" in r.json()["reply"]
    assert client.get("/chat/help/login").json()["title"] == "Logging in"
    for key in ("login", "signup", "forgot_password", "business_signup", "home"):
        for q in pages.PAGES[key].starters:
            assert pages.public_reply(key, q) != pages.PAGES[key].clarify, (key, q)


def test_greeting_introduces_the_page():
    assert reply("packing", "hi", intent="greeting").startswith("Hi Raja! You're on the packing list")


def test_page_answers_are_not_counted_as_unsolved_problems():
    """How-to questions answered from the page must never pile up into a
    hand-off to a person -- they are labelled page_help, not other."""
    d = draft_reply("What does “Packing to come home” do?", ctx(), "packing")
    assert d.intent == "page_help" and "come home" in d.reply
    assert draft_reply("help me", ctx(), "packing").intent == "other"


def test_many_page_questions_do_not_escalate(client, session_factory):
    from app.chat import service
    from app.models.user import User
    from tests.helpers import signup
    signup(client)
    with session_factory() as db:
        user = db.query(User).first()
        for q in pages.PAGES["profile"].starters * 2:
            turn = service.handle_message(db, user, q, "profile")
            assert not turn.escalated, q


def test_help_endpoint_and_unknown_page(client):
    r = client.get("/chat/help/profile").json()
    assert r["title"] == "Profile" and len(r["starters"]) == 4
    r = client.get("/chat/help/nonsense").json()
    assert r["page"] is None and r["title"] == "Help"
